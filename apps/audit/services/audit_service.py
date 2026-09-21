from django.db import transaction

from ..models import AuditLog


class AuditLogServiceError(Exception):
    """Raised when an audit log operation cannot be completed."""


class AuditLogService:
    @staticmethod
    def _validate_organization(organization):
        if organization is None:
            raise AuditLogServiceError(
                "Organization is required."
            )

    @staticmethod
    def _validate_user(organization, user):
        if user is None:
            return

        if not user.is_active:
            raise AuditLogServiceError(
                "Audit user must be an active user."
            )

        if not organization.members.filter(
            user=user
        ).exists():
            raise AuditLogServiceError(
                "User does not belong to the audit organization."
            )

    @staticmethod
    def _validate_action(action):
        valid_actions = {
            value
            for value, _label in AuditLog.Action.choices
        }

        if action not in valid_actions:
            raise AuditLogServiceError(
                f"Invalid audit action: {action}"
            )

    @staticmethod
    def _validate_object_id(object_id):
        if object_id is None:
            return

        if isinstance(object_id, bool):
            raise AuditLogServiceError(
                "Object ID must be a positive integer."
            )

        try:
            object_id = int(object_id)
        except (TypeError, ValueError):
            raise AuditLogServiceError(
                "Object ID must be a positive integer."
            )

        if object_id <= 0:
            raise AuditLogServiceError(
                "Object ID must be a positive integer."
            )

    @classmethod
    @transaction.atomic
    def create(
        cls,
        *,
        organization,
        action,
        object_type,
        object_id=None,
        object_repr="",
        description="",
        metadata=None,
        user=None,
        ip_address=None,
        user_agent="",
    ):
        cls._validate_organization(organization)
        cls._validate_user(organization, user)
        cls._validate_action(action)
        cls._validate_object_id(object_id)

        if not object_type or not object_type.strip():
            raise AuditLogServiceError(
                "Object type is required."
            )

        if metadata is None:
            metadata = {}

        if not isinstance(metadata, dict):
            raise AuditLogServiceError(
                "Audit metadata must be a dictionary."
            )

        if object_id is not None:
            object_id = int(object_id)

        return AuditLog.objects.create(
            organization=organization,
            user=user,
            action=action,
            object_type=object_type.strip(),
            object_id=object_id,
            object_repr=(object_repr or "").strip(),
            description=(description or "").strip(),
            metadata=metadata,
            ip_address=ip_address,
            user_agent=(user_agent or "").strip(),
        )