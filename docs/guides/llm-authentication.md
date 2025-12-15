# Multi-LLM Authentication Guide

**Version:** 1.0.0
**Last Updated:** 2025-12-15

## Overview

write-assist uses three LLMs in parallel: Claude (Anthropic), Gemini (Google), and ChatGPT (OpenAI). This guide covers authentication setup for each.

## Environment Variables

All API keys should be stored as environment variables, **never** in code or config files.

```bash
# Add to ~/.zshrc or ~/.bashrc
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="AIza..."
export OPENAI_API_KEY="sk-..."
```

After adding, reload your shell:
```bash
source ~/.zshrc
```

## Claude (Anthropic)

### Getting an API Key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Sign in or create an account
3. Navigate to API Keys
4. Create a new key
5. Copy and store securely

### Python SDK Installation

```bash
uv add anthropic
```

### Basic Usage

```python
from anthropic import Anthropic

client = Anthropic()  # Uses ANTHROPIC_API_KEY env var

message = client.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=4096,
    messages=[
        {"role": "user", "content": "Your prompt here"}
    ]
)

print(message.content[0].text)
```

### Available Models

| Model | Use Case | Context Window |
|-------|----------|----------------|
| claude-sonnet-4-20250514 | Balanced performance | 200K |
| claude-opus-4-20250514 | Highest capability | 200K |
| claude-haiku-3-5-20241022 | Fast, economical | 200K |

### Rate Limits

Check your tier at [console.anthropic.com/settings/limits](https://console.anthropic.com/settings/limits)

## Gemini (Google)

### Getting an API Key

1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Sign in with Google account
3. Click "Get API Key"
4. Create key in new or existing project
5. Copy and store securely

### Python SDK Installation

```bash
uv add google-generativeai
```

### Basic Usage

```python
import google.generativeai as genai

genai.configure()  # Uses GOOGLE_API_KEY env var

model = genai.GenerativeModel("gemini-1.5-pro")

response = model.generate_content("Your prompt here")

print(response.text)
```

### Available Models

| Model | Use Case | Context Window |
|-------|----------|----------------|
| gemini-1.5-pro | Balanced, large context | 2M |
| gemini-1.5-flash | Fast responses | 1M |
| gemini-2.0-flash-exp | Latest experimental | 1M |

### Rate Limits

Free tier: 60 requests/minute
Paid tier: Higher limits based on quota

## ChatGPT (OpenAI)

### Getting an API Key

1. Go to [platform.openai.com](https://platform.openai.com)
2. Sign in or create an account
3. Navigate to API Keys
4. Create a new secret key
5. Copy and store securely (shown only once)

### Python SDK Installation

```bash
uv add openai
```

### Basic Usage

```python
from openai import OpenAI

client = OpenAI()  # Uses OPENAI_API_KEY env var

response = client.chat.completions.create(
    model="gpt-4o",
    messages=[
        {"role": "user", "content": "Your prompt here"}
    ]
)

print(response.choices[0].message.content)
```

### Available Models

| Model | Use Case | Context Window |
|-------|----------|----------------|
| gpt-4o | Flagship multimodal | 128K |
| gpt-4o-mini | Fast, economical | 128K |
| gpt-4-turbo | Previous generation | 128K |
| o1-preview | Advanced reasoning | 128K |

### Rate Limits

Varies by tier and model. Check [platform.openai.com/account/limits](https://platform.openai.com/account/limits)

## Unified Client Pattern

For write-assist, we use a unified interface across all three providers:

```python
# src/write_assist/llm/client.py

from dataclasses import dataclass
from typing import Literal

ModelProvider = Literal["claude", "gemini", "chatgpt"]

@dataclass
class LLMResponse:
    content: str
    model: str
    provider: ModelProvider
    usage: dict

async def query_llm(
    prompt: str,
    provider: ModelProvider,
    model: str | None = None,
    max_tokens: int = 4096,
) -> LLMResponse:
    """Unified interface for querying any supported LLM."""

    if provider == "claude":
        return await _query_claude(prompt, model or "claude-sonnet-4-20250514", max_tokens)
    elif provider == "gemini":
        return await _query_gemini(prompt, model or "gemini-1.5-pro", max_tokens)
    elif provider == "chatgpt":
        return await _query_chatgpt(prompt, model or "gpt-4o", max_tokens)
    else:
        raise ValueError(f"Unknown provider: {provider}")
```

## Parallel Execution Pattern

For the ensemble pipeline:

```python
import asyncio
from write_assist.llm.client import query_llm

async def run_drafters(prompt: str) -> list[LLMResponse]:
    """Run drafter agent on all three LLMs in parallel."""

    tasks = [
        query_llm(prompt, provider="claude"),
        query_llm(prompt, provider="gemini"),
        query_llm(prompt, provider="chatgpt"),
    ]

    return await asyncio.gather(*tasks)
```

## Security Best Practices

1. **Never commit API keys** - Use environment variables
2. **Use .env files carefully** - Add to .gitignore
3. **Rotate keys periodically** - Especially after team changes
4. **Monitor usage** - Set up billing alerts
5. **Use least privilege** - Create project-specific keys when possible

## Verifying Setup

Run this script to verify all three APIs are configured:

```python
# temp/verify_llm_setup.py
import os

def verify_setup():
    keys = {
        "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY"),
        "GOOGLE_API_KEY": os.environ.get("GOOGLE_API_KEY"),
        "OPENAI_API_KEY": os.environ.get("OPENAI_API_KEY"),
    }

    for name, value in keys.items():
        if value:
            # Show first/last 4 chars only
            masked = f"{value[:4]}...{value[-4:]}"
            print(f"✓ {name}: {masked}")
        else:
            print(f"✗ {name}: NOT SET")

if __name__ == "__main__":
    verify_setup()
```

```bash
uv run python temp/verify_llm_setup.py
```

## Troubleshooting

### "Invalid API Key" Errors

- Verify key is set: `echo $ANTHROPIC_API_KEY`
- Check for leading/trailing whitespace
- Ensure key hasn't been revoked
- Verify correct environment (some keys are project-specific)

### Rate Limit Errors

- Implement exponential backoff
- Check your tier limits
- Consider batching requests
- Use appropriate model for task (smaller models for simple tasks)

### Network Errors

- Check internet connectivity
- Verify no proxy/firewall blocking
- Try curl to API endpoint directly

---

*Secure API key management is essential for multi-LLM systems.*
