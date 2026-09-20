import pandas as pd


class AIContextError(Exception):
    """Raised when AI context construction fails."""


class AIContextBuilder:
    """Builds structured context for AI analysis."""

    def build(
        self,
        workflow=None,
        duration_analytics=None,
        bottlenecks=None,
        anomalies=None,
        predictions=None,
        explainability=None,
    ):
        context = {
            "workflow": self._workflow_context(workflow),
            "duration_analytics": self._safe_value(duration_analytics),
            "bottlenecks": self._safe_value(bottlenecks),
            "anomalies": self._safe_value(anomalies),
            "predictions": self._safe_value(predictions),
            "explainability": self._safe_value(explainability),
        }

        return {
            key: value
            for key, value in context.items()
            if value is not None
        }

    def build_prompt_context(
        self,
        workflow=None,
        duration_analytics=None,
        bottlenecks=None,
        anomalies=None,
        predictions=None,
        explainability=None,
    ):
        context = self.build(
            workflow=workflow,
            duration_analytics=duration_analytics,
            bottlenecks=bottlenecks,
            anomalies=anomalies,
            predictions=predictions,
            explainability=explainability,
        )

        if not context:
            raise AIContextError(
                "At least one valid context source is required."
            )

        return self._format_context(context)

    def _workflow_context(self, workflow):
        if workflow is None:
            return None

        return {
            "id": getattr(workflow, "id", None),
            "name": getattr(workflow, "name", None),
            "description": getattr(workflow, "description", None),
            "category": getattr(workflow, "category", None),
            "status": getattr(workflow, "status", None),
        }

    def _safe_value(self, value):
        if value is None:
            return None

        if isinstance(value, pd.DataFrame):
            return value.to_dict(orient="records")

        if isinstance(value, (dict, list)):
            return value

        return value

    def _format_context(self, context):
        sections = []

        section_labels = {
            "workflow": "WORKFLOW CONTEXT",
            "duration_analytics": "DURATION ANALYTICS",
            "bottlenecks": "BOTTLENECKS",
            "anomalies": "ANOMALIES",
            "predictions": "PREDICTIONS",
            "explainability": "EXPLAINABILITY",
        }

        for key, label in section_labels.items():
            if key not in context:
                continue

            sections.append(
                f"{label}:\n{context[key]}"
            )

        if not sections:
            raise AIContextError(
                "No usable context sections were provided."
            )

        return "\n\n".join(sections)