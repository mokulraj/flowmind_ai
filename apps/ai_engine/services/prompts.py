class AIPromptError(Exception):
    """Raised when an AI prompt cannot be created."""


class AIPromptBuilder:
    """
    Builds structured prompts for FlowMind AI tasks.
    """

    WORKFLOW_ANALYSIS = "workflow_analysis"
    BOTTLENECK_ANALYSIS = "bottleneck_analysis"
    ANOMALY_ANALYSIS = "anomaly_analysis"
    PREDICTION_ANALYSIS = "prediction_analysis"
    OPERATIONAL_SUMMARY = "operational_summary"
    RAG_QUESTION = "rag_question"

    SUPPORTED_PROMPT_TYPES = {
        WORKFLOW_ANALYSIS,
        BOTTLENECK_ANALYSIS,
        ANOMALY_ANALYSIS,
        PREDICTION_ANALYSIS,
        OPERATIONAL_SUMMARY,
        RAG_QUESTION,
    }

    def build(
        self,
        prompt_type,
        context,
    ):
        """
        Build a prompt for the requested AI task.
        """

        self._validate_prompt_type(prompt_type)
        self._validate_context(context)

        builder = {
            self.WORKFLOW_ANALYSIS:
                self._workflow_analysis,
            self.BOTTLENECK_ANALYSIS:
                self._bottleneck_analysis,
            self.ANOMALY_ANALYSIS:
                self._anomaly_analysis,
            self.PREDICTION_ANALYSIS:
                self._prediction_analysis,
            self.OPERATIONAL_SUMMARY:
                self._operational_summary,
            self.RAG_QUESTION:
                self._rag_question,
        }[prompt_type]

        return builder(context)

    def _workflow_analysis(self, context):
        return (
            "Analyze the workflow context below.\n\n"
            "Identify important workflow behavior, "
            "performance observations, and operational "
            "insights. Use only information present in "
            "the supplied context.\n\n"
            f"{context}"
        )

    def _bottleneck_analysis(self, context):
        return (
            "Analyze the workflow bottleneck information "
            "below.\n\n"
            "Identify the affected workflow steps, "
            "their observed delays, severity information, "
            "and relevant operational implications. "
            "Do not invent measurements that are not "
            "present in the context.\n\n"
            f"{context}"
        )

    def _anomaly_analysis(self, context):
        return (
            "Analyze the workflow anomaly information "
            "below.\n\n"
            "Identify unusual workflow behavior and "
            "describe the relevant evidence contained "
            "in the supplied context. Do not invent "
            "causes that are not supported by the data.\n\n"
            f"{context}"
        )

    def _prediction_analysis(self, context):
        return (
            "Analyze the workflow prediction information "
            "below.\n\n"
            "Explain the available prediction results "
            "and their supporting information. Clearly "
            "distinguish observed data from predictions "
            "and do not invent unsupported values.\n\n"
            f"{context}"
        )

    def _operational_summary(self, context):
        return (
            "Create a concise operational summary from "
            "the following FlowMind workflow context.\n\n"
            "Highlight important observations across "
            "workflow performance, bottlenecks, anomalies, "
            "predictions, and other supplied information. "
            "Use only the supplied information.\n\n"
            f"{context}"
        )

    def _rag_question(self, context):
        return (
            "Answer the workflow question using the "
            "supplied FlowMind context and retrieved "
            "knowledge.\n\n"
            "Use retrieved knowledge as supporting context. "
            "Do not invent information that is not present "
            "in the supplied context. If the context does "
            "not contain enough information to answer a "
            "question, clearly state that limitation.\n\n"
            f"{context}"
        )

    def _validate_prompt_type(self, prompt_type):
        if prompt_type not in self.SUPPORTED_PROMPT_TYPES:
            raise AIPromptError(
                f"Unsupported prompt type: {prompt_type}"
            )

    def _validate_context(self, context):
        if context is None:
            raise AIPromptError(
                "Prompt context cannot be None."
            )

        if not str(context).strip():
            raise AIPromptError(
                "Prompt context cannot be empty."
            )