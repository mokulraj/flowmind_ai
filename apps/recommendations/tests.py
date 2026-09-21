import pandas as pd

from django.test import TestCase

from apps.accounts.models import User
from apps.audit.models import AuditLog
from apps.notifications.models import Notification
from apps.organizations.models import Organization, OrganizationMember
from apps.recommendations.models import Recommendation
from apps.recommendations.services.ai_explanation import (
    RecommendationAIExplanationError,
    RecommendationAIExplanationService,
)
from apps.recommendations.services.engine import (
    RecommendationEngine,
    RecommendationEngineError,
)
from apps.recommendations.services.pipeline import (
    RecommendationPipeline,
    RecommendationPipelineError,
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


class MockRecommendationAnalysisService:
    def __init__(self, response):
        self.response = response
        self.calls = []

    def analyze(self, **kwargs):
        self.calls.append(kwargs)

        return {
            "response": self.response,
            "context": {},
            "retrieved_knowledge": [],
            "prompt": "mock prompt",
            "prompt_type": "workflow_analysis",
        }


class RecommendationAIExplanationServiceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="ai_explanation_user",
            email="ai_explanation@example.com",
            password="test-password-123",
        )

        self.organization = Organization.objects.create(
            name="AI Explanation Organization",
            slug="ai-explanation-organization",
        )

        OrganizationMember.objects.create(
            organization=self.organization,
            user=self.user,
            role=OrganizationMember.Role.ADMIN,
        )

        self.workflow = Workflow.objects.create(
            organization=self.organization,
            name="AI Explanation Workflow",
            created_by=self.user,
        )

        self.recommendation = Recommendation.objects.create(
            organization=self.organization,
            workflow=self.workflow,
            title="Reduce verification delay",
            description=(
                "Verification is taking longer than expected."
            ),
            recommendation_type=(
                Recommendation.RecommendationType.BOTTLENECK
            ),
            priority=Recommendation.Priority.HIGH,
            score=82.0,
            severity_score=90.0,
            evidence_score=80.0,
            impact_score=70.0,
            evidence={
                "step_name": "Verification",
                "average_duration": 12.1,
                "expected_duration": 5.0,
                "delay_ratio": 2.42,
            },
            expected_impact=(
                "Reducing verification delay may improve "
                "overall workflow throughput."
            ),
        )

    def test_build_context_contains_recommendation_data(self):
        service = RecommendationAIExplanationService()

        context = service._build_context(
            self.recommendation
        )

        self.assertEqual(
            context["recommendation"]["title"],
            "Reduce verification delay",
        )

        self.assertEqual(
            context["recommendation"]["score"],
            82.0,
        )

        self.assertEqual(
            context["recommendation"]["evidence"][
                "step_name"
            ],
            "Verification",
        )

        self.assertEqual(
            context["workflow"]["name"],
            "AI Explanation Workflow",
        )

    def test_build_prompt_contains_evidence(self):
        service = RecommendationAIExplanationService()

        context = service._build_context(
            self.recommendation
        )

        prompt = service._build_prompt(
            context
        )

        self.assertIn(
            "Reduce verification delay",
            prompt,
        )

        self.assertIn(
            "Verification",
            prompt,
        )

        self.assertIn(
            "12.1",
            prompt,
        )

        self.assertIn(
            "5.0",
            prompt,
        )

        self.assertIn(
            "2.42",
            prompt,
        )

    def test_explain_saves_ai_explanation(self):
        mock_analysis = MockRecommendationAnalysisService(
            response=(
                "Verification is significantly slower than "
                "the expected duration based on the supplied "
                "evidence."
            )
        )

        service = RecommendationAIExplanationService(
            analysis_service=mock_analysis
        )

        result = service.explain(
            recommendation=self.recommendation
        )

        self.assertEqual(
            result["response"],
            (
                "Verification is significantly slower than "
                "the expected duration based on the supplied "
                "evidence."
            ),
        )

        refreshed = Recommendation.objects.get(
            pk=self.recommendation.pk
        )

        self.assertEqual(
            refreshed.ai_explanation,
            result["response"],
        )

    def test_explain_passes_organization_to_ai_service(self):
        mock_analysis = MockRecommendationAnalysisService(
            response="Explanation"
        )

        service = RecommendationAIExplanationService(
            analysis_service=mock_analysis
        )

        service.explain(
            recommendation=self.recommendation
        )

        self.assertEqual(
            len(mock_analysis.calls),
            1,
        )

        self.assertEqual(
            mock_analysis.calls[0]["organization"],
            self.organization,
        )

        self.assertEqual(
            mock_analysis.calls[0]["workflow"],
            self.workflow,
        )

    def test_custom_system_prompt_is_forwarded(self):
        mock_analysis = MockRecommendationAnalysisService(
            response="Explanation"
        )

        service = RecommendationAIExplanationService(
            analysis_service=mock_analysis
        )

        custom_prompt = (
            "Explain recommendations in a concise business style."
        )

        service.explain(
            recommendation=self.recommendation,
            system_prompt=custom_prompt,
        )

        self.assertEqual(
            mock_analysis.calls[0]["system_prompt"],
            custom_prompt,
        )

    def test_invalid_recommendation_is_rejected(self):
        service = RecommendationAIExplanationService()

        with self.assertRaises(
            RecommendationAIExplanationError
        ):
            service.explain(
                recommendation=None
            )

    def test_empty_ai_response_is_rejected(self):
        mock_analysis = MockRecommendationAnalysisService(
            response="   "
        )

        service = RecommendationAIExplanationService(
            analysis_service=mock_analysis
        )

        with self.assertRaises(
            RecommendationAIExplanationError
        ):
            service.explain(
                recommendation=self.recommendation
            )


class MockPipelineAIExplanationService:
    def __init__(self):
        self.calls = []

    def explain(self, recommendation):
        self.calls.append(recommendation)

        recommendation.ai_explanation = (
            f"AI explanation for: {recommendation.title}"
        )

        recommendation.save(
            update_fields=[
                "ai_explanation",
                "updated_at",
            ]
        )

        return {
            "recommendation": recommendation,
            "response": recommendation.ai_explanation,
        }


class MockRecommendationNotificationService:
    def __init__(self):
        self.calls = []

    def create_for_recommendation(
        self,
        *,
        recommendation,
        recipient=None,
    ):
        self.calls.append(
            {
                "recommendation": recommendation,
                "recipient": recipient,
            }
        )

        return Notification(
            organization=recommendation.organization,
            recipient=recipient,
            workflow=recommendation.workflow,
            notification_type=Notification.NotificationType.RECOMMENDATION,
            priority=recommendation.priority,
            title=recommendation.title,
            message=recommendation.description,
            related_object_type="recommendation",
            related_object_id=recommendation.id,
        )


class RecommendationPipelineTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="pipeline_user",
            email="pipeline@example.com",
            password="test-password-123",
        )

        self.organization = Organization.objects.create(
            name="Pipeline Test Organization",
            slug="pipeline-test-organization",
        )

        OrganizationMember.objects.create(
            organization=self.organization,
            user=self.user,
            role=OrganizationMember.Role.ADMIN,
        )

        self.workflow = Workflow.objects.create(
            organization=self.organization,
            name="Pipeline Workflow",
            created_by=self.user,
        )

        self.mock_ai_service = (
            MockPipelineAIExplanationService()
        )

        self.mock_notification_service = (
            MockRecommendationNotificationService()
        )

        self.pipeline = RecommendationPipeline(
            ai_explanation_service=self.mock_ai_service,
            notification_service=self.mock_notification_service,
        )

    def test_pipeline_generates_recommendation(self):
        bottlenecks = [
            {
                "step_name": "Verification",
                "average_duration": 12.1,
                "expected_duration": 5.0,
                "delay_ratio": 2.42,
                "delay_percentage": 142.0,
            }
        ]

        result = self.pipeline.run(
            organization=self.organization,
            workflow=self.workflow,
            bottlenecks=bottlenecks,
        )

        self.assertEqual(
            result["recommendation_count"],
            1,
        )

        self.assertEqual(
            len(result["recommendations"]),
            1,
        )

    def test_pipeline_scores_recommendation(self):
        bottlenecks = [
            {
                "step_name": "Verification",
                "average_duration": 12.1,
                "expected_duration": 5.0,
                "delay_ratio": 2.42,
                "delay_percentage": 142.0,
            }
        ]

        result = self.pipeline.run(
            organization=self.organization,
            workflow=self.workflow,
            bottlenecks=bottlenecks,
        )

        recommendation = result["recommendations"][0]

        self.assertGreater(
            recommendation.score,
            0,
        )

        self.assertGreater(
            recommendation.severity_score,
            0,
        )

        self.assertGreater(
            recommendation.evidence_score,
            0,
        )

        self.assertGreater(
            recommendation.impact_score,
            0,
        )

    def test_pipeline_generates_ai_explanation(self):
        bottlenecks = [
            {
                "step_name": "Verification",
                "average_duration": 12.1,
                "expected_duration": 5.0,
                "delay_ratio": 2.42,
                "delay_percentage": 142.0,
            }
        ]

        result = self.pipeline.run(
            organization=self.organization,
            workflow=self.workflow,
            bottlenecks=bottlenecks,
            generate_ai_explanations=True,
        )

        recommendation = result["recommendations"][0]

        self.assertEqual(
            recommendation.ai_explanation,
            "AI explanation for: "
            "Reduce Verification processing delay",
        )

        self.assertEqual(
            len(self.mock_ai_service.calls),
            1,
        )

    def test_pipeline_can_skip_ai_explanations(self):
        bottlenecks = [
            {
                "step_name": "Verification",
                "average_duration": 12.1,
                "expected_duration": 5.0,
                "delay_ratio": 2.42,
                "delay_percentage": 142.0,
            }
        ]

        result = self.pipeline.run(
            organization=self.organization,
            workflow=self.workflow,
            bottlenecks=bottlenecks,
            generate_ai_explanations=False,
        )

        self.assertEqual(
            result["recommendation_count"],
            1,
        )

        self.assertEqual(
            len(self.mock_ai_service.calls),
            0,
        )

        recommendation = result["recommendations"][0]

        self.assertEqual(
            recommendation.ai_explanation,
            "",
        )

    def test_pipeline_handles_multiple_sources(self):
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

        result = self.pipeline.run(
            organization=self.organization,
            workflow=self.workflow,
            bottlenecks=bottlenecks,
            anomalies=anomalies,
            predictions=predictions,
        )

        self.assertEqual(
            result["recommendation_count"],
            3,
        )

        self.assertEqual(
            len(self.mock_ai_service.calls),
            3,
        )

    def test_pipeline_requires_organization(self):
        with self.assertRaises(
            RecommendationPipelineError
        ):
            self.pipeline.run(
                organization=None
            )

    def test_pipeline_returns_recommendations_sorted_by_score(self):
        bottlenecks = [
            {
                "step_name": "Packing",
                "average_duration": 8.0,
                "expected_duration": 5.0,
                "delay_ratio": 1.6,
                "delay_percentage": 60.0,
            },
            {
                "step_name": "Verification",
                "average_duration": 15.0,
                "expected_duration": 5.0,
                "delay_ratio": 3.0,
                "delay_percentage": 200.0,
            },
        ]

        result = self.pipeline.run(
            organization=self.organization,
            workflow=self.workflow,
        )

        self.assertEqual(
            result["recommendation_count"],
            0,
        )

        result = self.pipeline.run(
            organization=self.organization,
            workflow=self.workflow,
            bottlenecks=bottlenecks,
        )

        recommendations = result["recommendations"]

        self.assertEqual(
            len(recommendations),
            2,
        )

        self.assertGreaterEqual(
            recommendations[0].score,
            recommendations[1].score,
        )

    def test_pipeline_creates_recommendation_notification(self):
        bottlenecks = [
            {
                "step_name": "Verification",
                "average_duration": 12.1,
                "expected_duration": 5.0,
                "delay_ratio": 2.42,
                "delay_percentage": 142.0,
            }
        ]

        result = self.pipeline.run(
            organization=self.organization,
            workflow=self.workflow,
            bottlenecks=bottlenecks,
        )

        self.assertEqual(
            result["recommendation_count"],
            1,
        )

        self.assertEqual(
            len(self.mock_notification_service.calls),
            1,
        )

        call = self.mock_notification_service.calls[0]

        self.assertEqual(
            call["recommendation"],
            result["recommendations"][0],
        )

        self.assertIsNone(
            call["recipient"],
        )

    def test_pipeline_can_skip_notification_creation(self):
        bottlenecks = [
            {
                "step_name": "Verification",
                "average_duration": 12.1,
                "expected_duration": 5.0,
                "delay_ratio": 2.42,
                "delay_percentage": 142.0,
            }
        ]

        result = self.pipeline.run(
            organization=self.organization,
            workflow=self.workflow,
            bottlenecks=bottlenecks,
            create_notifications=False,
        )

        self.assertEqual(
            result["recommendation_count"],
            1,
        )

        self.assertEqual(
            len(self.mock_notification_service.calls),
            0,
        )

    def test_pipeline_creates_one_notification_per_recommendation(self):
        bottlenecks = [
            {
                "step_name": "Verification",
                "average_duration": 12.1,
                "expected_duration": 5.0,
                "delay_ratio": 2.42,
                "delay_percentage": 142.0,
            },
            {
                "step_name": "Packing",
                "average_duration": 8.0,
                "expected_duration": 5.0,
                "delay_ratio": 1.6,
                "delay_percentage": 60.0,
            },
        ]

        result = self.pipeline.run(
            organization=self.organization,
            workflow=self.workflow,
            bottlenecks=bottlenecks,
        )

        self.assertEqual(
            result["recommendation_count"],
            2,
        )

        self.assertEqual(
            len(self.mock_notification_service.calls),
            2,
        )

        notification_recommendation_ids = {
            call["recommendation"].id
            for call in self.mock_notification_service.calls
        }

        recommendation_ids = {
            recommendation.id
            for recommendation in result["recommendations"]
        }

        self.assertEqual(
            notification_recommendation_ids,
            recommendation_ids,
        )

    def test_pipeline_creates_audit_log(self):
        bottlenecks = [
            {
                "step_name": "Verification",
                "average_duration": 12.1,
                "expected_duration": 5.0,
                "delay_ratio": 2.42,
                "delay_percentage": 142.0,
            }
        ]

        result = self.pipeline.run(
            organization=self.organization,
            workflow=self.workflow,
            bottlenecks=bottlenecks,
            generate_ai_explanations=False,
            create_notifications=False,
        )

        self.assertEqual(
            result["recommendation_count"],
            1,
        )

        audit_log = AuditLog.objects.get(
            organization=self.organization,
            action=AuditLog.Action.GENERATE,
            object_type="RecommendationPipeline",
        )

        self.assertEqual(
            audit_log.object_id,
            self.workflow.id,
        )

        self.assertEqual(
            audit_log.user,
            None,
        )

        self.assertEqual(
            audit_log.metadata["organization_id"],
            self.organization.id,
        )

        self.assertEqual(
            audit_log.metadata["workflow_id"],
            self.workflow.id,
        )

        self.assertEqual(
            audit_log.metadata["recommendation_count"],
            1,
        )

        self.assertEqual(
            audit_log.metadata["recommendation_types"][
                Recommendation.RecommendationType.BOTTLENECK
            ],
            1,
        )

        self.assertFalse(
            audit_log.metadata["generate_ai_explanations"]
        )

        self.assertFalse(
            audit_log.metadata["create_notifications"]
        )