from .context import AIContextBuilder, AIContextError
from .llm import LLMError, LLMService


class AIAnalysisError(Exception):
    """Raised when AI analysis fails."""


class AIAnalysisService:
    """Service responsible for preparing context and generating AI analysis."""

    DEFAULT_SYSTEM_PROMPT = (
        "You are an AI workflow analytics assistant. "
        "Analyze the supplied workflow information and provide "
        "clear, factual, actionable observations. "
        "Do not invent data that is not present in the context."
    )

    def __init__(
        self,
        llm_service=None,
        context_builder=None,
    ):
        self.llm_service = llm_service or LLMService()
        self.context_builder = context_builder or AIContextBuilder()

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
    ):
        try:
            structured_context = self.context_builder.build(
                workflow=workflow,
                duration_analytics=duration_analytics,
                bottlenecks=bottlenecks,
                anomalies=anomalies,
                predictions=predictions,
                explainability=explainability,
            )

            prompt_context = self.context_builder.build_prompt_context(
                workflow=workflow,
                duration_analytics=duration_analytics,
                bottlenecks=bottlenecks,
                anomalies=anomalies,
                predictions=predictions,
                explainability=explainability,
            )

        except AIContextError as exc:
            raise AIAnalysisError(str(exc)) from exc

        prompt = self._build_prompt(prompt_context)

        try:
            response = self.llm_service.generate(
                prompt=prompt,
                system_prompt=(
                    system_prompt or self.DEFAULT_SYSTEM_PROMPT
                ),
                temperature=temperature,
                max_tokens=max_tokens,
            )
        except LLMError as exc:
            raise AIAnalysisError(str(exc)) from exc

        return {
            "prompt": prompt,
            "response": response,
            "context": structured_context,
        }

    def _build_prompt(self, context):
        return (
            "Analyze the following FlowMind workflow context "
            "and provide clear, factual observations and "
            "actionable insights.\n\n"
            f"{context}"
        )