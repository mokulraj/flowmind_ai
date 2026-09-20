from apps.ai_engine.services.analysis import (
    AIAnalysisError,
    AIAnalysisService,
)
from apps.recommendations.models import Recommendation


class RecommendationAIExplanationError(Exception):
    """Raised when an AI recommendation explanation cannot be generated."""


class RecommendationAIExplanationService:
    """
    Generates an AI explanation for an existing recommendation.

    The recommendation itself is created by the deterministic
    recommendation engine. The AI is only responsible for explaining
    the recommendation using its existing evidence.
    """

    DEFAULT_SYSTEM_PROMPT = (
        "You are a FlowMind AI recommendation explanation assistant. "
        "Explain the supplied recommendation using only the provided "
        "recommendation details and evidence. Do not invent facts, "
        "measurements, causes, or outcomes. Clearly distinguish "
        "observed evidence from potential impact."
    )

    def __init__(self, analysis_service=None):
        self.analysis_service = (
            analysis_service or AIAnalysisService()
        )

    def explain(
        self,
        recommendation,
        system_prompt=None,
        temperature=0.2,
        max_tokens=800,
    ):
        if not isinstance(
            recommendation,
            Recommendation,
        ):
            raise RecommendationAIExplanationError(
                "A valid Recommendation instance is required."
            )

        context = self._build_context(
            recommendation
        )

        prompt = self._build_prompt(
            context
        )

        try:
            result = self.analysis_service.analyze(
                query=None,
                organization=recommendation.organization,
                workflow=recommendation.workflow,
                system_prompt=(
                    system_prompt
                    or self.DEFAULT_SYSTEM_PROMPT
                ),
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except AIAnalysisError as exc:
            raise RecommendationAIExplanationError(
                str(exc)
            ) from exc

        response = result.get("response")

        if response is None or not str(response).strip():
            raise RecommendationAIExplanationError(
                "AI returned an empty explanation."
            )

        recommendation.ai_explanation = str(
            response
        ).strip()

        recommendation.save(
            update_fields=[
                "ai_explanation",
                "updated_at",
            ]
        )

        return {
            "recommendation": recommendation,
            "prompt": prompt,
            "response": recommendation.ai_explanation,
            "context": context,
        }

    def _build_context(self, recommendation):
        return {
            "recommendation": {
                "title": recommendation.title,
                "description": recommendation.description,
                "type": recommendation.recommendation_type,
                "priority": recommendation.priority,
                "status": recommendation.status,
                "score": recommendation.score,
                "severity_score": recommendation.severity_score,
                "evidence_score": recommendation.evidence_score,
                "impact_score": recommendation.impact_score,
                "evidence": recommendation.evidence,
                "expected_impact": recommendation.expected_impact,
            },
            "workflow": (
                {
                    "id": recommendation.workflow.id,
                    "name": recommendation.workflow.name,
                    "category": recommendation.workflow.category,
                    "status": recommendation.workflow.status,
                }
                if recommendation.workflow
                else None
            ),
        }

    def _build_prompt(self, context):
        recommendation = context["recommendation"]

        evidence = recommendation["evidence"]
        expected_impact = recommendation["expected_impact"]

        return (
            "Explain the following FlowMind AI recommendation.\n\n"
            f"Title: {recommendation['title']}\n"
            f"Description: {recommendation['description']}\n"
            f"Type: {recommendation['type']}\n"
            f"Priority: {recommendation['priority']}\n"
            f"Score: {recommendation['score']}\n"
            f"Severity score: "
            f"{recommendation['severity_score']}\n"
            f"Evidence score: "
            f"{recommendation['evidence_score']}\n"
            f"Impact score: "
            f"{recommendation['impact_score']}\n"
            f"Evidence: {evidence}\n"
            f"Expected impact: {expected_impact}\n\n"
            "Provide a concise explanation of why this "
            "recommendation exists and what the supplied evidence "
            "shows. Do not introduce unsupported facts."
        )