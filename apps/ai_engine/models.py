from django.db import models


class KnowledgeDocument(models.Model):
    class SourceType(models.TextChoices):
        WORKFLOW = "WORKFLOW", "Workflow"
        DATASET = "DATASET", "Dataset"
        REPORT = "REPORT", "Report"
        MANUAL = "MANUAL", "Manual"
        OTHER = "OTHER", "Other"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="knowledge_documents",
    )

    title = models.CharField(max_length=255)

    source_type = models.CharField(
        max_length=20,
        choices=SourceType.choices,
        default=SourceType.OTHER,
    )

    source_reference = models.CharField(
        max_length=255,
        blank=True,
    )

    content = models.TextField()

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["organization", "source_type"]
            ),
        ]

    def __str__(self):
        return self.title


class KnowledgeChunk(models.Model):
    document = models.ForeignKey(
        KnowledgeDocument,
        on_delete=models.CASCADE,
        related_name="chunks",
    )

    chunk_index = models.PositiveIntegerField()

    content = models.TextField()

    token_count = models.PositiveIntegerField(
        default=0,
    )

    embedding = models.JSONField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["chunk_index"]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "document",
                    "chunk_index",
                ],
                name="unique_document_chunk_index",
            ),
        ]

        indexes = [
            models.Index(
                fields=[
                    "document",
                    "chunk_index",
                ],
            ),
        ]

    def __str__(self):
        return (
            f"{self.document.title} - "
            f"Chunk {self.chunk_index}"
        )