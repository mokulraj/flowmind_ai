from apps.audit.models import AuditLog
from apps.audit.services.audit_service import AuditLogService
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
    - audit logging
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

            self._create_audit_log(
                simulation=simulation,
                bottlenecks=bottlenecks,
                recommendation=recommendation,
                generate_recommendation=generate_recommendation,
            )

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

    def _create_audit_log(
        self,
        simulation,
        bottlenecks,
        recommendation,
        generate_recommendation,
    ):
        organization = simulation.organization

        bottleneck_count = 0

        if bottlenecks is not None:
            try:
                bottleneck_count = len(bottlenecks)
            except TypeError:
                bottleneck_count = 0

        AuditLogService.create(
            organization=organization,
            action=AuditLog.Action.RUN,
            object_type="Simulation",
            object_id=simulation.id,
            object_repr=str(simulation),
            description=(
                f"Simulation '{simulation.name}' completed."
            ),
            metadata={
                "simulation_id": simulation.id,
                "simulation_name": simulation.name,
                "workflow_id": (
                    simulation.workflow_id
                    if simulation.workflow_id
                    else None
                ),
                "status": simulation.status,
                "workload_change_percent": (
                    simulation.workload_change_percent
                ),
                "baseline_event_count": (
                    simulation.baseline_event_count
                ),
                "projected_event_count": (
                    simulation.projected_event_count
                ),
                "baseline_avg_duration": (
                    simulation.baseline_avg_duration
                ),
                "projected_avg_duration": (
                    simulation.projected_avg_duration
                ),
                "baseline_total_duration": (
                    simulation.baseline_total_duration
                ),
                "projected_total_duration": (
                    simulation.projected_total_duration
                ),
                "bottleneck_count": bottleneck_count,
                "recommendation_generated": (
                    recommendation is not None
                ),
                "generate_recommendation": (
                    generate_recommendation
                ),
            },
        )