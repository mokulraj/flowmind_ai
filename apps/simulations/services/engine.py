from numbers import Real

from apps.simulations.models import Simulation


class SimulationEngineError(Exception):
    """Raised when a simulation cannot be calculated."""


class SimulationEngine:
    """
    Calculates projected workflow metrics for a workload scenario.

    The engine keeps the simulation calculation logic separate from the
    Simulation model so that it can later be reused by APIs, dashboards,
    recommendations, and other services.
    """

    def run(
        self,
        simulation: Simulation,
        *,
        baseline_event_count=None,
        baseline_avg_duration=None,
        baseline_total_duration=None,
    ):
        if not isinstance(simulation, Simulation):
            raise SimulationEngineError(
                "simulation must be a Simulation instance."
            )

        workload_change = simulation.workload_change_percent

        if workload_change <= -100:
            raise SimulationEngineError(
                "workload_change_percent must be greater than -100."
            )

        event_count = self._resolve_value(
            baseline_event_count,
            simulation.baseline_event_count,
            "baseline_event_count",
        )

        avg_duration = self._resolve_value(
            baseline_avg_duration,
            simulation.baseline_avg_duration,
            "baseline_avg_duration",
        )

        total_duration = self._resolve_value(
            baseline_total_duration,
            simulation.baseline_total_duration,
            "baseline_total_duration",
        )

        projected_event_count = self._project_value(
            event_count,
            workload_change,
        )

        projected_total_duration = self._project_value(
            total_duration,
            workload_change,
        )

        projected_avg_duration = avg_duration

        simulation.baseline_event_count = event_count
        simulation.projected_event_count = projected_event_count

        simulation.baseline_avg_duration = avg_duration
        simulation.projected_avg_duration = projected_avg_duration

        simulation.baseline_total_duration = total_duration
        simulation.projected_total_duration = projected_total_duration

        simulation.results = {
            "workload_change_percent": workload_change,
            "baseline_event_count": event_count,
            "projected_event_count": projected_event_count,
            "event_count_change": (
                projected_event_count - event_count
            ),
            "baseline_avg_duration": avg_duration,
            "projected_avg_duration": projected_avg_duration,
            "baseline_total_duration": total_duration,
            "projected_total_duration": projected_total_duration,
            "total_duration_change": (
                projected_total_duration - total_duration
            ),
        }

        simulation.status = Simulation.Status.COMPLETED
        simulation.save()

        return simulation

    @staticmethod
    def _resolve_value(value, fallback, field_name):
        if value is None:
            value = fallback

        if not isinstance(value, Real):
            raise SimulationEngineError(
                f"{field_name} must be numeric."
            )

        if value < 0:
            raise SimulationEngineError(
                f"{field_name} cannot be negative."
            )

        return value

    @staticmethod
    def _project_value(value, percentage):
        projected = value * (1 + (percentage / 100))

        if isinstance(value, int):
            return max(0, round(projected))

        return max(0.0, projected)