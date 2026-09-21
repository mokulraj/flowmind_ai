from django.db import transaction
from django.utils import timezone

from apps.organizations.models import OrganizationMember

from ..models import Notification


class NotificationServiceError(Exception):
    """Raised when a notification operation cannot be completed."""


class NotificationService:
    """
    Business logic for creating and managing notifications.
    """

    @staticmethod
    def _validate_organization(organization):
        if organization is None:
            raise NotificationServiceError(
                "Organization is required."
            )

    @staticmethod
    def _validate_recipient(organization, recipient):
        if recipient is None:
            return

        if not recipient.is_active:
            raise NotificationServiceError(
                "Recipient must be an active user."
            )

        if not OrganizationMember.objects.filter(
            organization=organization,
            user=recipient,
        ).exists():
            raise NotificationServiceError(
                "Recipient does not belong to the notification organization."
            )

    @staticmethod
    def _validate_workflow(organization, workflow):
        if workflow is None:
            return

        if workflow.organization_id != organization.id:
            raise NotificationServiceError(
                "Workflow does not belong to the notification organization."
            )

    @classmethod
    @transaction.atomic
    def create(
        cls,
        *,
        organization,
        notification_type,
        title,
        message,
        priority=Notification.Priority.MEDIUM,
        recipient=None,
        workflow=None,
        related_object_type="",
        related_object_id=None,
    ):
        cls._validate_organization(organization)

        cls._validate_recipient(
            organization,
            recipient,
        )

        cls._validate_workflow(
            organization,
            workflow,
        )

        if not title or not title.strip():
            raise NotificationServiceError(
                "Notification title is required."
            )

        if not message or not message.strip():
            raise NotificationServiceError(
                "Notification message is required."
            )

        valid_types = {
            value
            for value, _label
            in Notification.NotificationType.choices
        }

        if notification_type not in valid_types:
            raise NotificationServiceError(
                f"Invalid notification type: {notification_type}"
            )

        valid_priorities = {
            value
            for value, _label
            in Notification.Priority.choices
        }

        if priority not in valid_priorities:
            raise NotificationServiceError(
                f"Invalid notification priority: {priority}"
            )

        return Notification.objects.create(
            organization=organization,
            recipient=recipient,
            workflow=workflow,
            notification_type=notification_type,
            priority=priority,
            title=title.strip(),
            message=message.strip(),
            related_object_type=related_object_type,
            related_object_id=related_object_id,
        )

    @staticmethod
    def mark_as_read(notification):
        if not isinstance(notification, Notification):
            raise NotificationServiceError(
                "A valid Notification instance is required."
            )

        if not notification.is_read:
            notification.is_read = True
            notification.read_at = timezone.now()

            notification.save(
                update_fields=[
                    "is_read",
                    "read_at",
                ]
            )

        return notification

    @staticmethod
    def mark_as_unread(notification):
        if not isinstance(notification, Notification):
            raise NotificationServiceError(
                "A valid Notification instance is required."
            )

        notification.is_read = False
        notification.read_at = None

        notification.save(
            update_fields=[
                "is_read",
                "read_at",
            ]
        )

        return notification

    @staticmethod
    def unread_for_user(
        *,
        organization,
        recipient,
    ):
        if organization is None:
            raise NotificationServiceError(
                "Organization is required."
            )

        if recipient is None:
            raise NotificationServiceError(
                "Recipient is required."
            )

        return Notification.objects.filter(
            organization=organization,
            recipient=recipient,
            is_read=False,
        ).order_by("-created_at")

    @staticmethod
    def unread_count(
        *,
        organization,
        recipient,
    ):
        return NotificationService.unread_for_user(
            organization=organization,
            recipient=recipient,
        ).count()