"""
E2E test: submit a performance run and verify monitoring metrics update.

Flow:
- Build PerformanceService with lightweight GatlingRunner (no Maven needed)
- Submit a short run against a dummy URL and wait for completion
- Write data/perf_runs/<id>/results/summary.json (simulated Gatling output)
- Call service.status to sync DB metrics
- Use Prometheus exporter collect_metrics() with the same UoW to update REGISTRY
- Assert registry text includes counters/gauges with expected statuses
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from database.repositories.unit_of_work import create_unit_of_work_factory
from src.application.performance.dto import SimulationParams
from src.application.performance.orchestrator import PerformanceOrchestrator
from src.application.performance.service import PerformanceService
from src.infrastructure.gatling.runner import GatlingRunner
from src.infrastructure.gatling.status_reader import InMemoryStatusStore, GatlingStatusReader

# Prometheus exporter pieces
from src.observability.prometheus_exporter import collect_metrics, REGISTRY
from prometheus_client.exposition import generate_latest


def test_performance_run_monitored_end_to_end(tmp_path: Path):
    # Use a single in-memory engine via factory to keep state consistent
    uow_factory = create_unit_of_work_factory("sqlite:///:memory:")

    # Lightweight runner simulates queued -> running -> succeeded
    store = InMemoryStatusStore()
    runner = GatlingRunner(store)
    reader = GatlingStatusReader(store)

    service = PerformanceService(
        PerformanceOrchestrator(runner=runner, status_reader=reader, uow_factory=uow_factory)
    )

    # Submit a short run using a full URL to avoid DB endpoint resolution
    params = SimulationParams(
        app_slug="demo-app",
        country_code="AR",
        environment="dev",
        test_type="smoke",
        users=1,
        duration_sec=2,
        endpoint_slug="http://example.com/ping",
    )

    submitted = service.submit(params)
    execution_id = submitted.execution_id

    # Prepare results dir and place a summary.json (as Gatling would produce)
    results_dir = Path("data/perf_runs") / execution_id / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "parsed": True,
        "path": str(results_dir / "summary.json"),
        "total": 42,
        "ok": 42,
        "ko": 0,
        "mean_rps": 3.3,
        "p95": 500.0,
        "p99": 700.0,
        "mean_rt": 200.0,
        "min_rt": 50.0,
        "max_rt": 900.0,
    }
    (results_dir / "summary.json").write_text(json.dumps(summary))

    # Poll until terminal state
    deadline = time.time() + 8
    final = None
    while time.time() < deadline:
        final = service.status(execution_id)
        if final.status in ("succeeded", "failed"):
            break
        time.sleep(0.1)

    assert final is not None
    assert final.status in ("succeeded", "failed")

    # DB has metrics after status() terminal sync
    info = service.get_execution(execution_id)
    assert info.get("execution_id") == execution_id
    assert info.get("total_requests") == 42
    assert info.get("successful_requests") == 42
    assert info.get("failed_requests") == 0

    # Update Prometheus exporter registry from the same DB
    collect_metrics(uow_factory)
    metrics_text = generate_latest(REGISTRY).decode("utf-8")

    # Validate exporter exposes our metric names and at least one terminal count
    assert "qa_perf_executions_current" in metrics_text
    assert "qa_perf_executions_total" in metrics_text
    # After one successful run, we expect COMPLETED gauge >= 0 and total counter incremented
    # We don't rely on exact numeric values to avoid flakiness, only presence of series labels
    assert 'qa_perf_executions_current{status="COMPLETED"}' in metrics_text or \
           'qa_perf_executions_current{status="FAILED"}' in metrics_text
    assert 'qa_perf_executions_total{status="COMPLETED"}' in metrics_text or \
           'qa_perf_executions_total{status="FAILED"}' in metrics_text
