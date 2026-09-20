from apps.recommendations.models import Recommendation
from apps.recommendations.services.ai_explanation import (
    RecommendationAIExplanationError,
    RecommendationAIExplanationService,
)
from apps.recommendations.services.engine import (
    RecommendationEngine,
    RecommendationEngineError,
)
from apps.recommendations.services.scoring import (
    RecommendationScoringError,
    RecommendationScoringService,
)


class RecommendationPipelineError(Exception):
    """Raised when the recommendation pipeline fails."""


class RecommendationPipeline:
    """
    Orchestrates recommendation generation, scoring, and AI explanation.

    Flow:

        Input evidence
            ↓
        RecommendationEngine
            ↓
        RecommendationScoringService
            ↓
        RecommendationAIExplanationService
            ↓
        Final recommendations
    """

    def __init__(
        self,
        engine=None,
        scoring_service=None,
        ai_explanation_service=None,
    ):
        self.engine = engine or RecommendationEngine()

        self.scoring_service = (
            scoring_service
            or RecommendationScoringService()
        )

        self.ai_explanation_service = (
            ai_explanation_service
            or RecommendationAIExplanationService()
        )

    def run(
        self,
        organization,
        workflow=None,
        bottlenecks=None,
        anomalies=None,
        predictions=None,
        data_quality=None,
        generate_ai_explanations=True,
    ):
        if organization is None:
            raise RecommendationPipelineError(
                "Organization is required."
            )

        try:
            recommendations = self.engine.generate(
                organization=organization,
                workflow=workflow,
                bottlenecks=bottlenecks,
                anomalies=anomalies,
                predictions=predictions,
                data_quality=data_quality,
            )
        except RecommendationEngineError as exc:
            raise RecommendationPipelineError(
                str(exc)
            ) from exc

        scored_recommendations = []

        for recommendation in recommendations:
            scores = self._calculate_scores(
                recommendation
            )

            try:
                scored = self.scoring_service.score(
                    recommendation=recommendation,
                    severity_score=scores["severity_score"],
                    evidence_score=scores["evidence_score"],
                    impact_score=scores["impact_score"],
                )
            except RecommendationScoringError as exc:
                raise RecommendationPipelineError(
                    str(exc)
                ) from exc

            scored_recommendations.append(
                scored
            )

        explained_recommendations = []

        for recommendation in scored_recommendations:
            if generate_ai_explanations:
                try:
                    self.ai_explanation_service.explain(
                        recommendation=recommendation
                    )
                except RecommendationAIExplanationError as exc:
                    raise RecommendationPipelineError(
                        str(exc)
                    ) from exc

            explained_recommendations.append(
                recommendation
            )

        explained_recommendations.sort(
            key=lambda recommendation: (
                -recommendation.score,
                -recommendation.created_at.timestamp(),
            )
        )

        return {
            "organization": organization,
            "workflow": workflow,
            "recommendations": explained_recommendations,
            "recommendation_count": len(
                explained_recommendations
            ),
        }

    def _calculate_scores(self, recommendation):
        severity_score = self._severity_score(
            recommendation
        )

        evidence_score = self._evidence_score(
            recommendation
        )

        impact_score = self._impact_score(
            recommendation
        )

        return {
            "severity_score": severity_score,
            "evidence_score": evidence_score,
            "impact_score": impact_score,
        }

    def _severity_score(self, recommendation):
        priority_scores = {
            Recommendation.Priority.CRITICAL: 100.0,
            Recommendation.Priority.HIGH: 85.0,
            Recommendation.Priority.MEDIUM: 65.0,
            Recommendation.Priority.LOW: 35.0,
        }

        return priority_scores.get(
            recommendation.priority,
            50.0,
        )

    def _evidence_score(self, recommendation):
        evidence = recommendation.evidence or {}

        if not evidence:
            return 20.0

        numeric_values = []

        for value in evidence.values():
            try:
                numeric_values.append(
                    abs(float(value))
                )
            except (TypeError, ValueError):
                continue

        if numeric_values:
            return min(
                100.0,
                60.0 + len(numeric_values) * 10.0,
            )

        return 50.0

    def _impact_score(self, recommendation):
        recommendation_type = (
            recommendation.recommendation_type
        )

        impact_scores = {
            Recommendation.RecommendationType.BOTTLENECK: 90.0,
            Recommendation.RecommendationType.ANOMALY: 75.0,
            Recommendation.RecommendationType.PREDICTION: 80.0,
            Recommendation.RecommendationType.DATA_QUALITY: 65.0,
            Recommendation.RecommendationType.CAPACITY: 85.0,
            Recommendation.RecommendationType.AUTOMATION: 90.0,
            Recommendation.RecommendationType.PROCESS: 80.0,
            Recommendation.RecommendationType.OTHER: 50.0,
        }

        return impact_scores.get(
            recommendation_type,
            50.0,
        )