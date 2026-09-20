from apps.analytics.services.pipeline import AnalyticsPipeline

from .detector import BottleneckDetector


class BottleneckPipeline:
    """
    Runs the complete dataset analytics pipeline and then
    detects workflow bottlenecks.
    """

    def __init__(self, dataset):
        self.dataset = dataset

    def run(self):
        analytics_pipeline = AnalyticsPipeline(
            dataset=self.dataset
        )

        analytics_result = analytics_pipeline.run()

        duration_analytics = analytics_result[
            "duration_analytics"
        ]

        workflow_steps = self.dataset.workflow.steps.all()

        detector = BottleneckDetector(
            analytics_dataframe=duration_analytics,
            workflow_steps=workflow_steps,
        )

        bottleneck_results = detector.detect()

        return {
            "preprocessing": analytics_result[
                "preprocessing"
            ],
            "duration_analytics": duration_analytics,
            "bottlenecks": bottleneck_results,
        }