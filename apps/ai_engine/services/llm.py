from abc import ABC, abstractmethod


class LLMError(Exception):
    """Raised when an LLM operation fails."""


class BaseLLMProvider(ABC):
    """Abstract interface for all LLM providers."""

    @abstractmethod
    def generate(
        self,
        prompt,
        system_prompt=None,
        temperature=0.2,
        max_tokens=1000,
    ):
        """Generate a response from the configured LLM provider."""
        raise NotImplementedError


class MockLLMProvider(BaseLLMProvider):
    """Development provider used until a production LLM is connected."""

    def generate(
        self,
        prompt,
        system_prompt=None,
        temperature=0.2,
        max_tokens=1000,
    ):
        if prompt is None or not str(prompt).strip():
            raise LLMError("Prompt cannot be empty.")

        return (
            "Mock AI response generated successfully. "
            "The production LLM provider will be connected later."
        )


class LLMService:
    """Application-level service for interacting with an LLM provider."""

    def __init__(self, provider=None):
        self.provider = provider or MockLLMProvider()

    def generate(
        self,
        prompt,
        system_prompt=None,
        temperature=0.2,
        max_tokens=1000,
    ):
        if prompt is None or not str(prompt).strip():
            raise LLMError("Prompt cannot be empty.")

        return self.provider.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )