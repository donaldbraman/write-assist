"""
Base agent class for orchestrating LLM calls.
"""

import asyncio
import json
import logging
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel, ValidationError
from tenacity import (
    before_sleep_log,
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from write_assist.agents.models import AgentError, ParallelRunResult, Provider
from write_assist.caching import get_llm_cache
from write_assist.llm import LLMClient, LLMError, Message

logger = logging.getLogger(__name__)

# Type variables for input/output models
InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)

# Default models per provider (premium models for write-assist)
DEFAULT_MODELS: dict[Provider, str] = {
    "claude": "claude-opus-4-5-20251101",
    "gemini": "gemini-2.5-flash",
    "chatgpt": "gpt-5.2",
}


class BaseAgent(ABC, Generic[InputT, OutputT]):
    """
    Abstract base class for agents.

    Handles:
    - Loading agent specs from markdown files
    - Building prompts from templates
    - Running prompts against LLMs
    - Parsing and validating JSON outputs
    """

    # Subclasses must define these
    agent_name: str
    spec_file: str  # Relative to .claude/agents/
    input_model: type[InputT]
    output_model: type[OutputT]

    def __init__(
        self,
        project_root: Path | None = None,
        models: dict[Provider, str] | None = None,
    ):
        """
        Initialize the agent.

        Args:
            project_root: Root directory of the project (for finding specs)
            models: Custom models per provider (overrides defaults)
        """
        self.project_root = project_root or self._find_project_root()
        self.models = models or DEFAULT_MODELS.copy()
        self._spec_content: str | None = None
        self._prompt_template: str | None = None

    def _find_project_root(self) -> Path:
        """Find the project root by looking for .claude directory."""
        current = Path.cwd()
        for parent in [current, *current.parents]:
            if (parent / ".claude").is_dir():
                return parent
        # Fall back to current directory
        return current

    @property
    def spec_path(self) -> Path:
        """Full path to the agent spec file."""
        return self.project_root / ".claude" / "agents" / self.spec_file

    def load_spec(self) -> str:
        """Load the agent specification from markdown."""
        if self._spec_content is None:
            if not self.spec_path.exists():
                raise FileNotFoundError(f"Agent spec not found: {self.spec_path}")
            self._spec_content = self.spec_path.read_text()
        return self._spec_content

    def extract_prompt_template(self) -> str:
        """Extract the prompt template from the spec."""
        if self._prompt_template is None:
            spec = self.load_spec()
            # Find content between ```prompt template``` markers
            # The spec uses ## Prompt Template followed by ``` code block
            match = re.search(
                r"## Prompt Template\s*\n```\n(.*?)\n```",
                spec,
                re.DOTALL,
            )
            if not match:
                raise ValueError(f"No prompt template found in {self.spec_file}")
            self._prompt_template = match.group(1)
        return self._prompt_template

    @abstractmethod
    def build_prompt(self, inputs: InputT) -> str:
        """
        Build the full prompt from inputs.

        Subclasses implement this to handle their specific variable substitution.
        """
        pass

    def parse_json_response(self, response: str, provider: Provider) -> OutputT:
        """
        Parse JSON from LLM response and validate against output model.

        Args:
            response: Raw response text from LLM
            provider: Which provider generated this response

        Returns:
            Validated output model instance

        Raises:
            ValueError: If JSON parsing or validation fails
        """
        # Store raw response for debugging
        self._last_raw_response = response
        self._last_provider = provider

        # Try to extract JSON from the response
        # LLMs sometimes wrap JSON in markdown code blocks
        json_str = response.strip()

        # Remove markdown code blocks if present
        if json_str.startswith("```json"):
            json_str = json_str[7:]
        elif json_str.startswith("```"):
            json_str = json_str[3:]

        if json_str.endswith("```"):
            json_str = json_str[:-3]

        json_str = json_str.strip()

        # Try to find JSON object if response has extra text
        if not json_str.startswith("{"):
            # Look for JSON object in the response
            match = re.search(r"\{[\s\S]*\}", json_str)
            if match:
                logger.warning(f"{provider} returned extra text before JSON, extracting object")
                json_str = match.group(0)

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            # Log the full response for debugging
            logger.error(
                f"JSON parse error from {provider}:\n"
                f"Error: {e}\n"
                f"Response length: {len(response)} chars\n"
                f"First 1000 chars:\n{response[:1000]}\n"
                f"Last 500 chars:\n{response[-500:]}"
            )
            raise ValueError(
                f"Failed to parse JSON from {provider}: {e}\n"
                f"Response length: {len(response)} chars\n"
                f"Response start: {response[:500]}...\n"
                f"Response end: ...{response[-500:]}"
            ) from e

        # Add metadata if not present
        if "metadata" not in data:
            data["metadata"] = {}
        data["metadata"]["provider"] = provider

        try:
            return self.output_model.model_validate(data)
        except ValidationError as e:
            # Log validation errors with context
            logger.error(
                f"Validation error from {provider}:\n"
                f"Error: {e}\n"
                f"Data keys: {list(data.keys())}\n"
                f"Expected model: {self.output_model.__name__}"
            )
            raise ValueError(
                f"Output validation failed for {provider}: {e}\n"
                f"Data keys received: {list(data.keys())}"
            ) from e

    async def run(
        self,
        inputs: InputT,
        provider: Provider,
        max_tokens: int = 8192,
        temperature: float = 0.7,
        max_retries: int = 3,
    ) -> OutputT:
        """
        Run the agent on a single provider with retry logic.

        Args:
            inputs: Validated input model
            provider: Which LLM provider to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            max_retries: Maximum number of retry attempts for transient failures

        Returns:
            Validated output model instance

        Raises:
            LLMError: If the LLM call fails after all retries
            ValueError: If output parsing/validation fails after all retries
        """
        # Validate inputs
        if not isinstance(inputs, self.input_model):
            inputs = self.input_model.model_validate(inputs)

        # Build prompt
        prompt = self.build_prompt(inputs)
        system_message = self._get_system_message()

        # Get model for this provider
        model = self.models.get(provider) or ""

        # Check cache for existing response
        cache = get_llm_cache()
        cache_key = cache.make_key(
            provider=provider,
            model=model,
            prompt=prompt,
            system_message=system_message,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        cached_response = cache.get(cache_key)
        if cached_response is not None:
            # Return cached response
            return self.parse_json_response(cached_response, provider)

        # Define the retryable operation
        @retry(
            stop=stop_after_attempt(max_retries),
            wait=wait_exponential(multiplier=2, min=4, max=60),
            retry=retry_if_exception_type((LLMError, ValueError, TimeoutError)),
            before_sleep=before_sleep_log(logger, logging.WARNING),
            reraise=True,
        )
        async def _call_with_retry() -> str:
            """Make LLM call with retry logic."""
            client = LLMClient(provider=provider, model=model if model else None)

            logger.info(f"Calling {provider} ({model or 'default'}) for {self.agent_name}")

            response = await client.chat(
                messages=[
                    Message(role="system", content=system_message),
                    Message(role="user", content=prompt),
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )

            # Try to parse immediately to catch format errors
            # This allows retry on malformed responses
            parsed = self.parse_json_response(response.content, provider)

            # Only cache if parsing succeeded
            cache.set(cache_key, response.content)

            return parsed

        return await _call_with_retry()

    async def run_parallel(
        self,
        inputs: InputT,
        providers: list[Provider] | None = None,
        max_tokens: int = 8192,
        temperature: float = 0.7,
        max_retries: int = 3,
    ) -> ParallelRunResult:
        """
        Run the agent on multiple providers in parallel.

        Args:
            inputs: Validated input model
            providers: List of providers (defaults to all three)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature
            max_retries: Maximum retry attempts per provider

        Returns:
            ParallelRunResult with successful and failed results
        """
        if providers is None:
            providers = ["claude", "gemini", "chatgpt"]

        # Validate inputs once
        if not isinstance(inputs, self.input_model):
            inputs = self.input_model.model_validate(inputs)

        # Store raw responses for failed providers (for debugging)
        self._failed_raw_responses: dict[Provider, str] = {}

        async def run_one(provider: Provider) -> tuple[Provider, OutputT | AgentError]:
            """Run on one provider, catching errors."""
            try:
                result = await self.run(
                    inputs=inputs,
                    provider=provider,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    max_retries=max_retries,
                )
                return provider, result
            except LLMError as e:
                logger.error(f"{self.agent_name} LLM error from {provider}: {e}")
                return provider, AgentError(
                    provider=provider,
                    error_type=type(e).__name__,
                    message=str(e),
                    original_error=str(e.original)
                    if hasattr(e, "original") and e.original
                    else None,
                )
            except ValueError as e:
                # Capture raw response if available
                if (
                    hasattr(self, "_last_raw_response")
                    and hasattr(self, "_last_provider")
                    and self._last_provider == provider
                ):
                    self._failed_raw_responses[provider] = self._last_raw_response
                    logger.error(
                        f"{self.agent_name} validation error from {provider}. "
                        f"Raw response saved ({len(self._last_raw_response)} chars)"
                    )
                return provider, AgentError(
                    provider=provider,
                    error_type="ValidationError",
                    message=str(e),
                )
            except Exception as e:
                logger.error(
                    f"{self.agent_name} unexpected error from {provider}: {type(e).__name__}: {e}"
                )
                return provider, AgentError(
                    provider=provider,
                    error_type=type(e).__name__,
                    message=str(e),
                )

        # Run all in parallel
        results = await asyncio.gather(*[run_one(p) for p in providers])

        # Separate successes and failures
        successful: dict[Provider, OutputT] = {}
        failed: dict[Provider, AgentError] = {}

        for provider, result in results:
            if isinstance(result, AgentError):
                failed[provider] = result
            else:
                successful[provider] = result

        return ParallelRunResult(successful=successful, failed=failed)

    def get_failed_raw_response(self, provider: Provider) -> str | None:
        """Get the raw response from a failed provider for debugging."""
        if hasattr(self, "_failed_raw_responses"):
            return self._failed_raw_responses.get(provider)
        return None

    def _get_system_message(self) -> str:
        """Get the system message for this agent."""
        return (
            f"You are the {self.agent_name} agent. "
            "You MUST respond with valid JSON matching the specified output contract. "
            "Do not include any text outside the JSON object."
        )
