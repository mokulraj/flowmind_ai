from apps.ai_engine.models import KnowledgeChunk, KnowledgeDocument


class ChunkingError(Exception):
    """Raised when knowledge document chunking fails."""


class KnowledgeChunkingService:
    """
    Splits knowledge document content into chunks and stores them
    as KnowledgeChunk records.
    """

    def __init__(self, chunk_size=500, chunk_overlap=50):
        if chunk_size <= 0:
            raise ChunkingError("chunk_size must be greater than zero.")

        if chunk_overlap < 0:
            raise ChunkingError("chunk_overlap cannot be negative.")

        if chunk_overlap >= chunk_size:
            raise ChunkingError(
                "chunk_overlap must be smaller than chunk_size."
            )

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def chunk_document(self, document):
        """
        Split a KnowledgeDocument into chunks and save them.

        Returns:
            dict containing document, chunk count, and created chunks.
        """

        if not isinstance(document, KnowledgeDocument):
            raise ChunkingError(
                "document must be a KnowledgeDocument instance."
            )

        content = (document.content or "").strip()

        if not content:
            raise ChunkingError(
                "Knowledge document content cannot be empty."
            )

        document.chunks.all().delete()

        chunks = self._split_text(content)

        created_chunks = []

        for index, chunk_content in enumerate(chunks):
            chunk = KnowledgeChunk.objects.create(
                document=document,
                chunk_index=index,
                content=chunk_content,
                token_count=self._estimate_token_count(chunk_content),
            )

            created_chunks.append(chunk)

        return {
            "document": document,
            "chunk_count": len(created_chunks),
            "chunks": created_chunks,
        }

    def _split_text(self, text):
        """
        Split text into overlapping character-based chunks.

        Character-based chunking is intentionally used at this stage.
        Embedding/token-aware chunking will be added later.
        """

        if not text:
            return []

        chunks = []
        start = 0
        text_length = len(text)

        while start < text_length:
            end = min(start + self.chunk_size, text_length)

            chunk = text[start:end].strip()

            if chunk:
                chunks.append(chunk)

            if end >= text_length:
                break

            start = end - self.chunk_overlap

        return chunks

    def _estimate_token_count(self, text):
        """
        Provide a lightweight token-count estimate.

        This is intentionally approximate. A real tokenizer will be
        introduced when the embedding/LLM layer is connected.
        """

        if not text:
            return 0

        return max(1, len(text.split()))