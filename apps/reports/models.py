from django.conf import settings
from django.core.validators import MinLengthValidator
from django.db import models


class Report(models.Model):
    class ReportType(models.TextChoices):
        WORKFLOW_SUMMARY = "WORKFLOW_SUMMARY", "Workflow Summary"
        ANALYTICS = "ANALYTICS", "Analytics"
        BOTTLENECK = "BOTTLENECK", "Bottleneck Analysis"
        ANOMALY = "ANOMALY", "Anomaly Analysis"
        PREDICTION = "PREDICTION", "Prediction Analysis"
        RECOMMENDATION = "RECOMMENDATION", "Recommendation Report"
        SIMULATION = "SIMULATION", "Simulation Report"
        AI_INSIGHT = "AI_INSIGHT", "AI Insight"
        CUSTOM = "CUSTOM", "Custom Report"

    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        GENERATING = "GENERATING", "Generating"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"

    class Format(models.TextChoices):
        HTML = "HTML", "HTML"
        JSON = "JSON", "JSON"
        PDF = "PDF", "PDF"
        CSV = "CSV", "CSV"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="reports",
    )

    workflow = models.ForeignKey(
        "workflows.Workflow",
        on_delete=models.CASCADE,
        related_name="reports",
        null=True,
        blank=True,
    )

    dataset = models.ForeignKey(
        "datasets.Dataset",
        on_delete=models.SET_NULL,
        related_name="reports",
        null=True,
        blank=True,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="created_reports",
        null=True,
        blank=True,
    )

    title = models.CharField(
        max_length=255,
        validators=[MinLengthValidator(1)],
    )

    description = models.TextField(
        blank=True,
    )

    report_type = models.CharField(
        max_length=40,
        choices=ReportType.choices,
        default=ReportType.WORKFLOW_SUMMARY,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    output_format = models.CharField(
        max_length=10,
        choices=Format.choices,
        default=Format.HTML,
    )

    content = models.TextField(
        blank=True,
    )

    data = models.JSONField(
        default=dict,
        blank=True,
    )

    error_message = models.TextField(
        blank=True,
    )

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
                fields=["organization", "-created_at"],
                name="report_org_created_idx",
            ),
            models.Index(
                fields=["organization", "status"],
                name="report_org_status_idx",
            ),
            models.Index(
                fields=["organization", "report_type"],
                name="report_org_type_idx",
            ),
            models.Index(
                fields=["organization", "workflow"],
                name="report_org_workflow_idx",
            ),
            models.Index(
                fields=["organization", "dataset"],
                name="report_org_dataset_idx",
            ),
        ]

    def __str__(self):
        return self.title