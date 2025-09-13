"""
Agent tools: thin wrappers around the new PerformanceService.

These are intentionally minimal. Business logic lives in the application layer.
"""

import json
import time
from pathlib import Path
from typing import Any, List, Optional

from agno.tools import tool


def _serialize_datetimes(data: Any) -> Any:
    """
    Recursively convert datetime objects to ISO strings for JSON serialization.
    """
    if hasattr(data, "isoformat"):  # datetime objects
        return data.isoformat()
    elif isinstance(data, dict):
        return {key: _serialize_datetimes(value) for key, value in data.items()}
    elif isinstance(data, list):
        return [_serialize_datetimes(item) for item in data]
    else:
        return data


# Absolute-first imports with fallback
try:
    from config import get_settings
    from database.models.performance_test_executions import ExecutionStatus
    from database.repositories.performance_test_executions import (
        PerformanceTestExecutionRepository,
    )
    from database.repositories.unit_of_work import create_unit_of_work_factory
    from src.application.performance import PerformanceService, SimulationParams
    from src.application.performance.factory import build_default_service
    from src.infrastructure.gatling.results_parser import (
        parse_gatling_endpoint_results,
        parse_gatling_results,
    )
except ImportError:  # pragma: no cover
    import os
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from config import get_settings  # type: ignore
    from database.models.performance_test_executions import (
        ExecutionStatus,  # type: ignore
    )
    from database.repositories.performance_test_executions import (
        PerformanceTestExecutionRepository,  # type: ignore
    )
    from database.repositories.unit_of_work import (
        create_unit_of_work_factory,  # type: ignore
    )
    from src.application.performance import (  # type: ignore
        PerformanceService,
        SimulationParams,
    )
    from src.application.performance.factory import (
        build_default_service,  # type: ignore
    )
    from src.infrastructure.gatling.results_parser import (  # type: ignore
        parse_gatling_endpoint_results,
        parse_gatling_results,
    )


_service: Optional[PerformanceService] = None


def _get_service() -> PerformanceService:
    global _service
    if _service is None:
        _service = build_default_service()
    return _service


@tool
def perf_submit_run(
    app_slug: str,
    country_code: str,
    environment: str,
    test_type: Optional[str] = None,
    users: Optional[int] = None,
    duration_sec: Optional[int] = None,
    endpoint_url: Optional[str] = None,
    # Advanced single-scenario options
    scenario_slug: Optional[str] = None,
    rps_target: Optional[float] = None,
    feeder_file: Optional[str] = None,
    injection_profile: Optional[List[dict[str, Any]]] = None,
    # Multi-scenario (optional): list of dicts matching ScenarioParams
    scenarios: Optional[List[dict[str, Any]]] = None,
    # Assertions and injection tuning (optional)
    enable_assertions: Optional[bool] = None,
    fail_pct_lt: Optional[float] = None,
    p95_lt: Optional[float] = None,
    p99_lt: Optional[float] = None,
    mean_rt_lt: Optional[float] = None,
    injection: Optional[str] = None,
    ramp_up: Optional[int] = None,
    hold_for: Optional[int] = None,
    ramp_down: Optional[int] = None,
    to_users: Optional[int] = None,
    pause_ms: Optional[int] = None,
) -> str:
    """Submit a performance run. Returns execution id.

    - Supports single-scenario (users/duration/endpoint_url) and multi-scenario via `scenarios`.
    - For multi-scenario, each item can include: scenario_slug, endpoint_slug/url, rps_target, feeder_file, injection_profile.
    """
    # Handle None values with defaults
    test_type = test_type or "smoke"
    users = users or 10
    duration_sec = duration_sec or 60

    service = _get_service()
    # Prepare params; when scenarios provided, we keep single-scenario fields for defaults only
    kw = dict(
        app_slug=app_slug,
        country_code=country_code,
        environment=environment,
        test_type=test_type,  # type: ignore[arg-type]
        users=users,
        duration_sec=duration_sec,
        endpoint_slug=endpoint_url,
        scenario_slug=scenario_slug,
        rps_target=rps_target,
        feeder_file=feeder_file,
        injection_profile=injection_profile,
    )
    # Optional assertions/injection settings
    if enable_assertions is not None:
        kw["enable_assertions"] = enable_assertions
    if fail_pct_lt is not None:
        kw["fail_pct_lt"] = fail_pct_lt
    if p95_lt is not None:
        kw["p95_lt"] = p95_lt
    if p99_lt is not None:
        kw["p99_lt"] = p99_lt
    if mean_rt_lt is not None:
        kw["mean_rt_lt"] = mean_rt_lt
    if injection is not None:
        kw["injection"] = injection
    if ramp_up is not None:
        kw["ramp_up"] = ramp_up
    if hold_for is not None:
        kw["hold_for"] = hold_for
    if ramp_down is not None:
        kw["ramp_down"] = ramp_down
    if to_users is not None:
        kw["to_users"] = to_users
    if pause_ms is not None:
        kw["pause_ms"] = pause_ms
    if scenarios is not None:
        kw["scenarios"] = scenarios  # type: ignore[assignment]

    params = SimulationParams(**kw)  # type: ignore[arg-type]
    submitted = service.submit(params)
    return submitted.execution_id


@tool
def perf_get_status(execution_id: str) -> str:
    """Get the current status for a performance run.

    This function also automatically processes and persists results to database when the test completes.
    Call this periodically to monitor test progress and ensure results are saved.
    """
    service = _get_service()
    st = service.status(execution_id)  # This triggers result processing when complete

    # Add helpful info about result processing
    status_data = st.model_dump()

    # Convert datetime objects to ISO strings for JSON serialization
    status_data = _serialize_datetimes(status_data)

    if st.status in ("succeeded", "failed"):
        status_data["results_note"] = (
            "Results have been automatically processed and saved to database"
        )
        # Try to get execution info to show DB persistence
        try:
            execution_data = service.get_execution(execution_id)
            if execution_data and execution_data.get("total_requests", 0) > 0:
                status_data["db_persistence"] = "confirmed"
                status_data["db_metrics"] = {
                    "total_requests": execution_data.get("total_requests"),
                    "error_rate": execution_data.get("error_rate"),
                    "avg_response_time": execution_data.get("avg_response_time"),
                }
            else:
                status_data["db_persistence"] = "pending"
        except Exception:
            status_data["db_persistence"] = "unknown"
    else:
        status_data["results_note"] = (
            f"Test is {st.status}. Results will be processed when complete."
        )

    return json.dumps(status_data)


@tool
def perf_list_recent(limit: int = 10) -> str:
    """List recent runs (DB-backed when available)."""
    service = _get_service()
    runs = service.list_recent(limit)
    runs_data = _serialize_datetimes(runs.model_dump())
    return json.dumps(runs_data)


@tool
def perf_discover_endpoints(app_slug: str, country_code: str, environment: str) -> str:
    """List available endpoints for app/env/country so the AI can pick one."""
    service = _get_service()
    eps = service.discover_endpoints(app_slug, environment, country_code)
    return json.dumps(eps)


__all__ = [
    "perf_submit_run",
    "perf_get_status",
    "perf_list_recent",
    "perf_discover_endpoints",
    "perf_plan_runs",
    "perf_submit_batch",
    "perf_get_summary",
    "perf_get_execution",
    "perf_run_test",
    "perf_get_metrics",
    "perf_get_prometheus_snapshot",
    "perf_get_prometheus_snapshot_internal",
    "perf_run_smart",
    "perf_process_completed_tests",
]


@tool
def perf_process_completed_results(execution_id: str) -> str:
    """Force processing of results for a completed test execution.

    Use this when a test has finished but results haven't been processed yet.
    This is useful for batch operations where tests run independently.
    """
    service = _get_service()

    try:
        # Force status check to trigger result processing
        status = service.status(execution_id)

        # Get updated execution data
        execution_data = service.get_execution(execution_id)

        return json.dumps(
            {
                "execution_id": execution_id,
                "processing_triggered": True,
                "current_status": status.status,
                "results_processed": execution_data.get("total_requests", 0) > 0,
                "metrics_summary": (
                    {
                        "total_requests": execution_data.get("total_requests"),
                        "error_rate": execution_data.get("error_rate"),
                        "avg_response_time": execution_data.get("avg_response_time"),
                        "gatling_report_path": execution_data.get(
                            "gatling_report_path"
                        ),
                    }
                    if execution_data
                    else None
                ),
            }
        )

    except Exception as e:
        return json.dumps(
            {
                "execution_id": execution_id,
                "processing_triggered": False,
                "error": str(e),
            }
        )


@tool
def perf_plan_runs(
    apps: List[str],
    countries: List[str],
    environments: List[str],
    endpoint_filter: Optional[str] = None,
    test_type: Optional[str] = None,
    users: Optional[int] = None,
    duration_sec: Optional[int] = None,
    per_endpoint_rps: Optional[dict[str, float]] = None,
) -> str:
    """Plan multi-scenario runs across apps/countries/environments.

    Returns a JSON list of SimulationParams-like dicts ready for perf_submit_batch.
    - endpoint_filter: if provided, only include endpoints whose name contains this substring (case-insensitive).
    - per_endpoint_rps: optional mapping {endpoint_name: rps_target}.
    """
    # Handle None values with defaults
    test_type = test_type or "smoke"
    users = users or 10
    duration_sec = duration_sec or 60

    service = _get_service()
    plan: List[dict[str, Any]] = []
    needle = (endpoint_filter or "").lower()

    for app in apps:
        for env in environments:
            for country in countries:
                eps = service.discover_endpoints(app, env, country)
                if needle:
                    eps = [e for e in eps if needle in (e.get("name") or "").lower()]
                if not eps:
                    continue

                scenarios: List[dict[str, Any]] = []
                for e in eps:
                    name = str(e.get("name") or e.get("url") or "")
                    scenarios.append(
                        {
                            "scenario_slug": name,
                            "endpoint_slug": name,  # resolved via DB later; or if full URL, used as-is
                            "rps_target": (
                                (per_endpoint_rps or {}).get(name)
                                if (per_endpoint_rps and name)
                                else None
                            ),
                        }
                    )

                plan.append(
                    {
                        "app_slug": app,
                        "country_code": country,
                        "environment": env,
                        "test_type": test_type,
                        "users": users,
                        "duration_sec": duration_sec,
                        "scenarios": scenarios,
                    }
                )

    return json.dumps(plan)


@tool
def perf_submit_batch(plan_json: str, max_concurrent: int = 3) -> str:
    """Submit a batch of planned runs.

    - plan_json: JSON from perf_plan_runs (list of SimulationParams-like dicts).
    - max_concurrent: limit parallel submissions.
    Returns a JSON array of {index, execution_id}.
    """
    import concurrent.futures as cf

    service = _get_service()
    try:
        plan_items = json.loads(plan_json)
    except Exception as e:
        return json.dumps({"error": f"invalid plan_json: {e}"})

    results: List[dict[str, Any]] = []

    def _submit_one(idx: int, item: dict[str, Any]) -> dict[str, Any]:
        try:
            params = SimulationParams(**item)  # type: ignore[arg-type]
            submitted = service.submit(params)
            return {"index": idx, "execution_id": submitted.execution_id}
        except Exception as e:
            return {"index": idx, "error": str(e)}

    with cf.ThreadPoolExecutor(max_workers=max(1, int(max_concurrent))) as ex:
        futs = [
            ex.submit(_submit_one, idx, item) for idx, item in enumerate(plan_items)
        ]
        for f in cf.as_completed(futs):
            results.append(f.result())

    # Preserve input order
    results.sort(key=lambda x: x.get("index", 0))
    return json.dumps(results)


@tool
def perf_get_summary(execution_id: str) -> str:
    """Return parsed summary for a run if available.

    Looks for data/perf_runs/<id>/results/summary.json; if missing, tries to parse results dir on-demand.
    """
    base = Path("data/perf_runs") / execution_id / "results"
    try:
        summary_path = base / "summary.json"
        if summary_path.exists():
            return summary_path.read_text()
        # Try on-demand parse (best-effort)
        summary = parse_gatling_results(base)
        return json.dumps(summary)
    except Exception as e:
        return json.dumps({"parsed": False, "error": str(e), "path": str(base)})


@tool
def perf_get_execution(execution_id: str) -> str:
    """Return DB-backed execution info (status, metrics) if available."""
    service = _get_service()
    data = service.get_execution(execution_id)
    return json.dumps(data)


@tool
def perf_run_test(
    app_slug: str,
    country_code: str,
    environment: str,
    test_type: Optional[str] = None,
    users: Optional[int] = None,
    duration_sec: Optional[int] = None,
    endpoint_url: Optional[str] = None,
    # Advanced single-scenario options
    scenario_slug: Optional[str] = None,
    rps_target: Optional[float] = None,
    feeder_file: Optional[str] = None,
    injection_profile: Optional[List[dict[str, Any]]] = None,
    # Multi-scenario (optional)
    scenarios: Optional[List[dict[str, Any]]] = None,
    # Assertions and injection tuning (optional)
    enable_assertions: Optional[bool] = None,
    fail_pct_lt: Optional[float] = None,
    p95_lt: Optional[float] = None,
    p99_lt: Optional[float] = None,
    mean_rt_lt: Optional[float] = None,
    injection: Optional[str] = None,
    ramp_up: Optional[int] = None,
    hold_for: Optional[int] = None,
    ramp_down: Optional[int] = None,
    to_users: Optional[int] = None,
    pause_ms: Optional[int] = None,
    # Wait controls
    wait_timeout_sec: int = 600,
    poll_interval_sec: float = 2.0,
) -> str:
    """Run a performance test end-to-end via the agent.

    Submits a run, waits until completion or timeout, then returns:
    { execution_id, final_status, summary, execution }
    """
    # Handle None values with defaults
    test_type = test_type or "smoke"
    users = users or 10
    duration_sec = duration_sec or 60

    service = _get_service()
    # Build params similar to perf_submit_run
    kw = dict(
        app_slug=app_slug,
        country_code=country_code,
        environment=environment,
        test_type=test_type,  # type: ignore[arg-type]
        users=users,
        duration_sec=duration_sec,
        endpoint_slug=endpoint_url,
        scenario_slug=scenario_slug,
        rps_target=rps_target,
        feeder_file=feeder_file,
        injection_profile=injection_profile,
    )
    if enable_assertions is not None:
        kw["enable_assertions"] = enable_assertions
    if fail_pct_lt is not None:
        kw["fail_pct_lt"] = fail_pct_lt
    if p95_lt is not None:
        kw["p95_lt"] = p95_lt
    if p99_lt is not None:
        kw["p99_lt"] = p99_lt
    if mean_rt_lt is not None:
        kw["mean_rt_lt"] = mean_rt_lt
    if injection is not None:
        kw["injection"] = injection
    if ramp_up is not None:
        kw["ramp_up"] = ramp_up
    if hold_for is not None:
        kw["hold_for"] = hold_for
    if ramp_down is not None:
        kw["ramp_down"] = ramp_down
    if to_users is not None:
        kw["to_users"] = to_users
    if pause_ms is not None:
        kw["pause_ms"] = pause_ms
    if scenarios is not None:
        kw["scenarios"] = scenarios  # type: ignore[assignment]

    params = SimulationParams(**kw)  # type: ignore[arg-type]
    submitted = service.submit(params)
    execution_id = submitted.execution_id

    # Wait for completion
    deadline = time.time() + max(1, int(wait_timeout_sec))
    status = None
    while time.time() < deadline:
        status = service.status(execution_id)
        if status.status in ("succeeded", "failed"):
            break
        time.sleep(max(0.1, float(poll_interval_sec)))

    final_status = status.status if status else "unknown"

    # Collect summary and DB execution info
    try:
        base = Path("data/perf_runs") / execution_id / "results"
        summary_path = base / "summary.json"
        if summary_path.exists():
            summary = json.loads(summary_path.read_text())
        else:
            summary = parse_gatling_results(base)
    except Exception as e:
        summary = {"parsed": False, "error": str(e)}

    execution = service.get_execution(execution_id)
    return json.dumps(
        {
            "execution_id": execution_id,
            "final_status": final_status,
            "summary": summary,
            "execution": execution,
        }
    )


def perf_run_test_internal(
    app_slug: str,
    country_code: str,
    environment: str,
    test_type: str = "smoke",
    users: int = 10,
    duration_sec: int = 60,
    endpoint_url: Optional[str] = None,
    scenario_slug: Optional[str] = None,
    rps_target: Optional[float] = None,
    feeder_file: Optional[str] = None,
    injection_profile: Optional[List[dict[str, Any]]] = None,
    scenarios: Optional[List[dict[str, Any]]] = None,
    enable_assertions: Optional[bool] = None,
    fail_pct_lt: Optional[float] = None,
    p95_lt: Optional[float] = None,
    p99_lt: Optional[float] = None,
    mean_rt_lt: Optional[float] = None,
    injection: Optional[str] = None,
    ramp_up: Optional[int] = None,
    hold_for: Optional[int] = None,
    ramp_down: Optional[int] = None,
    to_users: Optional[int] = None,
    pause_ms: Optional[int] = None,
    wait_timeout_sec: int = 600,
    poll_interval_sec: float = 2.0,
) -> dict:
    """Internal helper: same as perf_run_test but returns a Python dict, not JSON.

    Intended for tests to bypass the @tool decorator wrapper.
    """
    service = _get_service()
    kw = dict(
        app_slug=app_slug,
        country_code=country_code,
        environment=environment,
        test_type=test_type,  # type: ignore[arg-type]
        users=users,
        duration_sec=duration_sec,
        endpoint_slug=endpoint_url,
        scenario_slug=scenario_slug,
        rps_target=rps_target,
        feeder_file=feeder_file,
        injection_profile=injection_profile,
    )
    if enable_assertions is not None:
        kw["enable_assertions"] = enable_assertions
    if fail_pct_lt is not None:
        kw["fail_pct_lt"] = fail_pct_lt
    if p95_lt is not None:
        kw["p95_lt"] = p95_lt
    if p99_lt is not None:
        kw["p99_lt"] = p99_lt
    if mean_rt_lt is not None:
        kw["mean_rt_lt"] = mean_rt_lt
    if injection is not None:
        kw["injection"] = injection
    if ramp_up is not None:
        kw["ramp_up"] = ramp_up
    if hold_for is not None:
        kw["hold_for"] = hold_for
    if ramp_down is not None:
        kw["ramp_down"] = ramp_down
    if to_users is not None:
        kw["to_users"] = to_users
    if pause_ms is not None:
        kw["pause_ms"] = pause_ms
    if scenarios is not None:
        kw["scenarios"] = scenarios  # type: ignore[assignment]

    params = SimulationParams(**kw)  # type: ignore[arg-type]
    submitted = service.submit(params)
    execution_id = submitted.execution_id

    deadline = time.time() + max(1, int(wait_timeout_sec))
    status = None
    while time.time() < deadline:
        status = service.status(execution_id)
        if status.status in ("succeeded", "failed"):
            break
        time.sleep(max(0.1, float(poll_interval_sec)))
    final_status = status.status if status else "unknown"

    try:
        base = Path("data/perf_runs") / execution_id / "results"
        summary_path = base / "summary.json"
        if summary_path.exists():
            summary = json.loads(summary_path.read_text())
        else:
            summary = parse_gatling_results(base)
    except Exception as e:
        summary = {"parsed": False, "error": str(e)}

    execution = service.get_execution(execution_id)
    return {
        "execution_id": execution_id,
        "final_status": final_status,
        "summary": summary,
        "execution": execution,
    }


@tool
def perf_get_metrics() -> str:
    """Return a non-blocking monitoring snapshot and Prometheus endpoint.

    Output: {
      counts: {PENDING, RUNNING, COMPLETED, FAILED},
      recent: [ {execution_id, status, start_time, end_time}... ],
      prometheus: { metrics_url }
    }
    """
    # Aggregated counts via DB (similar to exporter)
    try:
        settings = get_settings()
        db_url = settings.database.url
        if not db_url:
            raise RuntimeError("database url not configured")
        uow_factory = create_unit_of_work_factory(db_url)
        with uow_factory.create_scope() as uow:
            repo = uow.get_repository(PerformanceTestExecutionRepository)
            pending = len(repo.find_by_status(ExecutionStatus.PENDING))
            running = len(repo.find_by_status(ExecutionStatus.RUNNING))
            completed = len(repo.find_by_status(ExecutionStatus.COMPLETED))
            failed = len(repo.find_by_status(ExecutionStatus.FAILED))

        # Also include a small recent list via the service facade
        service = _get_service()
        recent = [
            {
                "execution_id": r.execution_id,
                "status": r.status,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            }
            for r in service.list_recent(10).items
        ]

        return json.dumps(
            {
                "counts": {
                    "PENDING": pending,
                    "RUNNING": running,
                    "COMPLETED": completed,
                    "FAILED": failed,
                },
                "recent": recent,
                "prometheus": {"metrics_url": "http://localhost:9400/metrics"},
            }
        )
    except Exception as e:
        return json.dumps(
            {
                "error": str(e),
                "prometheus": {"metrics_url": "http://localhost:9400/metrics"},
            }
        )


def perf_get_metrics_internal() -> dict:
    """Internal helper: same as perf_get_metrics but returns a Python dict.

    Useful for tests without going through the @tool decorator.
    """
    try:
        settings = get_settings()
        db_url = settings.database.url
        if not db_url:
            raise RuntimeError("database url not configured")
        uow_factory = create_unit_of_work_factory(db_url)
        with uow_factory.create_scope() as uow:
            repo = uow.get_repository(PerformanceTestExecutionRepository)
            pending = len(repo.find_by_status(ExecutionStatus.PENDING))
            running = len(repo.find_by_status(ExecutionStatus.RUNNING))
            completed = len(repo.find_by_status(ExecutionStatus.COMPLETED))
            failed = len(repo.find_by_status(ExecutionStatus.FAILED))

        service = _get_service()
        recent = [
            {
                "execution_id": r.execution_id,
                "status": r.status,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            }
            for r in service.list_recent(10).items
        ]

        return {
            "counts": {
                "PENDING": pending,
                "RUNNING": running,
                "COMPLETED": completed,
                "FAILED": failed,
            },
            "recent": recent,
            "prometheus": {"metrics_url": "http://localhost:9400/metrics"},
        }
    except Exception as e:
        return {
            "error": str(e),
            "prometheus": {"metrics_url": "http://localhost:9400/metrics"},
        }


@tool
def perf_get_prometheus_snapshot(url: str = "http://localhost:9400/metrics") -> str:
    """Fetch and summarize Prometheus metrics from the exporter.

    Returns a compact JSON with totals and currents for perf executions.
    """
    import re
    import urllib.request

    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return json.dumps({"error": f"failed to fetch {url}: {e}"})

    def parse_lines(lines):
        counters = {}
        gauges = {}
        for ln in lines:
            if ln.startswith("#"):
                continue
            if ln.startswith("qa_perf_executions_total{"):
                m = re.match(
                    r'^qa_perf_executions_total\{status="([A-Z]+)"\}\s+([0-9eE\.+-]+)',
                    ln,
                )
                if m:
                    counters[m.group(1)] = float(m.group(2))
            elif ln.startswith("qa_perf_executions_current{"):
                m = re.match(
                    r'^qa_perf_executions_current\{status="([A-Z]+)"\}\s+([0-9eE\.+-]+)',
                    ln,
                )
                if m:
                    gauges[m.group(1)] = float(m.group(2))
        return counters, gauges

    counters, gauges = parse_lines(body.splitlines())
    return json.dumps(
        {
            "source": url,
            "executions_total": counters,
            "executions_current": gauges,
        }
    )


def perf_get_prometheus_snapshot_internal(
    url: str = "http://localhost:9400/metrics",
) -> dict:
    """Internal helper: same as perf_get_prometheus_snapshot but returns a dict.

    Useful for tests or direct Python calls without the @tool decorator.
    """
    import re
    import urllib.request

    try:
        with urllib.request.urlopen(url, timeout=5) as resp:
            body = resp.read().decode("utf-8", errors="ignore")
    except Exception as e:
        return {"error": f"failed to fetch {url}: {e}"}

    counters = {}
    gauges = {}
    for ln in body.splitlines():
        if ln.startswith("#"):
            continue
        if ln.startswith("qa_perf_executions_total{"):
            m = re.match(
                r'^qa_perf_executions_total\{status="([A-Z]+)"\}\s+([0-9eE\.+-]+)', ln
            )
            if m:
                counters[m.group(1)] = float(m.group(2))
        elif ln.startswith("qa_perf_executions_current{"):
            m = re.match(
                r'^qa_perf_executions_current\{status="([A-Z]+)"\}\s+([0-9eE\.+-]+)', ln
            )
            if m:
                gauges[m.group(1)] = float(m.group(2))
    return {"source": url, "executions_total": counters, "executions_current": gauges}


@tool
def perf_run_smart(
    app_slug: str,
    country_code: str,
    environment: str,
    test_type: Optional[str] = None,
    users: Optional[int] = None,
    duration_sec: Optional[int] = None,
    endpoint_url: Optional[str] = None,
    # Advanced options
    scenario_slug: Optional[str] = None,
    rps_target: Optional[float] = None,
    feeder_file: Optional[str] = None,
    injection_profile: Optional[List[dict[str, Any]]] = None,
    # Assertions and injection tuning (optional)
    enable_assertions: Optional[bool] = None,
    fail_pct_lt: Optional[float] = None,
    p95_lt: Optional[float] = None,
    p99_lt: Optional[float] = None,
    mean_rt_lt: Optional[float] = None,
    injection: Optional[str] = None,
    ramp_up: Optional[int] = None,
    hold_for: Optional[int] = None,
    ramp_down: Optional[int] = None,
    to_users: Optional[int] = None,
    pause_ms: Optional[int] = None,
) -> str:
    """Smart performance test execution.

    If endpoint_url is specified: runs a single endpoint test.
    If endpoint_url is NOT specified: runs ALL available endpoints in a multi-scenario test.

    Returns execution id for single endpoint, or JSON with multiple execution results for multi-scenario.
    """
    # Handle None values with defaults
    test_type = test_type or "smoke"
    users = users or 10
    duration_sec = duration_sec or 60

    service = _get_service()

    if endpoint_url:
        # Single endpoint mode - use existing logic
        kw = dict(
            app_slug=app_slug,
            country_code=country_code,
            environment=environment,
            test_type=test_type,
            users=users,
            duration_sec=duration_sec,
            endpoint_slug=endpoint_url,
            scenario_slug=scenario_slug,
            rps_target=rps_target,
            feeder_file=feeder_file,
            injection_profile=injection_profile,
        )

        # Add optional parameters
        if enable_assertions is not None:
            kw["enable_assertions"] = enable_assertions
        if fail_pct_lt is not None:
            kw["fail_pct_lt"] = fail_pct_lt
        if p95_lt is not None:
            kw["p95_lt"] = p95_lt
        if p99_lt is not None:
            kw["p99_lt"] = p99_lt
        if mean_rt_lt is not None:
            kw["mean_rt_lt"] = mean_rt_lt
        if injection is not None:
            kw["injection"] = injection
        if ramp_up is not None:
            kw["ramp_up"] = ramp_up
        if hold_for is not None:
            kw["hold_for"] = hold_for
        if ramp_down is not None:
            kw["ramp_down"] = ramp_down
        if to_users is not None:
            kw["to_users"] = to_users
        if pause_ms is not None:
            kw["pause_ms"] = pause_ms

        params = SimulationParams(**kw)  # type: ignore[arg-type]
        submitted = service.submit(params)
        execution_id = submitted.execution_id

        # Return immediately with execution info - don't wait
        return json.dumps(
            {
                "mode": "single-endpoint",
                "execution_id": execution_id,
                "status": "submitted",
                "endpoint": endpoint_url,
                "test_config": {
                    "app": app_slug,
                    "country": country_code,
                    "environment": environment,
                    "users": users,
                    "duration_sec": duration_sec,
                    "test_type": test_type,
                },
                "monitoring": {
                    "prometheus_metrics": "http://localhost:9400/metrics",
                    "check_status": f"perf_get_status('{execution_id}')",
                    "note": "Results will be processed automatically when test completes. Use status check to trigger processing.",
                },
            }
        )

    else:
        # Multi-scenario mode - discover all endpoints and run them all
        try:
            endpoints = service.discover_endpoints(app_slug, environment, country_code)
            if not endpoints:
                return f"No endpoints found for {app_slug}/{environment}/{country_code}"

            # Create scenarios for all discovered endpoints
            scenarios = []
            for ep in endpoints:
                name = str(ep.get("name") or ep.get("url") or "")
                scenarios.append(
                    {
                        "scenario_slug": name,
                        "endpoint_slug": name,
                        "rps_target": rps_target,  # Apply same RPS to all if specified
                    }
                )

            # Build multi-scenario params
            kw = dict(
                app_slug=app_slug,
                country_code=country_code,
                environment=environment,
                test_type=test_type,
                users=users,
                duration_sec=duration_sec,
                scenarios=scenarios,
            )

            # Add optional parameters
            if enable_assertions is not None:
                kw["enable_assertions"] = enable_assertions
            if fail_pct_lt is not None:
                kw["fail_pct_lt"] = fail_pct_lt
            if p95_lt is not None:
                kw["p95_lt"] = p95_lt
            if p99_lt is not None:
                kw["p99_lt"] = p99_lt
            if mean_rt_lt is not None:
                kw["mean_rt_lt"] = mean_rt_lt
            if injection is not None:
                kw["injection"] = injection
            if ramp_up is not None:
                kw["ramp_up"] = ramp_up
            if hold_for is not None:
                kw["hold_for"] = hold_for
            if ramp_down is not None:
                kw["ramp_down"] = ramp_down
            if to_users is not None:
                kw["to_users"] = to_users
            if pause_ms is not None:
                kw["pause_ms"] = pause_ms

            params = SimulationParams(**kw)  # type: ignore[arg-type]
            submitted = service.submit(params)
            execution_id = submitted.execution_id

            # Return immediately with execution info - don't wait
            endpoint_names = [ep.get("name", "Unknown") for ep in endpoints]
            return json.dumps(
                {
                    "mode": "multi-scenario",
                    "execution_id": execution_id,
                    "status": "submitted",
                    "endpoints_tested": endpoint_names,
                    "total_endpoints": len(endpoints),
                    "test_config": {
                        "app": app_slug,
                        "country": country_code,
                        "environment": environment,
                        "users": users,
                        "duration_sec": duration_sec,
                        "test_type": test_type,
                    },
                    "monitoring": {
                        "prometheus_metrics": "http://localhost:9400/metrics",
                        "check_status": f"perf_get_status('{execution_id}')",
                        "note": "Multi-scenario test results will be processed automatically when complete.",
                    },
                }
            )

        except Exception as e:
            return f"Error in multi-scenario execution: {str(e)}"


@tool
def perf_process_completed_tests(limit: int = 10) -> str:
    """Process and persist results for recently completed tests that may not have been processed yet.

    This is useful for batch processing when tests complete while the agent is not monitoring them.
    Uses Prometheus metrics to identify which tests need processing.

    Args:
        limit: Maximum number of tests to process

    Returns:
        JSON with processing results
    """
    service = _get_service()

    try:
        # Get recent completed/failed executions from database
        settings = get_settings()
        if not settings.database.url:
            return json.dumps({"error": "Database not configured"})

        uow_factory = create_unit_of_work_factory(settings.database.url)

        with uow_factory.create_scope() as uow:
            exec_repo = uow.get_repository(PerformanceTestExecutionRepository)

            # Find executions that might need processing
            # Look for RUNNING status executions that might have completed
            running_executions = exec_repo.find_by_status(ExecutionStatus.RUNNING)
            completed_executions = exec_repo.find_by_status(ExecutionStatus.COMPLETED)
            failed_executions = exec_repo.find_by_status(ExecutionStatus.FAILED)

            # Process up to 'limit' executions
            to_process = running_executions[:limit]

            processed = []
            for execution in to_process:
                try:
                    # Call status to trigger result processing
                    status = service.status(execution.execution_id)
                    processed.append(
                        {
                            "execution_id": execution.execution_id,
                            "old_status": "RUNNING",
                            "new_status": status.status,
                            "processed": True,
                        }
                    )
                except Exception as e:
                    processed.append(
                        {
                            "execution_id": execution.execution_id,
                            "processed": False,
                            "error": str(e),
                        }
                    )

            return json.dumps(
                {
                    "status": "success",
                    "summary": {
                        "running_found": len(running_executions),
                        "completed_found": len(completed_executions),
                        "failed_found": len(failed_executions),
                        "processed_count": len(
                            [p for p in processed if p.get("processed")]
                        ),
                    },
                    "processed_executions": processed,
                    "prometheus_metrics": "http://localhost:9400/metrics",
                }
            )

    except Exception as e:
        return json.dumps(
            {
                "status": "error",
                "message": str(e),
                "suggestion": "Check database connection and Prometheus status",
            }
        )
