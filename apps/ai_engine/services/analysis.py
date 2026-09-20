from apps.ai_engine.services.context import (
    AIContextBuilder,
    AIContextError,
)
from apps.ai_engine.services.llm import (
    LLMError,
    LLMService,
)
from apps.ai_engine.services.prompts import (
    AIPromptBuilder,
    AIPromptError,
)
from apps.ai_engine.services.vector_search import (
    KnowledgeVectorSearchService,
    VectorSearchError,
)


class AIAnalysisError(Exception):
    """Raised when AI analysis fails."""


class AIAnalysisService:
    DEFAULT_SYSTEM_PROMPT = (
        "You are an AI workflow analytics assistant. "
        "Analyze the supplied workflow information and provide "
        "clear, factual, actionable observations. "
        "Do not invent data that is not present in the context. "
        "When retrieved knowledge is provided, use it as supporting "
        "context and do not treat unsupported information as fact."
    )

    def __init__(
        self,
        llm_service=None,
        context_builder=None,
        vector_search_service=None,
        prompt_builder=None,
    ):
        self.llm_service = (
            llm_service
            or LLMService()
        )

        self.context_builder = (
            context_builder
            or AIContextBuilder()
        )

        self.vector_search_service = (
            vector_search_service
            or KnowledgeVectorSearchService()
        )

        self.prompt_builder = (
            prompt_builder
            or AIPromptBuilder()
        )

    def analyze(
        self,
        workflow=None,
        duration_analytics=None,
        bottlenecks=None,
        anomalies=None,
        predictions=None,
        explainability=None,
        system_prompt=None,
        temperature=0.2,
        max_tokens=1000,
        query=None,
        organization=None,
        top_k=5,
        prompt_type=None,
    ):
        retrieved_knowledge = None

        if query is not None:
            if organization is None:
                raise AIAnalysisError(
                    "organization is required when query is provided."
                )

            try:
                retrieved_knowledge = (
                    self.vector_search_service.search(
                        query=query,
                        organization=organization,
                        top_k=top_k,
                    )
                )
            except VectorSearchError as exc:
                raise AIAnalysisError(
                    str(exc)
                ) from exc

        try:
            structured_context = (
                self.context_builder.build(
                    workflow=workflow,
                    duration_analytics=duration_analytics,
                    bottlenecks=bottlenecks,
                    anomalies=anomalies,
                    predictions=predictions,
                    explainability=explainability,
                )
            )

            if retrieved_knowledge is not None:
                structured_context[
                    "retrieved_knowledge"
                ] = self._format_retrieved_knowledge(
                    retrieved_knowledge
                )

            prompt_context = (
                self._build_prompt_context(
                    structured_context
                )
            )

            resolved_prompt_type = (
                prompt_type
                or self._resolve_prompt_type(
                    query=query,
                    bottlenecks=bottlenecks,
                    anomalies=anomalies,
                    predictions=predictions,
                )
            )

            prompt = self.prompt_builder.build(
                prompt_type=resolved_prompt_type,
                context=prompt_context,
            )

        except (
            AIContextError,
            AIPromptError,
        ) as exc:
            raise AIAnalysisError(
                str(exc)
            ) from exc

        try:
            response = self.llm_service.generate(
                prompt=prompt,
                system_prompt=(
                    system_prompt
                    or self.DEFAULT_SYSTEM_PROMPT
                ),
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except LLMError as exc:
            raise AIAnalysisError(
                str(exc)
            ) from exc

        return {
            "prompt": prompt,
            "response": response,
            "context": structured_context,
            "retrieved_knowledge": (
                retrieved_knowledge
            ),
            "prompt_type": resolved_prompt_type,
        }

    def _build_prompt_context(
        self,
        structured_context,
    ):
        if not structured_context:
            raise AIContextError(
                "No AI context was supplied."
            )

        sections = []

        for key, value in structured_context.items():
            title = key.replace(
                "_",
                " ",
            ).upper()

            sections.append(
                f"{title}\n{value}"
            )

        if not sections:
            raise AIContextError(
                "No AI context sections were created."
            )

        return "\n\n".join(sections)

    def _format_retrieved_knowledge(
        self,
        retrieved_knowledge,
    ):
        formatted = []

        for index, result in enumerate(
            retrieved_knowledge,
            start=1,
        ):
            chunk = result["chunk"]
            document = result["document"]
            similarity = result["similarity"]

            formatted.append(
                {
                    "rank": index,
                    "document_title": document.title,
                    "chunk_index": chunk.chunk_index,
                    "content": chunk.content,
                    "similarity": round(
                        similarity,
                        6,
                    ),
                }
            )

        return formatted

    def _resolve_prompt_type(
        self,
        query=None,
        bottlenecks=None,
        anomalies=None,
        predictions=None,
    ):
        if query is not None:
            return AIPromptBuilder.RAG_QUESTION

        if bottlenecks is not None:
            return AIPromptBuilder.BOTTLENECK_ANALYSIS

        if anomalies is not None:
            return AIPromptBuilder.ANOMALY_ANALYSIS

        if predictions is not None:
            return AIPromptBuilder.PREDICTION_ANALYSIS

        return AIPromptBuilder.WORKFLOW_ANALYSIS