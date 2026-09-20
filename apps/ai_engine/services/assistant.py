from apps.ai_engine.services.analysis import (
    AIAnalysisError,
    AIAnalysisService,
)


class AIWorkflowAssistantError(Exception):
    """Raised when the AI workflow assistant fails."""


class AIWorkflowAssistant:
    """
    Application-level interface for FlowMind AI assistance.

    This service coordinates workflow analytics context,
    RAG retrieval, and AI analysis.
    """

    DEFAULT_QUERY = (
        "Analyze the supplied workflow information and "
        "identify the most important operational observations."
    )

    def __init__(self, analysis_service=None):
        self.analysis_service = (
            analysis_service
            or AIAnalysisService()
        )

    def ask(
        self,
        query=None,
        organization=None,
        workflow=None,
        duration_analytics=None,
        bottlenecks=None,
        anomalies=None,
        predictions=None,
        explainability=None,
        system_prompt=None,
        temperature=0.2,
        max_tokens=1000,
        top_k=5,
    ):
        """
        Ask the FlowMind AI assistant a question.

        A query combined with an organization enables RAG retrieval.
        """

        resolved_query = self._resolve_query(
            query=query,
            workflow=workflow,
            duration_analytics=duration_analytics,
            bottlenecks=bottlenecks,
            anomalies=anomalies,
            predictions=predictions,
            explainability=explainability,
        )

        if query is not None and organization is None:
            raise AIWorkflowAssistantError(
                "organization is required when query is provided."
            )

        if query is not None and not resolved_query:
            raise AIWorkflowAssistantError(
                "query cannot be empty."
            )

        try:
            result = self.analysis_service.analyze(
                workflow=workflow,
                duration_analytics=duration_analytics,
                bottlenecks=bottlenecks,
                anomalies=anomalies,
                predictions=predictions,
                explainability=explainability,
                system_prompt=system_prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                query=(
                    resolved_query
                    if query is not None
                    else None
                ),
                organization=organization,
                top_k=top_k,
            )
        except AIAnalysisError as exc:
            raise AIWorkflowAssistantError(
                str(exc)
            ) from exc

        return {
            "query": resolved_query,
            "response": result["response"],
            "context": result["context"],
            "retrieved_knowledge": result[
                "retrieved_knowledge"
            ],
            "prompt": result["prompt"],
        }

    def _resolve_query(
        self,
        query=None,
        workflow=None,
        duration_analytics=None,
        bottlenecks=None,
        anomalies=None,
        predictions=None,
        explainability=None,
    ):
        if query is not None:
            if not isinstance(query, str):
                raise AIWorkflowAssistantError(
                    "query must be a string."
                )

            resolved_query = query.strip()

            if not resolved_query:
                raise AIWorkflowAssistantError(
                    "query cannot be empty."
                )

            return resolved_query

        if self._has_analysis_context(
            workflow=workflow,
            duration_analytics=duration_analytics,
            bottlenecks=bottlenecks,
            anomalies=anomalies,
            predictions=predictions,
            explainability=explainability,
        ):
            return self.DEFAULT_QUERY

        return self.DEFAULT_QUERY

    @staticmethod
    def _has_analysis_context(
        workflow=None,
        duration_analytics=None,
        bottlenecks=None,
        anomalies=None,
        predictions=None,
        explainability=None,
    ):
        return any(
            value is not None
            for value in (
                workflow,
                duration_analytics,
                bottlenecks,
                anomalies,
                predictions,
                explainability,
            )
        )