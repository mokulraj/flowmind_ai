from django.contrib import admin

from .models import (
    KnowledgeChunk,
    KnowledgeDocument,
)


class KnowledgeChunkInline(
    admin.TabularInline
):
    model = KnowledgeChunk
    extra = 0
    readonly_fields = [
        "created_at",
    ]


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(
    admin.ModelAdmin
):
    list_display = [
        "title",
        "organization",
        "source_type",
        "source_reference",
        "created_at",
    ]

    list_filter = [
        "source_type",
        "created_at",
    ]

    search_fields = [
        "title",
        "content",
        "source_reference",
    ]

    inlines = [
        KnowledgeChunkInline,
    ]


@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(
    admin.ModelAdmin
):
    list_display = [
        "document",
        "chunk_index",
        "token_count",
        "created_at",
    ]

    list_filter = [
        "created_at",
    ]

    search_fields = [
        "content",
        "document__title",
    ]