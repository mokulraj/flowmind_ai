from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from apps.notifications.models import Notification
from apps.notifications.serializers import NotificationSerializer
from apps.notifications.services.notification_service import (
    NotificationService,
    NotificationServiceError,
)
from apps.notifications.services.recommendation_notifications import (
    RecommendationNotificationService,
)
from apps.notifications.views import (
    NotificationListView,
    NotificationMarkReadView,
    NotificationMarkUnreadView,
    NotificationUnreadCountView,
)
from apps.organizations.models import Organization, OrganizationMember
from apps.recommendations.models import Recommendation
from apps.workflows.models import Workflow


User = get_user_model()


class NotificationModelTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Notification Test Organization",
            slug="notification-test-organization",
        )

        self.user = User.objects.create_user(
            username="notification_user",
            email="notification@example.com",
            password="testpass123",
        )

        OrganizationMember.objects.create(
            organization=self.organization,
            user=self.user,
            role="VIEWER",
        )

        self.workflow = Workflow.objects.create(
            organization=self.organization,
            name="Notification Workflow",
            description="Workflow used for notification tests.",
            created_by=self.user,
        )

    def test_notification_creation(self):
        notification = Notification.objects.create(
            organization=self.organization,
            recipient=self.user,
            workflow=self.workflow,
            notification_type=Notification.NotificationType.BOTTLENECK,
            priority=Notification.Priority.HIGH,
            title="Bottleneck detected",
            message="Verification is taking longer than expected.",
        )

        self.assertEqual(notification.organization, self.organization)
        self.assertEqual(notification.recipient, self.user)
        self.assertEqual(notification.workflow, self.workflow)
        self.assertEqual(
            notification.notification_type,
            Notification.NotificationType.BOTTLENECK,
        )
        self.assertEqual(
            notification.priority,
            Notification.Priority.HIGH,
        )
        self.assertFalse(notification.is_read)
        self.assertIsNone(notification.read_at)

    def test_notification_defaults_to_medium_priority(self):
        notification = Notification.objects.create(
            organization=self.organization,
            title="System notification",
            message="Test notification.",
            notification_type=Notification.NotificationType.SYSTEM,
        )

        self.assertEqual(
            notification.priority,
            Notification.Priority.MEDIUM,
        )
        self.assertFalse(notification.is_read)

    def test_notification_can_have_no_recipient(self):
        notification = Notification.objects.create(
            organization=self.organization,
            notification_type=Notification.NotificationType.SYSTEM,
            title="Organization notification",
            message="This notification is for the organization.",
        )

        self.assertIsNone(notification.recipient)

    def test_notification_can_have_no_workflow(self):
        notification = Notification.objects.create(
            organization=self.organization,
            notification_type=Notification.NotificationType.REPORT,
            title="Report generated",
            message="Your report has been generated.",
        )

        self.assertIsNone(notification.workflow)

    def test_notification_string_representation(self):
        notification = Notification.objects.create(
            organization=self.organization,
            notification_type=Notification.NotificationType.AI_INSIGHT,
            title="AI insight available",
            message="A new insight is available.",
        )

        self.assertEqual(
            str(notification),
            "AI insight available",
        )

    def test_notification_related_object_fields(self):
        notification = Notification.objects.create(
            organization=self.organization,
            notification_type=Notification.NotificationType.RECOMMENDATION,
            title="Recommendation available",
            message="A recommendation has been generated.",
            related_object_type="recommendation",
            related_object_id=123,
        )

        self.assertEqual(
            notification.related_object_type,
            "recommendation",
        )
        self.assertEqual(
            notification.related_object_id,
            123,
        )

    def test_notification_can_be_marked_read(self):
        notification = Notification.objects.create(
            organization=self.organization,
            notification_type=Notification.NotificationType.ANOMALY,
            title="Anomaly detected",
            message="An anomaly was detected.",
        )

        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()

        notification.refresh_from_db()

        self.assertTrue(notification.is_read)
        self.assertIsNotNone(notification.read_at)

    def test_notification_belongs_to_organization(self):
        notification = Notification.objects.create(
            organization=self.organization,
            notification_type=Notification.NotificationType.SIMULATION,
            title="Simulation completed",
            message="Simulation completed successfully.",
        )

        self.assertEqual(
            notification.organization_id,
            self.organization.id,
        )


class NotificationServiceTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Service Test Organization",
            slug="service-test-organization",
        )

        self.other_organization = Organization.objects.create(
            name="Other Service Organization",
            slug="other-service-organization",
        )

        self.user = User.objects.create_user(
            username="service_user",
            email="service@example.com",
            password="testpass123",
        )

        OrganizationMember.objects.create(
            organization=self.organization,
            user=self.user,
            role="VIEWER",
        )

        self.other_user = User.objects.create_user(
            username="other_service_user",
            email="other-service@example.com",
            password="testpass123",
        )

        OrganizationMember.objects.create(
            organization=self.other_organization,
            user=self.other_user,
            role="VIEWER",
        )

        self.workflow = Workflow.objects.create(
            organization=self.organization,
            name="Service Workflow",
            description="Workflow used for service tests.",
            created_by=self.user,
        )

        self.other_workflow = Workflow.objects.create(
            organization=self.other_organization,
            name="Other Service Workflow",
            description="Workflow from another organization.",
            created_by=self.other_user,
        )

    def test_create_notification(self):
        notification = NotificationService.create(
            organization=self.organization,
            recipient=self.user,
            workflow=self.workflow,
            notification_type=Notification.NotificationType.BOTTLENECK,
            priority=Notification.Priority.HIGH,
            title="  Bottleneck detected  ",
            message="  Verification is delayed.  ",
        )

        self.assertEqual(notification.organization, self.organization)
        self.assertEqual(notification.recipient, self.user)
        self.assertEqual(notification.workflow, self.workflow)
        self.assertEqual(notification.title, "Bottleneck detected")
        self.assertEqual(notification.message, "Verification is delayed.")
        self.assertEqual(
            notification.priority,
            Notification.Priority.HIGH,
        )

    def test_create_notification_without_recipient(self):
        notification = NotificationService.create(
            organization=self.organization,
            notification_type=Notification.NotificationType.SYSTEM,
            title="System notification",
            message="System message.",
        )

        self.assertIsNone(notification.recipient)

    def test_create_notification_requires_organization(self):
        with self.assertRaises(NotificationServiceError):
            NotificationService.create(
                organization=None,
                notification_type=Notification.NotificationType.SYSTEM,
                title="Test",
                message="Test message.",
            )

    def test_create_notification_rejects_inactive_recipient(self):
        self.user.is_active = False
        self.user.save(update_fields=["is_active"])

        with self.assertRaisesMessage(
            NotificationServiceError,
            "Recipient must be an active user.",
        ):
            NotificationService.create(
                organization=self.organization,
                recipient=self.user,
                notification_type=Notification.NotificationType.SYSTEM,
                title="Test",
                message="Test message.",
            )

    def test_create_notification_rejects_cross_organization_recipient(self):
        with self.assertRaisesMessage(
            NotificationServiceError,
            "Recipient does not belong to the notification organization.",
        ):
            NotificationService.create(
                organization=self.organization,
                recipient=self.other_user,
                notification_type=Notification.NotificationType.SYSTEM,
                title="Test",
                message="Test message.",
            )

    def test_create_notification_rejects_cross_organization_workflow(self):
        with self.assertRaisesMessage(
            NotificationServiceError,
            "Workflow does not belong to the notification organization.",
        ):
            NotificationService.create(
                organization=self.organization,
                workflow=self.other_workflow,
                notification_type=Notification.NotificationType.SYSTEM,
                title="Test",
                message="Test message.",
            )

    def test_create_notification_rejects_invalid_type(self):
        with self.assertRaisesMessage(
            NotificationServiceError,
            "Invalid notification type: INVALID",
        ):
            NotificationService.create(
                organization=self.organization,
                notification_type="INVALID",
                title="Test",
                message="Test message.",
            )

    def test_create_notification_rejects_invalid_priority(self):
        with self.assertRaisesMessage(
            NotificationServiceError,
            "Invalid notification priority: INVALID",
        ):
            NotificationService.create(
                organization=self.organization,
                notification_type=Notification.NotificationType.SYSTEM,
                priority="INVALID",
                title="Test",
                message="Test message.",
            )

    def test_create_notification_requires_title(self):
        with self.assertRaisesMessage(
            NotificationServiceError,
            "Notification title is required.",
        ):
            NotificationService.create(
                organization=self.organization,
                notification_type=Notification.NotificationType.SYSTEM,
                title="   ",
                message="Test message.",
            )

    def test_create_notification_requires_message(self):
        with self.assertRaisesMessage(
            NotificationServiceError,
            "Notification message is required.",
        ):
            NotificationService.create(
                organization=self.organization,
                notification_type=Notification.NotificationType.SYSTEM,
                title="Test",
                message="   ",
            )

    def test_mark_as_read(self):
        notification = NotificationService.create(
            organization=self.organization,
            recipient=self.user,
            notification_type=Notification.NotificationType.SYSTEM,
            title="Test",
            message="Test message.",
        )

        result = NotificationService.mark_as_read(notification)

        self.assertTrue(result.is_read)
        self.assertIsNotNone(result.read_at)

    def test_mark_as_unread(self):
        notification = NotificationService.create(
            organization=self.organization,
            recipient=self.user,
            notification_type=Notification.NotificationType.SYSTEM,
            title="Test",
            message="Test message.",
        )

        notification.is_read = True
        notification.read_at = timezone.now()
        notification.save()

        result = NotificationService.mark_as_unread(notification)

        self.assertFalse(result.is_read)
        self.assertIsNone(result.read_at)

    def test_unread_for_user(self):
        first = NotificationService.create(
            organization=self.organization,
            recipient=self.user,
            notification_type=Notification.NotificationType.SYSTEM,
            title="First",
            message="First message.",
        )

        second = NotificationService.create(
            organization=self.organization,
            recipient=self.user,
            notification_type=Notification.NotificationType.ANOMALY,
            title="Second",
            message="Second message.",
        )

        NotificationService.mark_as_read(first)

        unread = list(
            NotificationService.unread_for_user(
                organization=self.organization,
                recipient=self.user,
            )
        )

        self.assertEqual(len(unread), 1)
        self.assertEqual(unread[0].id, second.id)

    def test_unread_count(self):
        NotificationService.create(
            organization=self.organization,
            recipient=self.user,
            notification_type=Notification.NotificationType.SYSTEM,
            title="First",
            message="First message.",
        )

        NotificationService.create(
            organization=self.organization,
            recipient=self.user,
            notification_type=Notification.NotificationType.ANOMALY,
            title="Second",
            message="Second message.",
        )

        self.assertEqual(
            NotificationService.unread_count(
                organization=self.organization,
                recipient=self.user,
            ),
            2,
        )

    def test_unread_notifications_are_isolated_by_organization(self):
        NotificationService.create(
            organization=self.organization,
            recipient=self.user,
            notification_type=Notification.NotificationType.SYSTEM,
            title="Organization A",
            message="Organization A message.",
        )

        other_notification = Notification.objects.create(
            organization=self.other_organization,
            recipient=self.other_user,
            notification_type=Notification.NotificationType.SYSTEM,
            title="Organization B",
            message="Organization B message.",
        )

        unread = list(
            NotificationService.unread_for_user(
                organization=self.organization,
                recipient=self.user,
            )
        )

        self.assertEqual(len(unread), 1)
        self.assertNotEqual(
            unread[0].organization_id,
            other_notification.organization_id,
        )


class NotificationSerializerTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Serializer Test Organization",
            slug="serializer-test-organization",
        )

        self.user = User.objects.create_user(
            username="serializer_user",
            email="serializer@example.com",
            password="testpass123",
        )

        OrganizationMember.objects.create(
            organization=self.organization,
            user=self.user,
            role="VIEWER",
        )

        self.workflow = Workflow.objects.create(
            organization=self.organization,
            name="Serializer Workflow",
            description="Workflow used for serializer tests.",
            created_by=self.user,
        )

        self.notification = Notification.objects.create(
            organization=self.organization,
            recipient=self.user,
            workflow=self.workflow,
            notification_type=Notification.NotificationType.BOTTLENECK,
            priority=Notification.Priority.HIGH,
            title="Bottleneck detected",
            message="Verification is taking longer than expected.",
            related_object_type="bottleneck",
            related_object_id=123,
        )

    def test_notification_serializes_expected_fields(self):
        serializer = NotificationSerializer(self.notification)
        data = serializer.data

        self.assertEqual(data["id"], self.notification.id)
        self.assertEqual(data["organization"], self.organization.id)
        self.assertEqual(
            data["organization_name"],
            self.organization.name,
        )
        self.assertEqual(data["recipient"], self.user.id)
        self.assertEqual(
            data["recipient_username"],
            self.user.username,
        )
        self.assertEqual(data["workflow"], self.workflow.id)
        self.assertEqual(
            data["workflow_name"],
            self.workflow.name,
        )
        self.assertEqual(
            data["notification_type"],
            Notification.NotificationType.BOTTLENECK,
        )
        self.assertEqual(
            data["priority"],
            Notification.Priority.HIGH,
        )
        self.assertEqual(data["title"], "Bottleneck detected")
        self.assertEqual(
            data["message"],
            "Verification is taking longer than expected.",
        )
        self.assertFalse(data["is_read"])
        self.assertEqual(
            data["related_object_type"],
            "bottleneck",
        )
        self.assertEqual(data["related_object_id"], 123)
        self.assertIn("created_at", data)
        self.assertIsNone(data["read_at"])

    def test_notification_serializer_is_read_only(self):
        serializer = NotificationSerializer(self.notification)

        for field_name in [
            "organization",
            "recipient",
            "workflow",
            "notification_type",
            "priority",
            "title",
            "message",
            "is_read",
            "related_object_type",
            "related_object_id",
            "created_at",
            "read_at",
        ]:
            self.assertTrue(
                serializer.fields[field_name].read_only,
                msg=f"{field_name} should be read-only.",
            )

    def test_notification_without_optional_relationships_serializes(self):
        notification = Notification.objects.create(
            organization=self.organization,
            notification_type=Notification.NotificationType.SYSTEM,
            title="System notification",
            message="System message.",
        )

        serializer = NotificationSerializer(notification)
        data = serializer.data

        self.assertEqual(
            data["organization"],
            self.organization.id,
        )
        self.assertEqual(
            data["organization_name"],
            self.organization.name,
        )
        self.assertIsNone(data["recipient"])
        self.assertIsNone(data["recipient_username"])
        self.assertIsNone(data["workflow"])
        self.assertIsNone(data["workflow_name"])


class NotificationAPITests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()

        self.organization = Organization.objects.create(
            name="API Test Organization",
            slug="api-test-organization",
        )

        self.other_organization = Organization.objects.create(
            name="Other API Organization",
            slug="other-api-organization",
        )

        self.user = User.objects.create_user(
            username="api_user",
            email="api@example.com",
            password="testpass123",
        )

        OrganizationMember.objects.create(
            organization=self.organization,
            user=self.user,
            role="VIEWER",
        )

        self.other_user = User.objects.create_user(
            username="other_api_user",
            email="other-api@example.com",
            password="testpass123",
        )

        OrganizationMember.objects.create(
            organization=self.other_organization,
            user=self.other_user,
            role="VIEWER",
        )

        self.notification = Notification.objects.create(
            organization=self.organization,
            recipient=self.user,
            notification_type=Notification.NotificationType.BOTTLENECK,
            priority=Notification.Priority.HIGH,
            title="Bottleneck detected",
            message="Verification is delayed.",
        )

        self.other_notification = Notification.objects.create(
            organization=self.other_organization,
            recipient=self.other_user,
            notification_type=Notification.NotificationType.SYSTEM,
            title="Other organization",
            message="Other organization notification.",
        )

    def test_notification_list_requires_authentication(self):
        request = self.factory.get("/notifications/")
        response = NotificationListView.as_view()(request)

        self.assertEqual(response.status_code, 403)

    def test_notification_list_returns_user_notifications(self):
        request = self.factory.get("/notifications/")
        force_authenticate(request, user=self.user)

        response = NotificationListView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["id"],
            self.notification.id,
        )

    def test_notification_list_can_filter_by_organization(self):
        request = self.factory.get(
            "/notifications/?organization={}".format(
                self.organization.id
            )
        )
        force_authenticate(request, user=self.user)

        response = NotificationListView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["organization"],
            self.organization.id,
        )

    def test_notification_list_can_filter_unread(self):
        NotificationService.mark_as_read(self.notification)

        unread_notification = NotificationService.create(
            organization=self.organization,
            recipient=self.user,
            notification_type=Notification.NotificationType.ANOMALY,
            title="Anomaly detected",
            message="An anomaly was detected.",
        )

        request = self.factory.get(
            "/notifications/?unread=true"
        )
        force_authenticate(request, user=self.user)

        response = NotificationListView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(
            response.data[0]["id"],
            unread_notification.id,
        )

    def test_notification_list_does_not_return_other_users_notifications(self):
        request = self.factory.get("/notifications/")
        force_authenticate(request, user=self.user)

        response = NotificationListView.as_view()(request)

        returned_ids = {
            item["id"]
            for item in response.data
        }

        self.assertIn(self.notification.id, returned_ids)
        self.assertNotIn(
            self.other_notification.id,
            returned_ids,
        )

    def test_notification_list_does_not_return_organization_notification_without_recipient(
        self,
    ):
        organization_notification = Notification.objects.create(
            organization=self.organization,
            recipient=None,
            notification_type=Notification.NotificationType.SYSTEM,
            title="Organization notification",
            message="This notification has no individual recipient.",
        )

        request = self.factory.get("/notifications/")
        force_authenticate(request, user=self.user)

        response = NotificationListView.as_view()(request)

        self.assertEqual(response.status_code, 200)

        returned_ids = {
            item["id"]
            for item in response.data
        }

        self.assertNotIn(
            organization_notification.id,
            returned_ids,
        )

    def test_unread_count(self):
        request = self.factory.get(
            "/notifications/unread-count/"
        )
        force_authenticate(request, user=self.user)

        response = NotificationUnreadCountView.as_view()(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)

    def test_mark_notification_as_read(self):
        request = self.factory.post(
            "/notifications/{}/read/".format(
                self.notification.id
            )
        )
        force_authenticate(request, user=self.user)

        response = NotificationMarkReadView.as_view()(
            request,
            pk=self.notification.id,
        )

        self.assertEqual(response.status_code, 200)

        self.notification.refresh_from_db()

        self.assertTrue(self.notification.is_read)
        self.assertIsNotNone(self.notification.read_at)

    def test_mark_notification_as_unread(self):
        self.notification.is_read = True
        self.notification.read_at = timezone.now()
        self.notification.save()

        request = self.factory.post(
            "/notifications/{}/unread/".format(
                self.notification.id
            )
        )
        force_authenticate(request, user=self.user)

        response = NotificationMarkUnreadView.as_view()(
            request,
            pk=self.notification.id,
        )

        self.assertEqual(response.status_code, 200)

        self.notification.refresh_from_db()

        self.assertFalse(self.notification.is_read)
        self.assertIsNone(self.notification.read_at)

    def test_user_cannot_mark_other_users_notification_as_read(self):
        request = self.factory.post(
            "/notifications/{}/read/".format(
                self.other_notification.id
            )
        )
        force_authenticate(request, user=self.user)

        response = NotificationMarkReadView.as_view()(
            request,
            pk=self.other_notification.id,
        )

        self.assertEqual(response.status_code, 404)

        self.other_notification.refresh_from_db()

        self.assertFalse(self.other_notification.is_read)

    def test_user_cannot_mark_other_users_notification_as_unread(self):
        self.other_notification.is_read = True
        self.other_notification.read_at = timezone.now()
        self.other_notification.save()

        request = self.factory.post(
            "/notifications/{}/unread/".format(
                self.other_notification.id
            )
        )
        force_authenticate(request, user=self.user)

        response = NotificationMarkUnreadView.as_view()(
            request,
            pk=self.other_notification.id,
        )

        self.assertEqual(response.status_code, 404)

        self.other_notification.refresh_from_db()

        self.assertTrue(self.other_notification.is_read)

    def test_notification_list_url_resolves(self):
        url = reverse("notifications:list")

        self.assertEqual(
            url,
            "/api/notifications/",
        )

    def test_notification_unread_count_url_resolves(self):
        url = reverse("notifications:unread-count")

        self.assertEqual(
            url,
            "/api/notifications/unread-count/",
        )

    def test_notification_mark_read_url_resolves(self):
        url = reverse(
            "notifications:mark-read",
            kwargs={"pk": self.notification.id},
        )

        self.assertEqual(
            url,
            f"/api/notifications/{self.notification.id}/read/",
        )

    def test_notification_mark_unread_url_resolves(self):
        url = reverse(
            "notifications:mark-unread",
            kwargs={"pk": self.notification.id},
        )

        self.assertEqual(
            url,
            f"/api/notifications/{self.notification.id}/unread/",
        )


class RecommendationNotificationServiceTests(TestCase):
    def setUp(self):
        self.organization = Organization.objects.create(
            name="Recommendation Notification Organization",
            slug="recommendation-notification-organization",
        )

        self.user = User.objects.create_user(
            username="recommendation_user",
            email="recommendation@example.com",
            password="testpass123",
        )

        OrganizationMember.objects.create(
            organization=self.organization,
            user=self.user,
            role="MANAGER",
        )

        self.workflow = Workflow.objects.create(
            organization=self.organization,
            name="Recommendation Workflow",
            description="Workflow for recommendation notification tests.",
            created_by=self.user,
        )

        self.recommendation = Recommendation.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            title="Automate low-risk verification",
            description="Consider automating low-risk verification tasks.",
            priority=Recommendation.Priority.HIGH,
            score=82,
        )

    def test_creates_notification_for_recommendation(self):
        notification = (
            RecommendationNotificationService.create_for_recommendation(
                recommendation=self.recommendation,
                recipient=self.user,
            )
        )

        self.assertEqual(
            notification.organization,
            self.organization,
        )
        self.assertEqual(
            notification.recipient,
            self.user,
        )
        self.assertEqual(
            notification.workflow,
            self.workflow,
        )
        self.assertEqual(
            notification.notification_type,
            Notification.NotificationType.RECOMMENDATION,
        )
        self.assertEqual(
            notification.priority,
            Notification.Priority.HIGH,
        )
        self.assertEqual(
            notification.title,
            self.recommendation.title,
        )
        self.assertEqual(
            notification.message,
            self.recommendation.description,
        )
        self.assertEqual(
            notification.related_object_type,
            "recommendation",
        )
        self.assertEqual(
            notification.related_object_id,
            self.recommendation.id,
        )

    def test_maps_critical_recommendation_to_critical_notification(self):
        self.recommendation.priority = Recommendation.Priority.CRITICAL
        self.recommendation.save(update_fields=["priority"])

        notification = (
            RecommendationNotificationService.create_for_recommendation(
                recommendation=self.recommendation,
                recipient=self.user,
            )
        )

        self.assertEqual(
            notification.priority,
            Notification.Priority.CRITICAL,
        )

    def test_maps_low_recommendation_to_low_notification(self):
        self.recommendation.priority = Recommendation.Priority.LOW
        self.recommendation.save(update_fields=["priority"])

        notification = (
            RecommendationNotificationService.create_for_recommendation(
                recommendation=self.recommendation,
                recipient=self.user,
            )
        )

        self.assertEqual(
            notification.priority,
            Notification.Priority.LOW,
        )

    def test_can_create_organization_notification_without_recipient(self):
        notification = (
            RecommendationNotificationService.create_for_recommendation(
                recommendation=self.recommendation,
            )
        )

        self.assertEqual(
            notification.organization,
            self.organization,
        )
        self.assertIsNone(notification.recipient)

    def test_rejects_invalid_recommendation(self):
        with self.assertRaisesMessage(
            ValueError,
            "A valid Recommendation instance is required.",
        ):
            RecommendationNotificationService.create_for_recommendation(
                recommendation="invalid",
                recipient=self.user,
            )