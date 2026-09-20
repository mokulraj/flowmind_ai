from django.contrib import admin

from .models import (
    Workflow,
    WorkflowConnection,
    WorkflowStep,
)


class WorkflowStepInline(admin.TabularInline):
    model = WorkflowStep
    extra = 0

    ordering = (
        "order",
    )


class WorkflowConnectionInline(admin.TabularInline):
    model = WorkflowConnection
    extra = 0


@admin.register(Workflow)
class WorkflowAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "organization",
        "category",
        "status",
        "created_by",
        "created_at",
    )

    list_filter = (
        "status",
        "category",
        "organization",
    )

    search_fields = (
        "name",
        "description",
        "organization__name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    autocomplete_fields = (
        "organization",
        "created_by",
    )

    inlines = [
        WorkflowStepInline,
        WorkflowConnectionInline,
    ]


@admin.register(WorkflowStep)
class WorkflowStepAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "workflow",
        "order",
        "expected_duration",
        "department",
        "responsible_role",
    )

    list_filter = (
        "department",
        "workflow",
    )

    search_fields = (
        "name",
        "workflow__name",
        "department",
        "responsible_role",
    )

    ordering = (
        "workflow",
        "order",
    )

    autocomplete_fields = (
        "workflow",
    )


@admin.register(WorkflowConnection)
class WorkflowConnectionAdmin(admin.ModelAdmin):
    list_display = (
        "workflow",
        "source_step",
        "target_step",
        "condition",
    )

    list_filter = (
        "workflow",
    )

    search_fields = (
        "workflow__name",
        "source_step__name",
        "target_step__name",
    )

    autocomplete_fields = (
        "workflow",
        "source_step",
        "target_step",
    )