from rest_framework import serializers

from .models import AuditLog


class AuditLogSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        source="organization.name",
        read_only=True,
    )

    username = serializers.CharField(
        source="user.username",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = AuditLog

        fields = [
            "id",
            "organization",
            "organization_name",
            "user",
            "username",
            "action",
            "object_type",
            "object_id",
            "object_repr",
            "description",
            "metadata",
            "ip_address",
            "user_agent",
            "created_at",
        ]

        read_only_fields = [
            "id",
            "organization",
            "organization_name",
            "user",
            "username",
            "action",
            "object_type",
            "object_id",
            "object_repr",
            "description",
            "metadata",
            "ip_address",
            "user_agent",
            "created_at",
        ]