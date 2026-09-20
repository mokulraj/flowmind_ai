from django.contrib import admin

from .models import Recommendation


@admin.register(Recommendation)
class RecommendationAdmin(admin.ModelAdmin):
    list_display = [
        "title",
        "organization",
        "workflow",
        "recommendation_type",
        "priority",
        "status",
        "created_at",
    ]

    list_filter = [
        "recommendation_type",
        "priority",
        "status",
        "created_at",
    ]

    search_fields = [
        "title",
        "description",
        "expected_impact",
        "ai_explanation",
        "organization__name",
        "workflow__name",
    ]

    readonly_fields = [
        "created_at",
        "updated_at",
    ]