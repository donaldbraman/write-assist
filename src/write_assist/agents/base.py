"""
Base agent class for orchestrating LLM calls.
"""

import asyncio
import json
import re
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Generic, TypeVar

from pydantic import BaseModel, ValidationError

from write_assist.agents.models import AgentError, ParallelRunResult, Provider
from write_assist.llm import LLMClient, LLMError, Message

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

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Failed to parse JSON from {provider}: {e}\nResponse: {response[:500]}..."
            ) from e

        # Add metadata if not present
        if "metadata" not in data:
            data["metadata"] = {}
        data["metadata"]["provider"] = provider

        try:
            return self.output_model.model_validate(data)
        except ValidationError as e:
            raise ValueError(f"Output validation failed for {provider}: {e}") from e

    async def run(
        self,
        inputs: InputT,
        provider: Provider,
        max_tokens: int = 8192,
        temperature: float = 0.7,
    ) -> OutputT:
        """
        Run the agent on a single provider.

        Args:
            inputs: Validated input model
            provider: Which LLM provider to use
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            Validated output model instance

        Raises:
            LLMError: If the LLM call fails
            ValueError: If output parsing/validation fails
        """
        # Validate inputs
        if not isinstance(inputs, self.input_model):
            inputs = self.input_model.model_validate(inputs)

        # Build prompt
        prompt = self.build_prompt(inputs)

        # Create client with specified model
        model = self.models.get(provider)
        client = LLMClient(provider=provider, model=model)

        # Make the call
        response = await client.chat(
            messages=[
                Message(role="system", content=self._get_system_message()),
                Message(role="user", content=prompt),
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )

        # Parse and validate response
        return self.parse_json_response(response.content, provider)

    async def run_parallel(
        self,
        inputs: InputT,
        providers: list[Provider] | None = None,
        max_tokens: int = 8192,
        temperature: float = 0.7,
    ) -> ParallelRunResult:
        """
        Run the agent on multiple providers in parallel.

        Args:
            inputs: Validated input model
            providers: List of providers (defaults to all three)
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature

        Returns:
            ParallelRunResult with successful and failed results
        """
        if providers is None:
            providers = ["claude", "gemini", "chatgpt"]

        # Validate inputs once
        if not isinstance(inputs, self.input_model):
            inputs = self.input_model.model_validate(inputs)

        async def run_one(provider: Provider) -> tuple[Provider, OutputT | AgentError]:
            """Run on one provider, catching errors."""
            try:
                result = await self.run(
                    inputs=inputs,
                    provider=provider,
                    max_tokens=max_tokens,
                    temperature=temperature,
                )
                return provider, result
            except LLMError as e:
                return provider, AgentError(
                    provider=provider,
                    error_type=type(e).__name__,
                    message=str(e),
                    original_error=e.original if hasattr(e, "original") else None,
                )
            except ValueError as e:
                return provider, AgentError(
                    provider=provider,
                    error_type="ValidationError",
                    message=str(e),
                )
            except Exception as e:
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

    def _get_system_message(self) -> str:
        """Get the system message for this agent."""
        return (
            f"You are the {self.agent_name} agent. "
            "You MUST respond with valid JSON matching the specified output contract. "
            "Do not include any text outside the JSON object."
        )
