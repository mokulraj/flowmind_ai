from abc import ABC, abstractmethod

import hashlib
import math


class EmbeddingError(Exception):
    """Raised when embedding generation fails."""


class BaseEmbeddingProvider(ABC):
    """Abstract interface for embedding providers."""

    @abstractmethod
    def embed(self, text):
        """Generate an embedding vector for one piece of text."""
        raise NotImplementedError

    def embed_many(self, texts):
        """Generate embeddings for multiple texts."""
        return [self.embed(text) for text in texts]


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """
    Deterministic local embedding provider for development and testing.

    This is NOT a production semantic embedding model.
    It gives us a stable vector representation so the RAG architecture
    can be developed and tested before connecting a real provider.
    """

    def __init__(self, dimensions=32):
        if dimensions <= 0:
            raise EmbeddingError(
                "Embedding dimensions must be greater than zero."
            )

        self.dimensions = dimensions

    def embed(self, text):
        if text is None or not str(text).strip():
            raise EmbeddingError(
                "Text cannot be empty."
            )

        normalized_text = str(text).strip().lower()

        vector = []

        for index in range(self.dimensions):
            digest = hashlib.sha256(
                f"{index}:{normalized_text}".encode("utf-8")
            ).digest()

            value = int.from_bytes(
                digest[:8],
                byteorder="big",
                signed=False,
            )

            normalized_value = (
                (value / 2**64) * 2
            ) - 1

            vector.append(normalized_value)

        return self._normalize(vector)

    def _normalize(self, vector):
        magnitude = math.sqrt(
            sum(value * value for value in vector)
        )

        if magnitude == 0:
            return vector

        return [
            value / magnitude
            for value in vector
        ]


class EmbeddingService:
    """Application-level service for embedding generation."""

    def __init__(self, provider=None):
        self.provider = provider or MockEmbeddingProvider()

    def embed(self, text):
        if text is None or not str(text).strip():
            raise EmbeddingError(
                "Text cannot be empty."
            )

        return self.provider.embed(text)

    def embed_many(self, texts):
        if texts is None:
            raise EmbeddingError(
                "texts cannot be None."
            )

        if not isinstance(texts, (list, tuple)):
            raise EmbeddingError(
                "texts must be a list or tuple."
            )

        if any(
            text is None or not str(text).strip()
            for text in texts
        ):
            raise EmbeddingError(
                "All texts must contain content."
            )

        return self.provider.embed_many(texts)