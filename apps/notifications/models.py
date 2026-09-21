from django.conf import settings
from django.db import models


class Notification(models.Model):
    class NotificationType(models.TextChoices):
        BOTTLENECK = "BOTTLENECK", "Bottleneck"
        ANOMALY = "ANOMALY", "Anomaly"
        PREDICTION = "PREDICTION", "Prediction"
        RECOMMENDATION = "RECOMMENDATION", "Recommendation"
        SIMULATION = "SIMULATION", "Simulation"
        REPORT = "REPORT", "Report"
        AI_INSIGHT = "AI_INSIGHT", "AI Insight"
        SYSTEM = "SYSTEM", "System"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    organization = models.ForeignKey(
        "organizations.Organization",
        on_delete=models.CASCADE,
        related_name="notifications",
    )

    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )

    workflow = models.ForeignKey(
        "workflows.Workflow",
        on_delete=models.CASCADE,
        related_name="notifications",
        null=True,
        blank=True,
    )

    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
    )

    priority = models.CharField(
        max_length=20,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )

    title = models.CharField(max_length=255)

    message = models.TextField()

    is_read = models.BooleanField(default=False)

    related_object_type = models.CharField(
        max_length=100,
        blank=True,
    )

    related_object_id = models.PositiveBigIntegerField(
        null=True,
        blank=True,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    read_at = models.DateTimeField(
        null=True,
        blank=True,
    )

    class Meta:
        ordering = ["-created_at"]

        indexes = [
            models.Index(
                fields=["organization", "-created_at"]
            ),
            models.Index(
                fields=["recipient", "-created_at"]
            ),
            models.Index(
                fields=["organization", "is_read"]
            ),
            models.Index(
                fields=["organization", "notification_type"]
            ),
        ]

    def __str__(self):
        return self.title