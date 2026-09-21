from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.organizations.models import OrganizationMember

from .models import AuditLog
from .serializers import AuditLogSerializer


class AuditLogListView(APIView):
    permission_classes = [IsAuthenticated]

    ORGANIZATION_AUDIT_ROLES = {
        OrganizationMember.Role.ADMIN,
        OrganizationMember.Role.MANAGER,
    }

    def get_user_role(self, user, organization_id=None):
        membership = OrganizationMember.objects.filter(
            user=user,
        )

        if organization_id:
            membership = membership.filter(
                organization_id=organization_id,
            )

        membership = membership.first()

        if membership is None:
            return None

        return membership.role

    def get(self, request):
        organization_id = request.query_params.get(
            "organization"
        )

        action = request.query_params.get(
            "action"
        )

        object_type = request.query_params.get(
            "object_type"
        )

        role = self.get_user_role(
            request.user,
            organization_id=organization_id,
        )

        if role is None:
            return Response(
                [],
                status=status.HTTP_200_OK,
            )

        if role in self.ORGANIZATION_AUDIT_ROLES:
            queryset = AuditLog.objects.filter(
                organization__members__user=request.user,
            )
        else:
            queryset = AuditLog.objects.filter(
                user=request.user,
            )

        if organization_id:
            queryset = queryset.filter(
                organization_id=organization_id,
            )

        if action:
            queryset = queryset.filter(
                action=action,
            )

        if object_type:
            queryset = queryset.filter(
                object_type=object_type,
            )

        queryset = queryset.select_related(
            "organization",
            "user",
        ).distinct()

        serializer = AuditLogSerializer(
            queryset,
            many=True,
        )

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )