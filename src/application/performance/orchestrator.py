from __future__ import annotations

"""Performance Orchestrator coordinating the full run lifecycle."""

from datetime import datetime
from pathlib import Path
from typing import Optional

# Logging import with absolute-first pattern and fallback
try:
    from src.logging_config import get_logger
except ImportError:  # pragma: no cover - fallback for direct module runs
    import os
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from src.logging_config import get_logger  # type: ignore

from .auto_cleanup import PerformanceAutoCleanup
from .config_builder import ConfigBuilder
from .dto import RunStatus, RunSubmitted, ScenarioParams, SimulationParams
from .guardrails import Guardrails
from .ports import RunnerPort, StatusReaderPort

# DB repositories and UoW
try:
    from database.models.performance_test_executions import (
        ExecutionScope,
        ExecutionStatus,
    )
    from database.repositories.application_endpoints_repository import (
        ApplicationEndpointRepository,
    )
    from database.repositories.apps_repository import AppsRepository
    from database.repositories.countries_repository import CountriesRepository
    from database.repositories.environments_repository import EnvironmentsRepository
    from database.repositories.performance_test_executions import (
        PerformanceTestExecutionRepository,
    )
    from database.repositories.unit_of_work import UnitOfWorkFactory
except ImportError:  # pragma: no cover - fallback for direct runs
    import os
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from database.models.performance_test_executions import (  # type: ignore
        ExecutionScope,
        ExecutionStatus,
    )
    from database.repositories.application_endpoints_repository import (
        ApplicationEndpointRepository,  # type: ignore
    )
    from database.repositories.apps_repository import AppsRepository  # type: ignore
    from database.repositories.countries_repository import (
        CountriesRepository,  # type: ignore
    )
    from database.repositories.environments_repository import (
        EnvironmentsRepository,  # type: ignore
    )
    from database.repositories.performance_test_executions import (  # type: ignore
        PerformanceTestExecutionRepository,
    )
    from database.repositories.unit_of_work import UnitOfWorkFactory  # type: ignore

logger = get_logger("PerformanceOrchestrator")


class PerformanceOrchestrator:
    """
    Orchestrates performance test runs:
    - Validates inputs (guardrails)
    - Resolves endpoint URL from DB mappings (placeholder for now)
    - Submits run via RunnerPort
    - Reads status via StatusReaderPort
    """

    def __init__(
        self,
        runner: RunnerPort,
        status_reader: StatusReaderPort,
        uow_factory: UnitOfWorkFactory | None = None,
    ):
        self.runner = runner
        self.status_reader = status_reader
        self.uow_factory = uow_factory
        # Initialize auto-cleanup with same database access
        self.auto_cleanup = PerformanceAutoCleanup(uow_factory)

    # Placeholder: In next step, inject UnitOfWorkFactory to resolve DB mappings
    def _resolve_endpoint_url(self, params: SimulationParams) -> str:
        # Accept direct URL during early phase
        if params.endpoint_slug and params.endpoint_slug.startswith("http"):
            return params.endpoint_slug

        if not self.uow_factory:
            raise ValueError(
                "Endpoint resolution requires database access; please provide a full endpoint_url for now."
            )

        if not params.endpoint_slug:
            raise ValueError(
                "endpoint_slug is required (logical endpoint name) or pass a full endpoint URL"
            )

        endpoint_name = params.endpoint_slug

        with self.uow_factory.create_scope() as uow:
            apps_repo = uow.get_repository(AppsRepository)
            env_repo = uow.get_repository(EnvironmentsRepository)
            c_repo = uow.get_repository(CountriesRepository)
            ep_repo = uow.get_repository(ApplicationEndpointRepository)

            app = apps_repo.get_by_code(params.app_slug)
            if not app:
                raise ValueError(f"Unknown app_slug: {params.app_slug}")
            env = env_repo.get_by_code(params.environment)
            if not env:
                raise ValueError(f"Unknown environment: {params.environment}")
            country = c_repo.get_by_code(params.country_code)
            if not country:
                raise ValueError(f"Unknown country_code: {params.country_code}")

            # Try country-specific endpoint first
            ep = ep_repo.get_by_combination(
                application_id=app.id,  # type: ignore
                environment_id=env.id,  # type: ignore
                country_id=country.id,
                endpoint_name=endpoint_name,
            )
            # Fallback to global endpoint
            if not ep:
                ep = ep_repo.get_by_combination(
                    application_id=app.id,  # type: ignore
                    environment_id=env.id,  # type: ignore
                    country_id=None,
                    endpoint_name=endpoint_name,
                )

            if not ep or not ep.endpoint_url:
                raise ValueError(
                    f"Endpoint not found for name '{endpoint_name}' in app={params.app_slug}, env={params.environment}, country={params.country_code}"
                )

            return ep.endpoint_url

    def _resolve_scenario_urls(self, params: SimulationParams) -> list[str]:
        """Resolve endpoints per scenario when multi-scenario is used.

        Falls back to global params.endpoint_slug/URL when a scenario doesn't specify one.
        """
        urls: list[str] = []
        if not params.scenarios:
            return urls
        for sp in params.scenarios:
            # Prefer scenario-specific endpoint if provided
            candidate = sp.endpoint_slug or params.endpoint_slug
            if candidate and candidate.startswith("http"):
                urls.append(candidate)
                continue
            # If DB is not available, fail fast requiring explicit URL
            if not self.uow_factory:
                raise ValueError(
                    "Endpoint resolution requires database access when endpoint_slug is not a full URL."
                )
            if not candidate:
                raise ValueError(
                    "Each scenario must set endpoint_slug or provide a global endpoint URL in params.endpoint_slug"
                )

            endpoint_name = candidate
            with self.uow_factory.create_scope() as uow:
                apps_repo = uow.get_repository(AppsRepository)
                env_repo = uow.get_repository(EnvironmentsRepository)
                c_repo = uow.get_repository(CountriesRepository)
                ep_repo = uow.get_repository(ApplicationEndpointRepository)

                app = apps_repo.get_by_code(params.app_slug)
                env = env_repo.get_by_code(params.environment)
                country = c_repo.get_by_code(params.country_code)
                if not app or not env or not country:
                    raise ValueError(
                        "Invalid app/environment/country while resolving scenario endpoint"
                    )

                ep = ep_repo.get_by_combination(
                    application_id=app.id,  # type: ignore
                    environment_id=env.id,  # type: ignore
                    country_id=country.id,
                    endpoint_name=endpoint_name,
                )
                if not ep:
                    ep = ep_repo.get_by_combination(
                        application_id=app.id,  # type: ignore
                        environment_id=env.id,  # type: ignore
                        country_id=None,
                        endpoint_name=endpoint_name,
                    )
                if not ep or not ep.endpoint_url:
                    raise ValueError(
                        f"Endpoint not found for scenario '{getattr(sp, 'scenario_slug', None) or endpoint_name}'"
                    )
                urls.append(ep.endpoint_url)
        return urls

    def submit(self, params: SimulationParams) -> RunSubmitted:
        Guardrails.validate(params)

        resolved_url = None
        resolved_scenarios = None
        if params.scenarios:
            resolved_scenarios = self._resolve_scenario_urls(params)
            # Mutate scenarios to carry full URLs so runners don't need DB
            for i, url in enumerate(resolved_scenarios):
                try:
                    if params.scenarios and i < len(params.scenarios):
                        params.scenarios[i].endpoint_slug = url
                except Exception:
                    pass
        else:
            resolved_url = self._resolve_endpoint_url(params)
            try:
                # Mutate single endpoint to be a full URL
                params.endpoint_slug = resolved_url
            except Exception:
                pass
        config = ConfigBuilder.build(params, resolved_url, resolved_scenarios)

        execution_id = self.runner.submit(params)
        logger.info(f"Submitted performance run {execution_id} for {params.app_slug}")

        # Persist execution record (PENDING)
        try:
            if self.uow_factory:
                with self.uow_factory.create_scope() as uow:
                    exec_repo = uow.get_repository(PerformanceTestExecutionRepository)
                    name = f"{params.app_slug}-{params.test_type}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

                    scope_map = {
                        "smoke": ExecutionScope.FUNCTIONAL,
                        "baseline": ExecutionScope.BASELINE,
                        "load": ExecutionScope.LOAD,
                        "stress": ExecutionScope.STRESS,
                    }

                    exec_repo.create(
                        {
                            "test_config_id": None,
                            "execution_id": execution_id,
                            "execution_name": name,
                            "status": ExecutionStatus.PENDING,
                            "execution_environment": params.environment,
                            "execution_scope": scope_map.get(
                                params.test_type, ExecutionScope.FUNCTIONAL
                            ),
                            "test_purpose": params.test_type,
                            "execution_notes": params.notes,
                            "configuration_snapshot": config,
                        }
                    )
        except Exception as e:
            logger.warning(f"Could not persist execution {execution_id}: {e}")

        return RunSubmitted(execution_id=execution_id, params=params)

    def status(self, execution_id: str) -> RunStatus:
        # Blend DB and in-memory status: use the freshest state available
        reader_status: Optional[RunStatus] = None
        db_status: Optional[RunStatus] = None

        if self.uow_factory:
            try:
                with self.uow_factory.create_scope() as uow:
                    exec_repo = uow.get_repository(PerformanceTestExecutionRepository)
                    ex = exec_repo.find_by_execution_id(execution_id)
                    if ex is not None:
                        db_status = self._from_db_execution(ex)
            except Exception:
                db_status = None

        try:
            reader_status = self.status_reader.get_status(execution_id)
        except Exception:
            reader_status = None

        order = {"queued": 0, "running": 1, "succeeded": 2, "failed": 2}

        # Decide best status
        chosen = reader_status or db_status
        if db_status and reader_status:
            if order.get(reader_status.status, 0) >= order.get(db_status.status, 0):
                chosen = reader_status
            else:
                chosen = db_status

        if not chosen:
            # Default minimal
            chosen = RunStatus(execution_id=execution_id, status="queued")

        # Ensure finished_at when terminal
        if chosen.status in {"succeeded", "failed"} and not chosen.finished_at:
            chosen.finished_at = datetime.utcnow()

        # Best-effort DB sync forward
        if (
            self.uow_factory
            and db_status
            and reader_status
            and order.get(reader_status.status, 0) > order.get(db_status.status, 0)
        ):
            try:
                with self.uow_factory.create_scope() as uow:
                    exec_repo = uow.get_repository(PerformanceTestExecutionRepository)
                    status_map = {
                        "queued": ExecutionStatus.PENDING,
                        "running": ExecutionStatus.RUNNING,
                        "succeeded": ExecutionStatus.COMPLETED,
                        "failed": ExecutionStatus.FAILED,
                    }
                    end_time = (
                        datetime.utcnow()
                        if reader_status.status in {"succeeded", "failed"}
                        else None
                    )
                    exec_repo.update_status(
                        execution_id,
                        status_map[reader_status.status],
                        end_time=end_time,
                    )
                    # When terminal, try to parse results summary.json under data/perf_runs/<id>/results
                    if reader_status.status in {"succeeded", "failed"}:
                        try:
                            run_results = (
                                Path("data/perf_runs") / execution_id / "results"
                            )
                            summary_path = run_results / "summary.json"
                            if summary_path.exists():
                                import json

                                summary = json.loads(summary_path.read_text())
                                # Use summary.json data directly - no reparsing needed
                                self._persist_summary_data(
                                    execution_id, summary, run_results, uow
                                )
                        except Exception:
                            pass

                        # Trigger auto-cleanup after successful execution
                        if reader_status.status == "succeeded":
                            try:
                                self.auto_cleanup.post_execution_cleanup()
                                logger.info(
                                    f"🧹 Auto-cleanup completed after successful execution {execution_id}"
                                )
                            except Exception as e:
                                logger.warning(
                                    f"⚠️  Auto-cleanup failed after execution {execution_id}: {e}"
                                )
            except Exception:
                pass

        # Artifact-based completion detection when reader_status is unavailable (e.g., different process)
        # If we have results artifacts, sync DB and reflect in chosen status to prevent stuck 'queued'.
        if self.uow_factory and reader_status is None:
            try:
                run_results = Path("data/perf_runs") / execution_id / "results"
                summary_path = run_results / "summary.json"
                log_path = run_results / "runner.log"
                detected_status: Optional[str] = None
                if summary_path.exists():
                    detected_status = "succeeded"
                elif log_path.exists():
                    try:
                        tail = "\n".join(
                            log_path.read_text(
                                encoding="utf-8", errors="ignore"
                            ).splitlines()[-200:]
                        )
                        if (
                            "BUILD FAILURE" in tail
                            or "[ERROR]" in tail
                            or "Failed to execute goal" in tail
                        ):
                            detected_status = "failed"
                    except Exception:
                        pass
                if detected_status:
                    with self.uow_factory.create_scope() as uow:
                        exec_repo = uow.get_repository(
                            PerformanceTestExecutionRepository
                        )
                        status_map = {
                            "succeeded": ExecutionStatus.COMPLETED,
                            "failed": ExecutionStatus.FAILED,
                        }
                        end_time = datetime.utcnow()
                        try:
                            exec_repo.update_status(
                                execution_id,
                                status_map[detected_status],
                                end_time=end_time,
                            )
                        except Exception:
                            pass
                        if summary_path.exists():
                            try:
                                import json

                                summary = json.loads(summary_path.read_text())
                                # Use summary.json data directly - no reparsing needed
                                self._persist_summary_data(
                                    execution_id, summary, run_results, uow
                                )
                            except Exception:
                                pass
                    # Reflect detection in chosen status
                    if detected_status == "succeeded":
                        chosen = RunStatus(
                            execution_id=execution_id,
                            status="succeeded",
                            finished_at=datetime.utcnow(),
                        )
                        # Trigger auto-cleanup after successful execution detection
                        try:
                            self.auto_cleanup.post_execution_cleanup()
                            logger.info(
                                f"🧹 Auto-cleanup completed after successful execution detection {execution_id}"
                            )
                        except Exception as e:
                            logger.warning(
                                f"⚠️  Auto-cleanup failed after execution detection {execution_id}: {e}"
                            )
                    elif detected_status == "failed":
                        chosen = RunStatus(
                            execution_id=execution_id,
                            status="failed",
                            finished_at=datetime.utcnow(),
                        )
            except Exception:
                pass

        return chosen

    def discover_endpoints(
        self, app_slug: str, environment: str, country_code: str
    ) -> list[dict]:
        if not self.uow_factory:
            return []

        with self.uow_factory.create_scope() as uow:
            apps_repo = uow.get_repository(AppsRepository)
            env_repo = uow.get_repository(EnvironmentsRepository)
            c_repo = uow.get_repository(CountriesRepository)
            ep_repo = uow.get_repository(ApplicationEndpointRepository)

            app = apps_repo.get_by_code(app_slug)
            env = env_repo.get_by_code(environment)
            country = c_repo.get_by_code(country_code)
            if not app or not env or not country:
                return []

            eps = ep_repo.get_endpoints_for_app_env(
                application_id=app.id,  # type: ignore
                environment_id=env.id,  # type: ignore
                country_id=country.id,
                include_global=True,
                active_only=True,
            )

            data: list[dict] = []
            for e in eps:
                data.append(
                    {
                        "name": e.endpoint_name,
                        "url": e.endpoint_url,
                        "method": getattr(e, "http_method", None),
                        "scope": (
                            "country" if getattr(e, "country_id", None) else "global"
                        ),
                    }
                )
            return data

    def get_execution(self, execution_id: str) -> dict:
        """Return DB-backed execution info if available, else empty dict.

        Includes status, timings, basic metrics, and paths persisted by update_metrics.
        """
        if not self.uow_factory:
            return {}
        try:
            with self.uow_factory.create_scope() as uow:
                exec_repo = uow.get_repository(PerformanceTestExecutionRepository)
                ex = exec_repo.find_by_execution_id(execution_id)
                if not ex:
                    return {}

                def v(name):
                    return getattr(ex, name, None)

                def enum_name(val):
                    try:
                        return (
                            val.name
                            if hasattr(val, "name")
                            else (str(val) if val is not None else None)
                        )
                    except Exception:
                        return str(val) if val is not None else None

                start_val = v("start_time")
                end_val = v("end_time")
                start_iso = (
                    start_val.isoformat() if isinstance(start_val, datetime) else None
                )
                end_iso = end_val.isoformat() if isinstance(end_val, datetime) else None
                return {
                    "execution_id": v("execution_id"),
                    "execution_name": v("execution_name"),
                    "status": enum_name(v("status")),
                    "start_time": start_iso,
                    "end_time": end_iso,
                    "duration_seconds": v("duration_seconds"),
                    "total_requests": v("total_requests"),
                    "successful_requests": v("successful_requests"),
                    "failed_requests": v("failed_requests"),
                    "avg_rps": v("avg_rps"),
                    "avg_response_time": v("avg_response_time"),
                    "p95_response_time": v("p95_response_time"),
                    "p99_response_time": v("p99_response_time"),
                    "min_response_time": v("min_response_time"),
                    "max_response_time": v("max_response_time"),
                    "error_rate": v("error_rate"),
                    "gatling_report_path": v("gatling_report_path"),
                    "execution_environment": v("execution_environment"),
                    "execution_scope": enum_name(v("execution_scope")),
                }
        except Exception:
            return {}

    # --- Helpers ---
    def _from_db_execution(self, ex) -> RunStatus:
        db_to_app = {
            "PENDING": "queued",
            "RUNNING": "running",
            "COMPLETED": "succeeded",
            "FAILED": "failed",
            "CANCELLED": "failed",
            "TIMEOUT": "failed",
        }
        status_str = db_to_app.get(str(getattr(ex, "status", "PENDING")), "queued")
        return RunStatus(
            execution_id=ex.execution_id,
            status=status_str,  # type: ignore[arg-type]
            started_at=getattr(ex, "start_time", None),
            finished_at=getattr(ex, "end_time", None),
            summary=None,
        )

    def list_recent(self, limit: int = 10) -> list[RunStatus]:
        if not self.uow_factory:
            return []
        try:
            with self.uow_factory.create_scope() as uow:
                exec_repo = uow.get_repository(PerformanceTestExecutionRepository)
                running = exec_repo.find_by_status(ExecutionStatus.RUNNING)[:limit]
                pending = exec_repo.find_by_status(ExecutionStatus.PENDING)[:limit]
                completed = exec_repo.find_by_status(ExecutionStatus.COMPLETED)[:limit]
                failed = exec_repo.find_by_status(ExecutionStatus.FAILED)[:limit]

                all_items = (
                    list(running) + list(pending) + list(completed) + list(failed)
                )
                # Sort by created_at desc if present
                all_items.sort(
                    key=lambda x: getattr(x, "created_at", datetime.min), reverse=True
                )
                all_items = all_items[:limit]
                return [self._from_db_execution(ex) for ex in all_items]
        except Exception:
            return []

    def _persist_summary_data(
        self, execution_id: str, summary: dict, run_results: Path, uow
    ) -> None:
        """Persist both global execution metrics and endpoint-level results from summary.json.

        Uses the already parsed summary.json data directly - no reparsing needed.
        """
        exec_repo = uow.get_repository(PerformanceTestExecutionRepository)

        # Extract global fields for execution table from summary
        fields = self._extract_global_fields_from_summary(summary, run_results)
        exec_repo.update_metrics(execution_id, fields)

        # Persist endpoint-level results if available
        self._persist_endpoint_results_from_summary(execution_id, summary, uow)

    def _extract_global_fields_from_summary(
        self, summary: dict, run_results: Path
    ) -> dict:
        """Extract global execution fields directly from summary.json data."""
        fields = {}

        # Extract primary metrics directly from summary
        if summary.get("total") is not None:
            fields["total_requests"] = (
                int(summary["total"]) if summary["total"] is not None else 0
            )
        if summary.get("ok") is not None:
            fields["successful_requests"] = (
                int(summary["ok"]) if summary["ok"] is not None else 0
            )
        if summary.get("ko") is not None:
            fields["failed_requests"] = (
                int(summary["ko"]) if summary["ko"] is not None else 0
            )

        # Extract timing metrics from summary
        if summary.get("mean_rps") is not None:
            fields["avg_rps"] = (
                float(summary["mean_rps"]) if summary["mean_rps"] is not None else None
            )
        if summary.get("mean_rt") is not None:
            fields["avg_response_time"] = (
                float(summary["mean_rt"]) if summary["mean_rt"] is not None else None
            )
        if summary.get("p95") is not None:
            fields["p95_response_time"] = (
                float(summary["p95"]) if summary["p95"] is not None else None
            )
        if summary.get("p99") is not None:
            fields["p99_response_time"] = (
                float(summary["p99"]) if summary["p99"] is not None else None
            )
        if summary.get("min_rt") is not None:
            fields["min_response_time"] = (
                float(summary["min_rt"]) if summary["min_rt"] is not None else None
            )
        if summary.get("max_rt") is not None:
            fields["max_response_time"] = (
                float(summary["max_rt"]) if summary["max_rt"] is not None else None
            )

        # Add additional percentiles if available in global_stats
        global_stats = summary.get("global_stats", {})
        if global_stats.get("p50") is not None:
            fields["p50_response_time"] = float(global_stats["p50"])
        if global_stats.get("p75") is not None:
            fields["p75_response_time"] = float(global_stats["p75"])

        # Compute error rate
        try:
            tot = fields.get("total_requests") or 0
            fail = fields.get("failed_requests") or 0
            fields["error_rate"] = (fail / tot) if tot else 0.0
        except Exception:
            pass

        # Add metadata fields
        fields["gatling_report_path"] = str(run_results)
        metadata = summary.get("metadata", {})
        fields["sla_compliance"] = metadata.get("all_passed", False)
        fields["validation_status"] = (
            "passed" if metadata.get("all_passed") else "failed"
        )

        return fields

    def _persist_endpoint_results_from_summary(
        self, execution_id: str, summary: dict, uow
    ) -> None:
        """Persist endpoint-level results directly from summary.json data."""
        try:
            from database.repositories.performance_endpoint_results_repository import (
                PerformanceEndpointResultsRepository,
            )

            endpoints = summary.get("endpoints", [])
            if not endpoints:
                return

            per_repo = uow.get_repository(PerformanceEndpointResultsRepository)

            # Clear previous results to avoid duplicates
            try:
                per_repo.delete_by_execution_id(execution_id)
            except Exception:
                pass

            # Helper function for safe float conversion
            def _flt(v):
                try:
                    if v is None:
                        return None
                    if isinstance(v, (int, float)):
                        return float(v)
                    if isinstance(v, str) and v.strip() != "":
                        return float(v)
                except Exception:
                    return None
                return None

            # Persist each endpoint result
            for item in endpoints:
                name = str(item.get("name") or "request")
                per_repo.create_endpoint_result(
                    execution_id=execution_id,
                    endpoint_name=name,
                    endpoint_url=item.get("url"),  # Enhanced data may include URL
                    http_method=item.get(
                        "method", "GET"
                    ),  # Enhanced data may include method
                    # Use correct field names from summary.json structure
                    total_requests=int(
                        item.get("total_requests") or item.get("total") or 0
                    ),
                    successful_requests=int(
                        item.get("successful_requests") or item.get("ok") or 0
                    ),
                    failed_requests=int(
                        item.get("failed_requests") or item.get("ko") or 0
                    ),
                    p50_response_time=_flt(
                        item.get("p50_response_time") or item.get("p50")
                    ),
                    p75_response_time=_flt(
                        item.get("p75_response_time") or item.get("p75")
                    ),
                    p95_response_time=_flt(
                        item.get("p95_response_time") or item.get("p95")
                    ),
                    p99_response_time=_flt(
                        item.get("p99_response_time") or item.get("p99")
                    ),
                    avg_response_time=_flt(
                        item.get("avg_response_time") or item.get("mean_rt")
                    ),
                    max_response_time=_flt(
                        item.get("max_response_time") or item.get("max_rt")
                    ),
                    min_response_time=_flt(
                        item.get("min_response_time") or item.get("min_rt")
                    ),
                    requests_per_second=_flt(
                        item.get("requests_per_second") or item.get("mean_rps")
                    ),
                )
        except Exception as e:
            # Log endpoint processing error for debugging
            print(
                f"Warning: Failed to persist endpoint results for {execution_id}: {e}"
            )
            # Continue processing rather than failing completely
            pass
