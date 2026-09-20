import pandas as pd

from django.test import TestCase

from apps.accounts.models import User
from apps.organizations.models import Organization, OrganizationMember
from apps.recommendations.models import Recommendation
from apps.recommendations.services.engine import (
    RecommendationEngine,
    RecommendationEngineError,
)
from apps.recommendations.services.scoring import (
    RecommendationScoringError,
    RecommendationScoringService,
)
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

        self.assertEqual(
            recommendation.score,
            0.0,
        )

        self.assertEqual(
            recommendation.severity_score,
            0.0,
        )

        self.assertEqual(
            recommendation.evidence_score,
            0.0,
        )

        self.assertEqual(
            recommendation.impact_score,
            0.0,
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


class RecommendationEngineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="engine_user",
            email="engine@example.com",
            password="test-password-123",
        )

        self.organization = Organization.objects.create(
            name="Engine Test Organization",
            slug="engine-test-organization",
        )

        OrganizationMember.objects.create(
            organization=self.organization,
            user=self.user,
            role=OrganizationMember.Role.ADMIN,
        )

        self.workflow = Workflow.objects.create(
            organization=self.organization,
            name="Engine Workflow",
            created_by=self.user,
        )

        self.engine = RecommendationEngine()

    def test_bottleneck_generates_recommendation(self):
        bottlenecks = [
            {
                "step_name": "Verification",
                "average_duration": 12.1,
                "expected_duration": 5.0,
                "delay_ratio": 2.42,
                "delay_percentage": 142.0,
            }
        ]

        recommendations = self.engine.generate(
            organization=self.organization,
            workflow=self.workflow,
            bottlenecks=bottlenecks,
        )

        self.assertEqual(len(recommendations), 1)

        recommendation = recommendations[0]

        self.assertEqual(
            recommendation.recommendation_type,
            Recommendation.RecommendationType.BOTTLENECK,
        )

        self.assertEqual(
            recommendation.priority,
            Recommendation.Priority.HIGH,
        )

        self.assertEqual(
            recommendation.evidence["step_name"],
            "Verification",
        )

    def test_bottleneck_priority_is_medium(self):
        bottlenecks = [
            {
                "step_name": "Packing",
                "average_duration": 8.0,
                "expected_duration": 5.0,
                "delay_ratio": 1.6,
                "delay_percentage": 60.0,
            }
        ]

        recommendations = self.engine.generate(
            organization=self.organization,
            workflow=self.workflow,
            bottlenecks=bottlenecks,
        )

        self.assertEqual(
            recommendations[0].priority,
            Recommendation.Priority.MEDIUM,
        )

    def test_bottleneck_priority_is_low(self):
        bottlenecks = [
            {
                "step_name": "Shipping",
                "average_duration": 6.0,
                "expected_duration": 5.0,
                "delay_ratio": 1.2,
                "delay_percentage": 20.0,
            }
        ]

        recommendations = self.engine.generate(
            organization=self.organization,
            workflow=self.workflow,
            bottlenecks=bottlenecks,
        )

        self.assertEqual(
            recommendations[0].priority,
            Recommendation.Priority.LOW,
        )

    def test_anomaly_generates_recommendation(self):
        anomalies = pd.DataFrame(
            [
                {
                    "step_name": "Verification",
                    "duration_minutes": 31.0,
                    "anomaly_prediction": -1,
                    "anomaly_score": -0.25,
                    "is_anomaly": True,
                    "anomaly_severity": "HIGH",
                }
            ]
        )

        recommendations = self.engine.generate(
            organization=self.organization,
            workflow=self.workflow,
            anomalies=anomalies,
        )

        self.assertEqual(len(recommendations), 1)

        recommendation = recommendations[0]

        self.assertEqual(
            recommendation.recommendation_type,
            Recommendation.RecommendationType.ANOMALY,
        )

        self.assertEqual(
            recommendation.priority,
            Recommendation.Priority.HIGH,
        )

    def test_normal_anomaly_does_not_generate_recommendation(self):
        anomalies = [
            {
                "step_name": "Packing",
                "duration_minutes": 8.0,
                "anomaly_prediction": 1,
                "anomaly_score": 0.1,
                "is_anomaly": False,
                "anomaly_severity": "NORMAL",
            }
        ]

        recommendations = self.engine.generate(
            organization=self.organization,
            workflow=self.workflow,
            anomalies=anomalies,
        )

        self.assertEqual(recommendations, [])

    def test_prediction_generates_recommendation(self):
        predictions = [
            {
                "step_name": "Verification",
                "predicted_duration_minutes": 12.5,
            }
        ]

        recommendations = self.engine.generate(
            organization=self.organization,
            workflow=self.workflow,
            predictions=predictions,
        )

        self.assertEqual(len(recommendations), 1)

        recommendation = recommendations[0]

        self.assertEqual(
            recommendation.recommendation_type,
            Recommendation.RecommendationType.PREDICTION,
        )

        self.assertEqual(
            recommendation.priority,
            Recommendation.Priority.HIGH,
        )

    def test_low_prediction_uses_medium_priority(self):
        predictions = [
            {
                "step_name": "Packing",
                "predicted_duration_minutes": 8.0,
            }
        ]

        recommendations = self.engine.generate(
            organization=self.organization,
            workflow=self.workflow,
            predictions=predictions,
        )

        self.assertEqual(
            recommendations[0].priority,
            Recommendation.Priority.MEDIUM,
        )

    def test_data_quality_generates_recommendation(self):
        data_quality = {
            "quality_score": 72.5,
            "missing_percentage": 10.0,
            "duplicate_percentage": 5.0,
        }

        recommendations = self.engine.generate(
            organization=self.organization,
            workflow=self.workflow,
            data_quality=data_quality,
        )

        self.assertEqual(len(recommendations), 1)

        recommendation = recommendations[0]

        self.assertEqual(
            recommendation.recommendation_type,
            Recommendation.RecommendationType.DATA_QUALITY,
        )

        self.assertEqual(
            recommendation.priority,
            Recommendation.Priority.MEDIUM,
        )

    def test_critical_data_quality_uses_high_priority(self):
        data_quality = {
            "quality_score": 45.0,
            "missing_percentage": 40.0,
            "duplicate_percentage": 15.0,
        }

        recommendations = self.engine.generate(
            organization=self.organization,
            workflow=self.workflow,
            data_quality=data_quality,
        )

        self.assertEqual(
            recommendations[0].priority,
            Recommendation.Priority.HIGH,
        )

    def test_good_data_quality_does_not_generate_recommendation(self):
        data_quality = {
            "quality_score": 95.0,
            "missing_percentage": 2.0,
            "duplicate_percentage": 1.0,
        }

        recommendations = self.engine.generate(
            organization=self.organization,
            workflow=self.workflow,
            data_quality=data_quality,
        )

        self.assertEqual(recommendations, [])

    def test_multiple_sources_generate_multiple_recommendations(self):
        bottlenecks = [
            {
                "step_name": "Verification",
                "average_duration": 12.1,
                "expected_duration": 5.0,
                "delay_ratio": 2.42,
                "delay_percentage": 142.0,
            }
        ]

        anomalies = [
            {
                "step_name": "Packing",
                "duration_minutes": 31.0,
                "anomaly_prediction": -1,
                "anomaly_score": -0.25,
                "is_anomaly": True,
                "anomaly_severity": "HIGH",
            }
        ]

        predictions = [
            {
                "step_name": "Shipping",
                "predicted_duration_minutes": 11.0,
            }
        ]

        data_quality = {
            "quality_score": 70.0,
            "missing_percentage": 10.0,
            "duplicate_percentage": 5.0,
        }

        recommendations = self.engine.generate(
            organization=self.organization,
            workflow=self.workflow,
            bottlenecks=bottlenecks,
            anomalies=anomalies,
            predictions=predictions,
            data_quality=data_quality,
        )

        self.assertEqual(len(recommendations), 4)

    def test_organization_is_required(self):
        with self.assertRaises(RecommendationEngineError):
            self.engine.generate(
                organization=None,
            )

    def test_empty_inputs_generate_no_recommendations(self):
        recommendations = self.engine.generate(
            organization=self.organization,
            workflow=self.workflow,
        )

        self.assertEqual(recommendations, [])

    def test_recommendations_are_saved_to_database(self):
        bottlenecks = [
            {
                "step_name": "Verification",
                "average_duration": 12.1,
                "expected_duration": 5.0,
                "delay_ratio": 2.42,
                "delay_percentage": 142.0,
            }
        ]

        self.engine.generate(
            organization=self.organization,
            workflow=self.workflow,
            bottlenecks=bottlenecks,
        )

        self.assertEqual(
            Recommendation.objects.filter(
                organization=self.organization
            ).count(),
            1,
        )


class RecommendationScoringServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="scoring_user",
            email="scoring@example.com",
            password="test-password-123",
        )

        self.organization = Organization.objects.create(
            name="Scoring Test Organization",
            slug="scoring-test-organization",
        )

        OrganizationMember.objects.create(
            organization=self.organization,
            user=self.user,
            role=OrganizationMember.Role.ADMIN,
        )

        self.workflow = Workflow.objects.create(
            organization=self.organization,
            name="Scoring Workflow",
            created_by=self.user,
        )

        self.recommendation = Recommendation.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            title="Test recommendation",
            description="Recommendation used for scoring tests.",
        )

        self.service = RecommendationScoringService()

    def test_score_calculation(self):
        result = self.service.score(
            recommendation=self.recommendation,
            severity_score=80,
            evidence_score=90,
            impact_score=70,
        )

        expected_score = (
            80 * 0.40
            + 90 * 0.30
            + 70 * 0.30
        )

        self.assertEqual(
            result.score,
            round(expected_score, 2),
        )

        self.assertEqual(
            result.severity_score,
            80,
        )

        self.assertEqual(
            result.evidence_score,
            90,
        )

        self.assertEqual(
            result.impact_score,
            70,
        )

    def test_critical_priority(self):
        result = self.service.score(
            recommendation=self.recommendation,
            severity_score=100,
            evidence_score=100,
            impact_score=100,
        )

        self.assertEqual(
            result.score,
            100,
        )

        self.assertEqual(
            result.priority,
            Recommendation.Priority.CRITICAL,
        )

    def test_high_priority(self):
        result = self.service.score(
            recommendation=self.recommendation,
            severity_score=80,
            evidence_score=70,
            impact_score=70,
        )

        self.assertEqual(
            result.score,
            74,
        )

        self.assertEqual(
            result.priority,
            Recommendation.Priority.HIGH,
        )

    def test_medium_priority(self):
        result = self.service.score(
            recommendation=self.recommendation,
            severity_score=60,
            evidence_score=50,
            impact_score=50,
        )

        self.assertEqual(
            result.score,
            54,
        )

        self.assertEqual(
            result.priority,
            Recommendation.Priority.MEDIUM,
        )

    def test_low_priority(self):
        result = self.service.score(
            recommendation=self.recommendation,
            severity_score=30,
            evidence_score=40,
            impact_score=20,
        )

        self.assertEqual(
            result.score,
            30,
        )

        self.assertEqual(
            result.priority,
            Recommendation.Priority.LOW,
        )

    def test_negative_score_is_rejected(self):
        with self.assertRaises(RecommendationScoringError):
            self.service.score(
                recommendation=self.recommendation,
                severity_score=-1,
                evidence_score=50,
                impact_score=50,
            )

    def test_score_above_100_is_rejected(self):
        with self.assertRaises(RecommendationScoringError):
            self.service.score(
                recommendation=self.recommendation,
                severity_score=101,
                evidence_score=50,
                impact_score=50,
            )

    def test_non_numeric_score_is_rejected(self):
        with self.assertRaises(RecommendationScoringError):
            self.service.score(
                recommendation=self.recommendation,
                severity_score="invalid",
                evidence_score=50,
                impact_score=50,
            )

    def test_invalid_recommendation_is_rejected(self):
        with self.assertRaises(RecommendationScoringError):
            self.service.score(
                recommendation=None,
                severity_score=50,
                evidence_score=50,
                impact_score=50,
            )

    def test_score_is_persisted(self):
        self.service.score(
        recommendation=self.recommendation,
        severity_score=90,
        evidence_score=80,
        impact_score=70,
    )

        refreshed = Recommendation.objects.get(
            pk=self.recommendation.pk
        )

        self.assertEqual(
            refreshed.score,
            81,
        )

        self.assertEqual(
            refreshed.severity_score,
            90,
        )

        self.assertEqual(
            refreshed.evidence_score,
            80,
        )

        self.assertEqual(
            refreshed.impact_score,
            70,
        )

    def test_score_many(self):
        second = Recommendation.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            title="Second recommendation",
            description="Second recommendation.",
            severity_score=90,
            evidence_score=80,
            impact_score=70,
        )

        results = self.service.score_many(
            [
                self.recommendation,
                second,
            ]
        )

        self.assertEqual(
            len(results),
            2,
        )

    def test_score_many_requires_input(self):
        with self.assertRaises(RecommendationScoringError):
            self.service.score_many(None)