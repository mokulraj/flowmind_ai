from django.db import models


class Recommendation(models.Model):
    class RecommendationType(models.TextChoices):
        BOTTLENECK = "BOTTLENECK", "Bottleneck"
        ANOMALY = "ANOMALY", "Anomaly"
        PREDICTION = "PREDICTION", "Prediction"
        DATA_QUALITY = "DATA_QUALITY", "Data Quality"
        PROCESS = "PROCESS", "Process Improvement"
        CAPACITY = "CAPACITY", "Capacity"
        AUTOMATION = "AUTOMATION", "Automation"
        OTHER = "OTHER", "Other"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    class Status(models.TextChoices):
        NEW = "NEW", "New"
        REVIEWED = "REVIEWED", "Reviewed"
        ACCEPTED = "ACCEPTED", "Accepted"
        REJECTED = "REJECTED", "Rejected"
        COMPLETED = "COMPLETED", "Completed"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="recommendations",
    )

    workflow = models.ForeignKey(
        "workflows.Workflow",
        on_delete=models.CASCADE,
        related_name="recommendations",
        null=True,
        blank=True,
    )

    title = models.CharField(max_length=255)

    description = models.TextField()

    recommendation_type = models.CharField(
        max_length=30,
        choices=RecommendationType.choices,
        default=RecommendationType.OTHER,
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.NEW,
    )

    evidence = models.JSONField(
        default=dict,
        blank=True,
    )

    expected_impact = models.TextField(
        blank=True,
    )

    ai_explanation = models.TextField(
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
                fields=["organization", "workflow"],
            ),
            models.Index(
                fields=["organization", "priority"],
            ),
            models.Index(
                fields=["organization", "status"],
            ),
            models.Index(
                fields=["organization", "recommendation_type"],
            ),
        ]

    def __str__(self):
        return self.title