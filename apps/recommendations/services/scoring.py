from apps.recommendations.models import Recommendation


class RecommendationScoringError(Exception):
    """Raised when recommendation scoring fails."""


class RecommendationScoringService:
    """
    Calculates an explainable 0-100 recommendation score.

    Formula:

        severity * 0.40
        + evidence * 0.30
        + impact * 0.30
    """

    SEVERITY_WEIGHT = 0.40
    EVIDENCE_WEIGHT = 0.30
    IMPACT_WEIGHT = 0.30

    def score(
        self,
        recommendation,
        severity_score,
        evidence_score,
        impact_score,
    ):
        if not isinstance(
            recommendation,
            Recommendation,
        ):
            raise RecommendationScoringError(
                "A valid Recommendation instance is required."
            )

        severity = self._validate_score(
            severity_score,
            "severity_score",
        )

        evidence = self._validate_score(
            evidence_score,
            "evidence_score",
        )

        impact = self._validate_score(
            impact_score,
            "impact_score",
        )

        total = (
            severity * self.SEVERITY_WEIGHT
            + evidence * self.EVIDENCE_WEIGHT
            + impact * self.IMPACT_WEIGHT
        )

        total = round(total, 2)

        recommendation.severity_score = severity
        recommendation.evidence_score = evidence
        recommendation.impact_score = impact
        recommendation.score = total

        recommendation.priority = self._priority_from_score(
            total
        )

        recommendation.save(
            update_fields=[
                "severity_score",
                "evidence_score",
                "impact_score",
                "score",
                "priority",
                "updated_at",
            ]
        )

        return recommendation

    def score_many(
        self,
        recommendations,
    ):
        if recommendations is None:
            raise RecommendationScoringError(
                "Recommendations are required."
            )

        recommendations = list(recommendations)

        return [
            self.score(
                recommendation=recommendation,
                severity_score=recommendation.severity_score,
                evidence_score=recommendation.evidence_score,
                impact_score=recommendation.impact_score,
            )
            for recommendation in recommendations
        ]

    def _validate_score(self, value, field_name):
        try:
            numeric_value = float(value)
        except (TypeError, ValueError):
            raise RecommendationScoringError(
                f"{field_name} must be a number."
            )

        if numeric_value < 0 or numeric_value > 100:
            raise RecommendationScoringError(
                f"{field_name} must be between 0 and 100."
            )

        return numeric_value

    def _priority_from_score(self, score):
        if score >= 85:
            return Recommendation.Priority.CRITICAL

        if score >= 70:
            return Recommendation.Priority.HIGH

        if score >= 50:
            return Recommendation.Priority.MEDIUM

        return Recommendation.Priority.LOW