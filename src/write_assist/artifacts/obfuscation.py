"""
Provider name obfuscation for bias-free evaluation.

Uses Hebrew letters (aleph, bet, gimel) as neutral aliases to prevent
unconscious bias when editors see drafts or judges evaluate edits.
"""

import random
from typing import Literal

from pydantic import BaseModel, PrivateAttr

from write_assist.agents.models import Provider

# Alias type
Alias = Literal["aleph", "bet", "gimel"]

# All aliases
ALIASES: list[Alias] = ["aleph", "bet", "gimel"]

# All providers
PROVIDERS: list[Provider] = ["claude", "gemini", "chatgpt"]


class ProviderMapping(BaseModel):
    """Bidirectional mapping between providers and obfuscated aliases."""

    aleph: Provider
    bet: Provider
    gimel: Provider

    # Reverse lookup cache (private attribute)
    _reverse: dict[Provider, Alias] = PrivateAttr(default_factory=dict)

    def model_post_init(self, __context: object) -> None:
        """Build reverse lookup after initialization."""
        self._reverse = {
            self.aleph: "aleph",
            self.bet: "bet",
            self.gimel: "gimel",
        }

    def get_provider(self, alias: Alias) -> Provider:
        """Get the real provider for an alias."""
        return getattr(self, alias)

    def get_alias(self, provider: Provider) -> Alias:
        """Get the alias for a provider."""
        return self._reverse[provider]

    def to_dict(self) -> dict[Alias, Provider]:
        """Export as alias -> provider dict."""
        return {
            "aleph": self.aleph,
            "bet": self.bet,
            "gimel": self.gimel,
        }

    def to_reverse_dict(self) -> dict[Provider, Alias]:
        """Export as provider -> alias dict."""
        return dict(self._reverse)

    @classmethod
    def create_random(cls) -> "ProviderMapping":
        """Create a new random mapping."""
        shuffled = PROVIDERS.copy()
        random.shuffle(shuffled)
        return cls(
            aleph=shuffled[0],
            bet=shuffled[1],
            gimel=shuffled[2],
        )

    @classmethod
    def from_dict(cls, mapping: dict[str, str]) -> "ProviderMapping":
        """Restore from a dict (e.g., from JSON)."""
        return cls(
            aleph=mapping["aleph"],  # type: ignore
            bet=mapping["bet"],  # type: ignore
            gimel=mapping["gimel"],  # type: ignore
        )


def obfuscate_provider_in_text(text: str, mapping: ProviderMapping) -> str:
    """
    Replace provider names with aliases in text.

    Handles case variations: Claude, CLAUDE, claude -> aleph
    """
    result = text
    for provider in PROVIDERS:
        alias = mapping.get_alias(provider)  # type: ignore
        # Replace all case variations
        result = result.replace(provider, alias)
        result = result.replace(provider.title(), alias.title())
        result = result.replace(provider.upper(), alias.upper())
    return result


def reveal_provider_in_text(text: str, mapping: ProviderMapping) -> str:
    """
    Replace aliases with real provider names in text.

    Handles case variations: Aleph, ALEPH, aleph -> claude
    """
    result = text
    for alias in ALIASES:
        provider = mapping.get_provider(alias)
        # Replace all case variations
        result = result.replace(alias, provider)
        result = result.replace(alias.title(), provider.title())
        result = result.replace(alias.upper(), provider.upper())
    return result
