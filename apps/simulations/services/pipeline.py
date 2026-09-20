from apps.simulations.models import Simulation
from apps.simulations.services.bottleneck import (
    BottleneckSimulationError,
    BottleneckSimulationService,
)
from apps.simulations.services.engine import (
    SimulationEngine,
    SimulationEngineError,
)
from apps.simulations.services.recommendations import (
    SimulationRecommendationError,
    SimulationRecommendationService,
)


class SimulationPipelineError(Exception):
    """Raised when the simulation pipeline cannot complete."""


class SimulationPipeline:
    """
    Orchestrates the complete simulation workflow.

    The pipeline combines:
    - baseline workload projection
    - bottleneck-aware simulation
    - optional recommendation generation
    """

    def __init__(
        self,
        engine=None,
        bottleneck_service=None,
        recommendation_service=None,
    ):
        self.engine = engine or SimulationEngine()
        self.bottleneck_service = (
            bottleneck_service
            or BottleneckSimulationService()
        )
        self.recommendation_service = (
            recommendation_service
            or SimulationRecommendationService()
        )

    def run(
        self,
        simulation,
        *,
        baseline_event_count=None,
        baseline_avg_duration=None,
        baseline_total_duration=None,
        bottlenecks=None,
        generate_recommendation=True,
    ):
        if not isinstance(simulation, Simulation):
            raise SimulationPipelineError(
                "simulation must be a Simulation instance."
            )

        try:
            simulation = self.engine.run(
                simulation,
                baseline_event_count=baseline_event_count,
                baseline_avg_duration=baseline_avg_duration,
                baseline_total_duration=baseline_total_duration,
            )

            if bottlenecks is not None:
                simulation = self.bottleneck_service.run(
                    simulation,
                    bottlenecks,
                )

            recommendation = None

            if generate_recommendation:
                recommendation = (
                    self.recommendation_service.generate(
                        simulation
                    )
                )

            simulation.refresh_from_db()

            return {
                "simulation": simulation,
                "recommendation": recommendation,
                "results": simulation.results,
            }

        except (
            SimulationEngineError,
            BottleneckSimulationError,
            SimulationRecommendationError,
        ) as exc:
            raise SimulationPipelineError(
                str(exc)
            ) from exc