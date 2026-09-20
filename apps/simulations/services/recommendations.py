from apps.recommendations.models import Recommendation
from apps.simulations.models import Simulation


class SimulationRecommendationError(Exception):
    """Raised when a simulation recommendation cannot be generated."""


class SimulationRecommendationService:
    """
    Creates recommendations from completed simulation results.

    The service does not replace the existing recommendation engine.
    It provides simulation-specific evidence that can be consumed by
    the recommendation system.
    """

    def generate(self, simulation: Simulation):
        if not isinstance(simulation, Simulation):
            raise SimulationRecommendationError(
                "simulation must be a Simulation instance."
            )

        if simulation.status != Simulation.Status.COMPLETED:
            raise SimulationRecommendationError(
                "Only completed simulations can generate recommendations."
            )

        if not simulation.workflow_id:
            raise SimulationRecommendationError(
                "Simulation must be associated with a workflow."
            )

        results = simulation.results or {}

        projected_event_count = self._number(
            results.get("projected_event_count"),
            "projected_event_count",
        )

        baseline_event_count = self._number(
            results.get("baseline_event_count"),
            "baseline_event_count",
        )

        projected_duration = self._number(
            results.get("projected_bottleneck_duration"),
            "projected_bottleneck_duration",
            default=0.0,
        )

        baseline_duration = self._number(
            results.get("baseline_bottleneck_duration"),
            "baseline_bottleneck_duration",
            default=0.0,
        )

        event_increase = (
            projected_event_count - baseline_event_count
        )

        duration_increase = (
            projected_duration - baseline_duration
        )

        if event_increase <= 0 and duration_increase <= 0:
            return None

        workload_change = simulation.workload_change_percent

        title = (
            f"Simulation indicates increased workload impact: "
            f"{simulation.name}"
        )

        description = (
            f"The simulation projects a {workload_change:.1f}% "
            "workload change with measurable impact on workflow "
            "capacity or bottleneck duration."
        )

        priority = self._priority(
            workload_change=workload_change,
            duration_increase=duration_increase,
        )

        evidence = {
            "source": "simulation",
            "simulation_id": simulation.id,
            "simulation_name": simulation.name,
            "workload_change_percent": workload_change,
            "baseline_event_count": baseline_event_count,
            "projected_event_count": projected_event_count,
            "event_count_change": event_increase,
            "baseline_bottleneck_duration": baseline_duration,
            "projected_bottleneck_duration": projected_duration,
            "bottleneck_duration_change": duration_increase,
            "simulation_results": results,
        }

        recommendation = Recommendation.objects.create(
            organization=simulation.organization,
            workflow=simulation.workflow,
            title=title,
            description=description,
            recommendation_type="CAPACITY",
            priority=priority,
            evidence=evidence,
            expected_impact=(
                "Evaluate workflow capacity and bottleneck "
                "mitigation before accepting the simulated "
                "workload increase."
            ),
        )

        return recommendation

    @staticmethod
    def _number(value, field_name, default=None):
        if value is None and default is not None:
            return default

        if isinstance(value, bool) or not isinstance(
            value,
            (int, float),
        ):
            raise SimulationRecommendationError(
                f"{field_name} must be numeric."
            )

        return float(value)

    @staticmethod
    def _priority(
        *,
        workload_change,
        duration_increase,
    ):
        if workload_change >= 50 or duration_increase >= 20:
            return "CRITICAL"

        if workload_change >= 25 or duration_increase >= 10:
            return "HIGH"

        if workload_change > 0 or duration_increase > 0:
            return "MEDIUM"

        return "LOW"