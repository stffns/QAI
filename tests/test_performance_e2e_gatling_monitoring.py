"""E2E: Ensure Gatling runs start and monitoring reflects progress/completion.

This test forces the lightweight GatlingRunner (no Maven) by monkeypatching
the agent tools' service builder, then:
 - Submits and waits for a run via perf_run_test
 - Verifies DB-backed monitoring snapshot via perf_get_metrics
 - Updates Prometheus metrics using exporter.collect_metrics and asserts gauges
"""

from __future__ import annotations

import json
from typing import Any, Dict


def _build_lightweight_service():
    """Construct a PerformanceService wired to the lightweight runner.

    Uses the same UnitOfWorkFactory as production if available to allow DB-backed
    status persistence and metrics aggregation.
    """
    from src.application.performance.service import PerformanceService
    from src.application.performance.orchestrator import PerformanceOrchestrator
    from src.infrastructure.gatling.runner import GatlingRunner
    from src.infrastructure.gatling.status_reader import GatlingStatusReader, InMemoryStatusStore
    from database.connection import db_manager
    from config import get_settings
    from database.repositories.unit_of_work import create_unit_of_work_factory

    # Ensure DB exists; tests can use the configured sqlite URL
    try:
        db_manager.create_db_and_tables()
    except Exception:
        pass

    uow_factory = None
    try:
        settings = get_settings()
        if settings.database.url:
            uow_factory = create_unit_of_work_factory(settings.database.url)
    except Exception:
        uow_factory = None

    store = InMemoryStatusStore()
    runner = GatlingRunner(store)
    reader = GatlingStatusReader(store)
    orchestrator = PerformanceOrchestrator(runner=runner, status_reader=reader, uow_factory=uow_factory)
    return PerformanceService(orchestrator)


def test_e2e_gatling_runs_and_monitoring(monkeypatch):
    # Patch agent tools to use lightweight service and reset cached singleton
    import src.agent.tools.perf_tools as perf_tools

    monkeypatch.setattr(perf_tools, "build_default_service", _build_lightweight_service)
    monkeypatch.setattr(perf_tools, "_service", None, raising=False)

    # Submit and wait for completion via internal helper (bypass @tool wrapper)
    result = perf_tools.perf_run_test_internal(
        app_slug="demo-app",
        country_code="AR",
        environment="dev",
        test_type="smoke",
        users=2,
        duration_sec=5,
        endpoint_url="http://localhost:8080/ping",
        wait_timeout_sec=30,
        poll_interval_sec=0.2,
    )

    assert result.get("execution_id"), f"Unexpected result: {result}"
    assert result.get("final_status") in ("succeeded", "failed"), f"Final status missing: {result}"

    # Basic expectation: lightweight runner succeeds
    assert result["final_status"] == "succeeded"

    # Verify DB-backed snapshot monitoring tool
    metrics = perf_tools.perf_get_metrics_internal()
    assert "counts" in metrics, f"No counts in metrics: {metrics}"
    counts = metrics["counts"]
    # At least one completed execution should be recorded
    assert counts.get("COMPLETED", 0) >= 1 or counts.get("FAILED", 0) >= 1

    # Recent list should contain our execution id in some terminal state
    recent = metrics.get("recent", [])
    assert any(r.get("execution_id") == result["execution_id"] for r in recent), f"Run not found in recent: {recent}"

    # Update Prometheus metrics directly and assert gauge/counter presence
    # We avoid starting the long-running exporter loop; instead we call collect_metrics
    from src.observability import prometheus_exporter as exporter
    from config import get_settings
    from database.repositories.unit_of_work import create_unit_of_work_factory
    from prometheus_client import generate_latest

    settings = get_settings()
    uow_factory = create_unit_of_work_factory(settings.database.url) if settings.database.url else None
    assert uow_factory is not None, "UoW factory missing; database URL not configured"

    exporter.collect_metrics(uow_factory)
    payload = generate_latest(exporter.REGISTRY).decode("utf-8")
    # Ensure core metric names exist
    assert "qa_perf_executions_current" in payload
    assert "qa_perf_executions_total" in payload
    # Ensure we have at least one current metric line for COMPLETED or FAILED or RUNNING/PENDING
    assert any(lbl in payload for lbl in ("status=\"COMPLETED\"", "status=\"FAILED\"", "status=\"RUNNING\"", "status=\"PENDING\""))
