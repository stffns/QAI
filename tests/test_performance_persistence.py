"""
E2E test: verifies that performance run metrics are persisted to DB from summary.json

Flow:
- Build a PerformanceService with the lightweight GatlingRunner (no Maven)
- Submit a short run against a dummy URL
- Create data/perf_runs/<id>/results/summary.json with sample metrics
- Wait for the runner to mark the run succeeded
- Call service.status(execution_id) to trigger DB sync and metrics update
- Fetch via service.get_execution and assert fields present
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from src.application.performance.dto import SimulationParams
from src.application.performance.service import PerformanceService
from src.application.performance.orchestrator import PerformanceOrchestrator
from src.infrastructure.gatling.runner import GatlingRunner
from src.infrastructure.gatling.status_reader import InMemoryStatusStore, GatlingStatusReader
from database.repositories.unit_of_work import create_unit_of_work_factory


def test_perf_metrics_persisted_to_db(tmp_path: Path):
    # Use in-memory DB for isolation
    uow_factory = create_unit_of_work_factory("sqlite:///:memory:")

    # Build lightweight runner + reader
    store = InMemoryStatusStore()
    runner = GatlingRunner(store)
    reader = GatlingStatusReader(store)

    # Wire orchestrator with UnitOfWorkFactory (so it can persist execution + metrics)
    orchestrator = PerformanceOrchestrator(runner=runner, status_reader=reader, uow_factory=uow_factory)
    service = PerformanceService(orchestrator)

    # Submit a short run with a full URL so no DB endpoint resolution is needed
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

    # Prepare results directory and write a summary.json mimicking Gatling output
    results_dir = Path("data/perf_runs") / execution_id / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    summary = {
        "parsed": True,
        "path": str(results_dir / "summary.json"),
        "total": 100,
        "ok": 98,
        "ko": 2,
        "mean_rps": 5.0,
        "p95": 850.0,
        "p99": 1200.0,
        "mean_rt": 600.0,
        "min_rt": 100.0,
        "max_rt": 1500.0,
    }
    (results_dir / "summary.json").write_text(json.dumps(summary))

    # Wait briefly for simulated run to complete
    deadline = time.time() + 5
    status = None
    while time.time() < deadline:
        status = service.status(execution_id)
        if status.status in ("succeeded", "failed"):
            break
        time.sleep(0.1)

    # Ensure runner finished
    assert status is not None
    assert status.status in ("succeeded", "failed")

    # Trigger DB-backed read and verify metrics were persisted
    data = service.get_execution(execution_id)
    # Minimal structural checks
    assert data.get("execution_id") == execution_id
    assert data.get("status") in ("succeeded", "failed", "RUNNING", "COMPLETED", "FAILED")
    # Metrics persisted from summary.json
    assert data.get("total_requests") == 100
    assert data.get("successful_requests") == 98
    assert data.get("failed_requests") == 2
    assert data.get("avg_rps") == 5.0
    assert data.get("avg_response_time") == 600.0
    assert data.get("p95_response_time") == 850.0
    assert data.get("p99_response_time") == 1200.0
    assert data.get("min_response_time") == 100.0
    assert data.get("max_response_time") == 1500.0
