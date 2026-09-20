from django.contrib import admin

from apps.simulations.models import Simulation


@admin.register(Simulation)
class SimulationAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "organization",
        "workflow",
        "workload_change_percent",
        "status",
        "created_at",
    )

    list_filter = (
        "status",
        "organization",
        "workflow",
    )

    search_fields = (
        "name",
        "description",
        "notes",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    ordering = (
        "-created_at",
    )