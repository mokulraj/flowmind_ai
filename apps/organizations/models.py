from django.conf import settings
from django.db import models


class Organization(models.Model):
    """
    Represents a FlowMind customer organization.

    All organization-owned resources will eventually reference
    this model to provide tenant isolation.
    """

    name = models.CharField(
        max_length=255,
    )

    slug = models.SlugField(
        max_length=255,
        unique=True,
    )

    industry = models.CharField(
        max_length=255,
        blank=True,
    )

    description = models.TextField(
        blank=True,
    )

    logo = models.ImageField(
        upload_to="organizations/logos/",
        blank=True,
        null=True,
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["slug"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        return self.name


class OrganizationMember(models.Model):
    """
    Connects a FlowMind user to an organization.

    A user can belong to multiple organizations, which gives us
    flexibility for future multi-tenant use cases.
    """

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        MANAGER = "MANAGER", "Manager"
        ANALYST = "ANALYST", "Analyst"
        VIEWER = "VIEWER", "Viewer"

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name="members",
    )

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="organization_memberships",
    )

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER,
    )

    joined_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["organization", "user"],
                name="unique_organization_user",
            ),
        ]

        indexes = [
            models.Index(
                fields=["organization", "role"],
            ),
            models.Index(
                fields=["user", "role"],
            ),
        ]

        ordering = ["organization", "user"]

    def __str__(self):
        return (
            f"{self.user.email} - "
            f"{self.organization.name} - "
            f"{self.role}"
        )