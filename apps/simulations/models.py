from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Simulation(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        RUNNING = "RUNNING", "Running"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="simulations",
    )

    workflow = models.ForeignKey(
        "workflows.Workflow",
        on_delete=models.CASCADE,
        related_name="simulations",
    )

    name = models.CharField(max_length=255)

    description = models.TextField(blank=True)

    workload_change_percent = models.FloatField(
        default=0.0,
        validators=[
            MinValueValidator(-100.0),
        ],
        help_text="Percentage change in workload compared with the baseline.",
    )

    baseline_event_count = models.PositiveIntegerField(default=0)

    projected_event_count = models.PositiveIntegerField(default=0)

    baseline_avg_duration = models.FloatField(default=0.0)

    projected_avg_duration = models.FloatField(default=0.0)

    baseline_total_duration = models.FloatField(default=0.0)

    projected_total_duration = models.FloatField(default=0.0)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    results = models.JSONField(default=dict, blank=True)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["organization", "created_at"],
                name="sim_org_created_idx",
            ),
            models.Index(
                fields=["organization", "workflow"],
                name="sim_org_workflow_idx",
            ),
            models.Index(
                fields=["status"],
                name="sim_status_idx",
            ),
        ]

    def __str__(self):
        return self.name