from django.test import TestCase

from apps.accounts.models import User
from apps.organizations.models import Organization, OrganizationMember
from apps.recommendations.models import Recommendation
from apps.workflows.models import Workflow


class RecommendationModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="recommendation_user",
            email="recommendation@example.com",
            password="test-password-123",
        )

        self.organization = Organization.objects.create(
            name="Recommendation Test Organization",
            slug="recommendation-test-organization",
        )

        OrganizationMember.objects.create(
            organization=self.organization,
            user=self.user,
            role=OrganizationMember.Role.ADMIN,
        )

        self.workflow = Workflow.objects.create(
            organization=self.organization,
            name="Recommendation Workflow",
            created_by=self.user,
        )

    def test_create_recommendation(self):
        recommendation = Recommendation.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            title="Reduce verification delay",
            description="Verification is taking longer than expected.",
            recommendation_type=Recommendation.RecommendationType.BOTTLENECK,
            priority=Recommendation.Priority.HIGH,
            evidence={
                "step_name": "Verification",
                "average_duration": 12.1,
                "expected_duration": 5.0,
            },
            expected_impact="Reduce average verification duration.",
        )

        self.assertEqual(
            recommendation.organization,
            self.organization,
        )

        self.assertEqual(
            recommendation.workflow,
            self.workflow,
        )

        self.assertEqual(
            recommendation.priority,
            Recommendation.Priority.HIGH,
        )

        self.assertEqual(
            recommendation.status,
            Recommendation.Status.NEW,
        )

    def test_recommendation_defaults(self):
        recommendation = Recommendation.objects.create(
            organization=self.organization,
            title="Review workflow",
            description="Review the workflow for improvement opportunities.",
        )

        self.assertEqual(
            recommendation.recommendation_type,
            Recommendation.RecommendationType.OTHER,
        )

        self.assertEqual(
            recommendation.priority,
            Recommendation.Priority.MEDIUM,
        )

        self.assertEqual(
            recommendation.status,
            Recommendation.Status.NEW,
        )

        self.assertEqual(
            recommendation.evidence,
            {},
        )

    def test_recommendation_can_exist_without_workflow(self):
        recommendation = Recommendation.objects.create(
            organization=self.organization,
            title="Improve data quality",
            description="Review missing values in the uploaded dataset.",
            recommendation_type=Recommendation.RecommendationType.DATA_QUALITY,
        )

        self.assertIsNone(recommendation.workflow)

    def test_recommendation_string_representation(self):
        recommendation = Recommendation.objects.create(
            organization=self.organization,
            title="Automate verification",
            description="Consider automating low-risk verification.",
        )

        self.assertEqual(
            str(recommendation),
            "Automate verification",
        )

    def test_recommendation_organization_is_required(self):
        recommendation = Recommendation(
            title="Invalid recommendation",
            description="This recommendation has no organization.",
        )

        with self.assertRaises(Exception):
            recommendation.full_clean()