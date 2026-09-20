from apps.ai_engine.models import KnowledgeChunk
from apps.ai_engine.services.embeddings import (
    EmbeddingError,
    EmbeddingService,
)


class KnowledgeEmbeddingError(Exception):
    """Raised when knowledge chunk embedding fails."""


class KnowledgeEmbeddingService:
    """
    Generates and stores embeddings for KnowledgeChunk records.
    """

    def __init__(self, embedding_service=None):
        self.embedding_service = (
            embedding_service
            or EmbeddingService()
        )

    def embed_chunk(self, chunk):
        """
        Generate and store an embedding for one chunk.

        Returns:
            KnowledgeChunk instance with embedding populated.
        """

        if not isinstance(chunk, KnowledgeChunk):
            raise KnowledgeEmbeddingError(
                "chunk must be a KnowledgeChunk instance."
            )

        content = (chunk.content or "").strip()

        if not content:
            raise KnowledgeEmbeddingError(
                "Knowledge chunk content cannot be empty."
            )

        try:
            embedding = self.embedding_service.embed(
                content
            )
        except EmbeddingError as exc:
            raise KnowledgeEmbeddingError(
                str(exc)
            ) from exc

        chunk.embedding = embedding
        chunk.save(
            update_fields=["embedding"]
        )

        return chunk

    def embed_document(self, document):
        """
        Generate embeddings for every chunk belonging to a
        knowledge document.

        Returns:
            Dictionary containing the document, chunks processed,
            and generated embeddings.
        """

        if document is None:
            raise KnowledgeEmbeddingError(
                "document cannot be None."
            )

        chunks = list(
            document.chunks.all().order_by(
                "chunk_index"
            )
        )

        if not chunks:
            raise KnowledgeEmbeddingError(
                "Knowledge document has no chunks."
            )

        embedded_chunks = []

        for chunk in chunks:
            embedded_chunk = self.embed_chunk(
                chunk
            )

            embedded_chunks.append(
                embedded_chunk
            )

        return {
            "document": document,
            "chunk_count": len(
                embedded_chunks
            ),
            "chunks": embedded_chunks,
        }

    def embed_chunks(self, chunks):
        """
        Generate embeddings for an iterable of chunks.
        """

        if chunks is None:
            raise KnowledgeEmbeddingError(
                "chunks cannot be None."
            )

        chunks = list(chunks)

        if not chunks:
            raise KnowledgeEmbeddingError(
                "chunks cannot be empty."
            )

        embedded_chunks = []

        for chunk in chunks:
            embedded_chunks.append(
                self.embed_chunk(chunk)
            )

        return embedded_chunks