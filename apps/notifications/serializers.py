from rest_framework import serializers

from .models import Notification


class NotificationSerializer(serializers.ModelSerializer):
    organization_name = serializers.CharField(
        source="organization.name",
        read_only=True,
    )
    recipient_username = serializers.CharField(
        source="recipient.username",
        read_only=True,
        allow_null=True,
    )
    workflow_name = serializers.CharField(
        source="workflow.name",
        read_only=True,
        allow_null=True,
    )

    class Meta:
        model = Notification
        fields = [
            "id",
            "organization",
            "organization_name",
            "recipient",
            "recipient_username",
            "workflow",
            "workflow_name",
            "notification_type",
            "priority",
            "title",
            "message",
            "is_read",
            "related_object_type",
            "related_object_id",
            "created_at",
            "read_at",
        ]
        read_only_fields = [
            "id",
            "organization",
            "organization_name",
            "recipient",
            "recipient_username",
            "workflow",
            "workflow_name",
            "notification_type",
            "priority",
            "title",
            "message",
            "is_read",
            "related_object_type",
            "related_object_id",
            "created_at",
            "read_at",
        ]