from apps.recommendations.models import Recommendation


class RecommendationEngineError(Exception):
    """Raised when recommendation generation fails."""


class RecommendationEngine:
    """
    Generates deterministic recommendations from workflow analytics.

    This service does not use an LLM. AI-generated explanations are added
    later in the recommendation AI integration layer.
    """

    BOTTLENECK_DELAY_RATIO_HIGH = 2.0
    BOTTLENECK_DELAY_RATIO_MEDIUM = 1.5

    def generate(
        self,
        organization,
        workflow=None,
        bottlenecks=None,
        anomalies=None,
        predictions=None,
        data_quality=None,
    ):
        if organization is None:
            raise RecommendationEngineError(
                "Organization is required."
            )

        recommendations = []

        recommendations.extend(
            self._generate_bottleneck_recommendations(
                organization=organization,
                workflow=workflow,
                bottlenecks=bottlenecks,
            )
        )

        recommendations.extend(
            self._generate_anomaly_recommendations(
                organization=organization,
                workflow=workflow,
                anomalies=anomalies,
            )
        )

        recommendations.extend(
            self._generate_prediction_recommendations(
                organization=organization,
                workflow=workflow,
                predictions=predictions,
            )
        )

        recommendations.extend(
            self._generate_data_quality_recommendations(
                organization=organization,
                workflow=workflow,
                data_quality=data_quality,
            )
        )

        return recommendations

    def _generate_bottleneck_recommendations(
        self,
        organization,
        workflow,
        bottlenecks,
    ):
        recommendations = []

        if not bottlenecks:
            return recommendations

        for bottleneck in bottlenecks:
            step_name = bottleneck.get("step_name")

            if not step_name:
                continue

            average_duration = self._number(
                bottleneck.get("average_duration")
            )

            expected_duration = self._number(
                bottleneck.get("expected_duration")
            )

            delay_ratio = self._number(
                bottleneck.get("delay_ratio")
            )

            delay_percentage = self._number(
                bottleneck.get("delay_percentage")
            )

            priority = self._bottleneck_priority(
                delay_ratio=delay_ratio,
            )

            recommendation = Recommendation.objects.create(
                organization=organization,
                workflow=workflow,
                title=f"Reduce {step_name} processing delay",
                description=(
                    f"{step_name} is taking longer than its expected "
                    "processing duration. Review capacity, workload, "
                    "and process design for this step."
                ),
                recommendation_type=(
                    Recommendation.RecommendationType.BOTTLENECK
                ),
                priority=priority,
                evidence={
                    "step_name": step_name,
                    "average_duration": average_duration,
                    "expected_duration": expected_duration,
                    "delay_ratio": delay_ratio,
                    "delay_percentage": delay_percentage,
                },
                expected_impact=(
                    f"Reducing delay at {step_name} may improve overall "
                    "workflow throughput and processing time."
                ),
            )

            recommendations.append(recommendation)

        return recommendations

    def _generate_anomaly_recommendations(
        self,
        organization,
        workflow,
        anomalies,
    ):
        recommendations = []

        if anomalies is None:
            return recommendations

        anomaly_dataframe = self._to_records(anomalies)

        for anomaly in anomaly_dataframe:
            if not self._is_anomaly(anomaly):
                continue

            step_name = anomaly.get("step_name", "workflow step")

            duration = self._number(
                anomaly.get("duration_minutes")
            )

            severity = str(
                anomaly.get("anomaly_severity", "MEDIUM")
            ).upper()

            priority = self._anomaly_priority(
                severity=severity,
            )

            recommendation = Recommendation.objects.create(
                organization=organization,
                workflow=workflow,
                title=f"Investigate abnormal duration at {step_name}",
                description=(
                    f"An unusual processing duration was detected for "
                    f"{step_name}. Investigate the underlying event, "
                    "workload, or process condition."
                ),
                recommendation_type=(
                    Recommendation.RecommendationType.ANOMALY
                ),
                priority=priority,
                evidence={
                    "step_name": step_name,
                    "duration_minutes": duration,
                    "anomaly_severity": severity,
                    "anomaly_prediction": anomaly.get(
                        "anomaly_prediction"
                    ),
                    "anomaly_score": self._number(
                        anomaly.get("anomaly_score")
                    ),
                },
                expected_impact=(
                    f"Investigating the abnormal {step_name} event may "
                    "help prevent similar delays."
                ),
            )

            recommendations.append(recommendation)

        return recommendations

    def _generate_prediction_recommendations(
        self,
        organization,
        workflow,
        predictions,
    ):
        recommendations = []

        if predictions is None:
            return recommendations

        prediction_records = self._to_records(predictions)

        for prediction in prediction_records:
            predicted_duration = self._number(
                prediction.get("predicted_duration_minutes")
            )

            if predicted_duration is None:
                continue

            step_name = prediction.get(
                "step_name",
                "workflow step",
            )

            priority = (
                Recommendation.Priority.HIGH
                if predicted_duration >= 10
                else Recommendation.Priority.MEDIUM
            )

            recommendation = Recommendation.objects.create(
                organization=organization,
                workflow=workflow,
                title=f"Review predicted duration for {step_name}",
                description=(
                    f"The model predicts a processing duration of "
                    f"{predicted_duration} minutes for {step_name}. "
                    "Review workload and capacity before delays occur."
                ),
                recommendation_type=(
                    Recommendation.RecommendationType.PREDICTION
                ),
                priority=priority,
                evidence={
                    "step_name": step_name,
                    "predicted_duration_minutes": predicted_duration,
                },
                expected_impact=(
                    f"Planning around the predicted {predicted_duration} "
                    "minute duration may reduce unexpected delays."
                ),
            )

            recommendations.append(recommendation)

        return recommendations

    def _generate_data_quality_recommendations(
        self,
        organization,
        workflow,
        data_quality,
    ):
        recommendations = []

        if not data_quality:
            return recommendations

        quality_score = self._number(
            data_quality.get("quality_score")
        )

        if quality_score is None:
            return recommendations

        if quality_score >= 90:
            return recommendations

        if quality_score < 60:
            priority = Recommendation.Priority.HIGH
        else:
            priority = Recommendation.Priority.MEDIUM

        recommendation = Recommendation.objects.create(
            organization=organization,
            workflow=workflow,
            title="Improve dataset quality",
            description=(
                "The dataset quality score indicates that data should "
                "be reviewed before relying heavily on downstream "
                "analytics and predictions."
            ),
            recommendation_type=(
                Recommendation.RecommendationType.DATA_QUALITY
            ),
            priority=priority,
            evidence={
                "quality_score": quality_score,
                "missing_percentage": self._number(
                    data_quality.get("missing_percentage")
                ),
                "duplicate_percentage": self._number(
                    data_quality.get("duplicate_percentage")
                ),
            },
            expected_impact=(
                "Improving data quality can increase confidence in "
                "analytics, anomaly detection, and predictions."
            ),
        )

        recommendations.append(recommendation)

        return recommendations

    def _bottleneck_priority(self, delay_ratio):
        if delay_ratio is None:
            return Recommendation.Priority.MEDIUM

        if delay_ratio >= self.BOTTLENECK_DELAY_RATIO_HIGH:
            return Recommendation.Priority.HIGH

        if delay_ratio >= self.BOTTLENECK_DELAY_RATIO_MEDIUM:
            return Recommendation.Priority.MEDIUM

        return Recommendation.Priority.LOW

    def _anomaly_priority(self, severity):
        mapping = {
            "CRITICAL": Recommendation.Priority.CRITICAL,
            "HIGH": Recommendation.Priority.HIGH,
            "MEDIUM": Recommendation.Priority.MEDIUM,
            "LOW": Recommendation.Priority.LOW,
        }

        return mapping.get(
            severity,
            Recommendation.Priority.MEDIUM,
        )

    def _is_anomaly(self, anomaly):
        value = anomaly.get("is_anomaly")

        if isinstance(value, bool):
            return value

        prediction = anomaly.get("anomaly_prediction")

        try:
            return int(prediction) == -1
        except (TypeError, ValueError):
            return False

    def _to_records(self, value):
        if value is None:
            return []

        if hasattr(value, "to_dict"):
            return value.to_dict(orient="records")

        if isinstance(value, dict):
            return [value]

        if isinstance(value, (list, tuple)):
            return list(value)

        raise RecommendationEngineError(
            "Recommendation input must be a DataFrame, dictionary, "
            "list, or tuple."
        )

    def _number(self, value):
        if value is None:
            return None

        try:
            number = float(value)
        except (TypeError, ValueError):
            return None

        return number