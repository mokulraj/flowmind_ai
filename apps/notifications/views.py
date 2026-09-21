from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import Notification
from .serializers import NotificationSerializer
from .services.notification_service import (
    NotificationService,
    NotificationServiceError,
)


class NotificationListView(APIView):
    """
    List notifications belonging to the authenticated user.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization")
        unread_only = request.query_params.get("unread")

        queryset = Notification.objects.filter(
            recipient=request.user,
        ).select_related(
            "organization",
            "recipient",
            "workflow",
        )

        if organization_id:
            queryset = queryset.filter(
                organization_id=organization_id,
            )

        if unread_only and unread_only.lower() == "true":
            queryset = queryset.filter(is_read=False)

        serializer = NotificationSerializer(
            queryset,
            many=True,
        )

        return Response(serializer.data)


class NotificationUnreadCountView(APIView):
    """
    Return the unread notification count for the authenticated user.
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        organization_id = request.query_params.get("organization")

        queryset = Notification.objects.filter(
            recipient=request.user,
            is_read=False,
        )

        if organization_id:
            queryset = queryset.filter(
                organization_id=organization_id,
            )

        return Response(
            {
                "count": queryset.count(),
            }
        )


class NotificationMarkReadView(APIView):
    """
    Mark one notification as read.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            notification = Notification.objects.get(
                pk=pk,
                recipient=request.user,
            )
        except Notification.DoesNotExist:
            return Response(
                {
                    "detail": "Notification not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            NotificationService.mark_as_read(notification)
        except NotificationServiceError as exc:
            return Response(
                {
                    "detail": str(exc)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            NotificationSerializer(notification).data,
            status=status.HTTP_200_OK,
        )


class NotificationMarkUnreadView(APIView):
    """
    Mark one notification as unread.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            notification = Notification.objects.get(
                pk=pk,
                recipient=request.user,
            )
        except Notification.DoesNotExist:
            return Response(
                {
                    "detail": "Notification not found."
                },
                status=status.HTTP_404_NOT_FOUND,
            )

        try:
            NotificationService.mark_as_unread(notification)
        except NotificationServiceError as exc:
            return Response(
                {
                    "detail": str(exc)
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            NotificationSerializer(notification).data,
            status=status.HTTP_200_OK,
        )