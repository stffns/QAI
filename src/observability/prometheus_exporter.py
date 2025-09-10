from __future__ import annotations

"""Prometheus exporter for performance executions (separate from agent).

Starts an HTTP server and exposes low-cardinality metrics aggregated from DB.
"""

from typing import Optional

from prometheus_client import Counter, Gauge, start_http_server, CollectorRegistry

# Absolute-first imports with fallback to handle direct runs
try:
    from config import get_settings
    from database.repositories.unit_of_work import create_unit_of_work_factory
    from database.repositories.performance_test_executions import PerformanceTestExecutionRepository
    from database.models.performance_test_executions import ExecutionStatus
except ImportError:  # pragma: no cover - fallback
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
    from config import get_settings  # type: ignore
    from database.repositories.unit_of_work import create_unit_of_work_factory  # type: ignore
    from database.repositories.performance_test_executions import PerformanceTestExecutionRepository  # type: ignore
    from database.models.performance_test_executions import ExecutionStatus  # type: ignore


# Use a dedicated registry to avoid duplicates on module re-import/reload
REGISTRY = CollectorRegistry()

EXECUTIONS_TOTAL = Counter(
    "qa_perf_executions_total",
    "Total number of performance executions by status (monotonic; terminal states only)",
    labelnames=("status",),
    registry=REGISTRY,
)

EXECUTIONS_CURRENT = Gauge(
    "qa_perf_executions_current",
    "Current number of running/pending executions",
    labelnames=("status",),
    registry=REGISTRY,
)


_LAST_COUNTS = {"COMPLETED": 0, "FAILED": 0}


def collect_metrics(uow_factory) -> None:
    with uow_factory.create_scope() as uow:
        repo = uow.get_repository(PerformanceTestExecutionRepository)
        # Simple counts by status
        pending = len(repo.find_by_status(ExecutionStatus.PENDING))
        running = len(repo.find_by_status(ExecutionStatus.RUNNING))
        completed = len(repo.find_by_status(ExecutionStatus.COMPLETED))
        failed = len(repo.find_by_status(ExecutionStatus.FAILED))

        # Update counters and gauges (avoid high cardinality; no execution_id labels)
        # Counters: increment only terminal states using deltas to keep monotonicity
        for status_name, count in (
            ("PENDING", pending),
            ("RUNNING", running),
            ("COMPLETED", completed),
            ("FAILED", failed),
        ):
            # Gauges reflect current values
            EXECUTIONS_CURRENT.labels(status=status_name).set(count)

        # Terminal states counters
        for terminal_name, current in (("COMPLETED", completed), ("FAILED", failed)):
            last = _LAST_COUNTS.get(terminal_name, 0)
            delta = max(0, current - last)
            if delta:
                EXECUTIONS_TOTAL.labels(status=terminal_name).inc(delta)
                _LAST_COUNTS[terminal_name] = current


def run_exporter(port: int = 9400) -> None:
    settings = get_settings()
    uow_factory: Optional[object] = None
    try:
        if settings.database.url:
            uow_factory = create_unit_of_work_factory(settings.database.url)
    except Exception:
        uow_factory = None

    # Bind HTTP server to the dedicated registry
    start_http_server(port, registry=REGISTRY)
    # Very simple polling loop; in production, integrate into your scheduler
    import time
    while True:
        try:
            if uow_factory:
                collect_metrics(uow_factory)
        except Exception:
            pass
        time.sleep(10)


if __name__ == "__main__":
    run_exporter()
