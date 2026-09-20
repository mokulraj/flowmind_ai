from numbers import Real

from apps.simulations.models import Simulation


class BottleneckSimulationError(Exception):
    """Raised when a bottleneck-aware simulation cannot be calculated."""


class BottleneckSimulationService:
    """
    Calculates the effect of workload changes on workflow bottlenecks.

    The service uses bottleneck records supplied by the caller rather than
    directly querying a specific bottleneck model. This keeps the simulation
    layer independent from the bottleneck detection implementation.
    """

    SEVERITY_MULTIPLIERS = {
        "CRITICAL": 1.50,
        "HIGH": 1.35,
        "MEDIUM": 1.20,
        "LOW": 1.10,
    }

    def run(
        self,
        simulation: Simulation,
        bottlenecks,
    ):
        if not isinstance(simulation, Simulation):
            raise BottleneckSimulationError(
                "simulation must be a Simulation instance."
            )

        if not isinstance(bottlenecks, (list, tuple)):
            raise BottleneckSimulationError(
                "bottlenecks must be a list or tuple."
            )

        workload_factor = (
            1 + simulation.workload_change_percent / 100
        )

        if workload_factor <= 0:
            raise BottleneckSimulationError(
                "workload change must produce a positive workload factor."
            )

        processed_bottlenecks = []

        for bottleneck in bottlenecks:
            processed_bottlenecks.append(
                self._simulate_bottleneck(
                    bottleneck,
                    workload_factor,
                )
            )

        total_baseline_duration = sum(
            item["baseline_avg_duration"]
            for item in processed_bottlenecks
        )

        total_projected_duration = sum(
            item["projected_avg_duration"]
            for item in processed_bottlenecks
        )

        duration_change = (
            total_projected_duration - total_baseline_duration
        )

        simulation.results = {
            **simulation.results,
            "bottleneck_count": len(processed_bottlenecks),
            "bottlenecks": processed_bottlenecks,
            "baseline_bottleneck_duration": total_baseline_duration,
            "projected_bottleneck_duration": total_projected_duration,
            "bottleneck_duration_change": duration_change,
        }

        simulation.projected_avg_duration = (
            total_projected_duration
        )

        simulation.status = Simulation.Status.COMPLETED
        simulation.save()

        return simulation

    def _simulate_bottleneck(
        self,
        bottleneck,
        workload_factor,
    ):
        name = self._get_value(
            bottleneck,
            "step_name",
            "Unnamed Step",
        )

        baseline_duration = self._get_number(
            bottleneck,
            "avg_duration",
            0.0,
        )

        severity = str(
            self._get_value(
                bottleneck,
                "severity",
                "MEDIUM",
            )
        ).upper()

        multiplier = self.SEVERITY_MULTIPLIERS.get(
            severity,
            self.SEVERITY_MULTIPLIERS["MEDIUM"],
        )

        if workload_factor <= 1:
            projected_duration = (
                baseline_duration * workload_factor
            )
        else:
            projected_duration = (
                baseline_duration
                * workload_factor
                * multiplier
            )

        return {
            "step_name": name,
            "severity": severity,
            "baseline_avg_duration": baseline_duration,
            "workload_factor": workload_factor,
            "severity_multiplier": multiplier,
            "projected_avg_duration": projected_duration,
            "duration_change": (
                projected_duration - baseline_duration
            ),
        }

    @staticmethod
    def _get_value(record, field, default=None):
        if isinstance(record, dict):
            return record.get(field, default)

        return getattr(record, field, default)

    @staticmethod
    def _get_number(record, field, default=0.0):
        value = BottleneckSimulationService._get_value(
            record,
            field,
            default,
        )

        if not isinstance(value, Real):
            raise BottleneckSimulationError(
                f"{field} must be numeric."
            )

        if value < 0:
            raise BottleneckSimulationError(
                f"{field} cannot be negative."
            )

        return float(value)