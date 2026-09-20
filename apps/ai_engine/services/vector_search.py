import math

from apps.ai_engine.models import KnowledgeChunk
from apps.ai_engine.services.embeddings import (
    EmbeddingError,
    EmbeddingService,
)


class VectorSearchError(Exception):
    """Raised when vector similarity search fails."""


class KnowledgeVectorSearchService:
    """
    Searches knowledge chunks using cosine similarity.
    """

    def __init__(self, embedding_service=None):
        self.embedding_service = (
            embedding_service
            or EmbeddingService()
        )

    def search(
        self,
        query,
        organization,
        top_k=5,
    ):
        """
        Find the most relevant knowledge chunks for a query.

        Results are restricted to the supplied organization.
        """

        self._validate_query(query)
        self._validate_top_k(top_k)

        if organization is None:
            raise VectorSearchError(
                "organization cannot be None."
            )

        try:
            query_embedding = (
                self.embedding_service.embed(query)
            )
        except EmbeddingError as exc:
            raise VectorSearchError(
                str(exc)
            ) from exc

        chunks = (
            KnowledgeChunk.objects
            .filter(
                document__organization=organization,
            )
            .exclude(
                embedding__isnull=True,
            )
            .select_related("document")
        )

        results = []

        for chunk in chunks:
            if not chunk.embedding:
                continue

            similarity = self._cosine_similarity(
                query_embedding,
                chunk.embedding,
            )

            results.append(
                {
                    "chunk": chunk,
                    "document": chunk.document,
                    "similarity": similarity,
                }
            )

        results.sort(
            key=lambda item: item["similarity"],
            reverse=True,
        )

        return results[:top_k]

    def _validate_query(self, query):
        if query is None:
            raise VectorSearchError(
                "query cannot be None."
            )

        if not str(query).strip():
            raise VectorSearchError(
                "query cannot be empty."
            )

    def _validate_top_k(self, top_k):
        if not isinstance(top_k, int):
            raise VectorSearchError(
                "top_k must be an integer."
            )

        if top_k <= 0:
            raise VectorSearchError(
                "top_k must be greater than zero."
            )

    @staticmethod
    def _cosine_similarity(vector_a, vector_b):
        if not isinstance(vector_a, (list, tuple)):
            raise VectorSearchError(
                "First vector must be a list or tuple."
            )

        if not isinstance(vector_b, (list, tuple)):
            raise VectorSearchError(
                "Second vector must be a list or tuple."
            )

        if len(vector_a) != len(vector_b):
            raise VectorSearchError(
                "Vectors must have the same dimensions."
            )

        if not vector_a:
            raise VectorSearchError(
                "Vectors cannot be empty."
            )

        try:
            dot_product = sum(
                float(a) * float(b)
                for a, b in zip(
                    vector_a,
                    vector_b,
                )
            )

            magnitude_a = math.sqrt(
                sum(
                    float(value) ** 2
                    for value in vector_a
                )
            )

            magnitude_b = math.sqrt(
                sum(
                    float(value) ** 2
                    for value in vector_b
                )
            )
        except (TypeError, ValueError) as exc:
            raise VectorSearchError(
                "Vectors must contain numeric values."
            ) from exc

        if magnitude_a == 0 or magnitude_b == 0:
            raise VectorSearchError(
                "Vectors cannot have zero magnitude."
            )

        return dot_product / (
            magnitude_a * magnitude_b
        )