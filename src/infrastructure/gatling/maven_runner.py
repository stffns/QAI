from __future__ import annotations

"""Maven-based Gatling runner that executes the project in tools/gatling.

Maps SimulationParams/config to the example.UniversalSimulation system properties.
Supports a lightweight echo mode for smoke testing with GATLING_MAVEN_ECHO=1.
"""

import os
import json
import time
import shlex
import subprocess
import threading
import uuid
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

try:
    from src.application.performance.dto import SimulationParams
    from src.infrastructure.gatling.status_reader import InMemoryStatusStore
    from src.infrastructure.gatling.results_parser import parse_gatling_results, create_enhanced_summary
except ImportError:  # pragma: no cover
    import sys
    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.application.performance.dto import SimulationParams  # type: ignore
    from src.infrastructure.gatling.status_reader import InMemoryStatusStore  # type: ignore
    from src.infrastructure.gatling.results_parser import parse_gatling_results, create_enhanced_summary  # type: ignore


RUNS_BASE = Path("data/perf_runs")
GATLING_PROJECT_DIR = Path("tools/gatling")


class MavenGatlingRunner:
    def __init__(self, status_store: InMemoryStatusStore, env: Optional[dict[str, str]] = None):
        self.status_store = status_store
        self.env = {**os.environ, **(env or {})}
        self._metrics = None  # lazy-init prometheus metrics
        RUNS_BASE.mkdir(parents=True, exist_ok=True)

    def _init_metrics(self) -> None:
        if self._metrics is not None:
            return
        try:  # pragma: no cover
            from prometheus_client import Counter, Histogram
            started = Counter("qa_perf_runs_started_total", "Runs started by runner", labelnames=("runner",))
            finished = Counter("qa_perf_runs_finished_total", "Runs finished by status", labelnames=("runner", "status"))
            duration = Histogram("qa_perf_run_duration_seconds", "Run duration seconds", labelnames=("runner",))
            self._metrics = (started, finished, duration)
        except Exception:
            self._metrics = ()

    def _build_cmd(self, params: SimulationParams, run_dir: Path) -> list[str]:
        # Use first scenario; also build optional endpoints chain
        endpoint_url = params.endpoint_slug or ""
        endpoints_chain: list[str] = []
        if params.scenarios and len(params.scenarios) > 0:
            endpoint_url = params.scenarios[0].endpoint_slug or endpoint_url or ""
            # Build a list of endpoint paths to chain, if >1 scenarios provided
            for sp in params.scenarios:
                ep = getattr(sp, "endpoint_slug", None) or ""
                if ep.startswith("http"):
                    parsed_ep = urlparse(ep)
                    path = parsed_ep.path + (f"?{parsed_ep.query}" if parsed_ep.query else "")
                else:
                    path = ep if ep.startswith("/") else f"/{ep}"
                if path:
                    endpoints_chain.append(path)

        parsed = urlparse(endpoint_url) if endpoint_url.startswith("http") else None
        base_url = f"{parsed.scheme}://{parsed.netloc}" if parsed else self.env.get("GATLING_BASEURL", "http://localhost")
        endpoint_path = (parsed.path + (f"?{parsed.query}" if parsed and parsed.query else "")) if parsed else "/"

        vu = max(1, int(getattr(params, "users", 1)))
        duration = max(1, int(getattr(params, "duration_sec", 60)))
        rps = 0.0
        if params.scenarios and len(params.scenarios) > 0 and getattr(params.scenarios[0], "rps_target", None):
            rps = float(params.scenarios[0].rps_target)  # type: ignore[arg-type]
        elif getattr(params, "rps_target", None):
            rps = float(params.rps_target)  # type: ignore[arg-type]

        feeder_type = "none"
        feeder_file = None
        if params.scenarios and len(params.scenarios) > 0 and getattr(params.scenarios[0], "feeder_file", None):
            feeder_type = "csv"
            feeder_file = params.scenarios[0].feeder_file
        elif getattr(params, "feeder_file", None):
            feeder_type = "csv"
            feeder_file = params.feeder_file

        # Prepare -D properties
        props = {
            "gatling.simulationClass": "example.UniversalSimulation",
            "baseUrl": base_url,
            "endpoint": endpoint_path,
            "vu": str(vu),
            "duration": str(duration),
            "rps": str(rps),
            "feederType": feeder_type,
        }
        # Optional: pass endpoints chain
        if len(endpoints_chain) > 1:
            props["endpoints"] = ",".join(endpoints_chain)
        if feeder_file:
            # Resolve to absolute or keep relative path
            props["csvFile"] = str(feeder_file)

        # Optional assertions via SimulationParams or environment variables
        if getattr(params, "enable_assertions", None) is not None:
            props["enableAssertions"] = str(bool(params.enable_assertions))
        elif self.env.get("GATLING_ENABLE_ASSERTIONS") is not None:
            props["enableAssertions"] = str(self.env.get("GATLING_ENABLE_ASSERTIONS"))

        if getattr(params, "fail_pct_lt", None) is not None:
            props["failPctLt"] = str(params.fail_pct_lt)
        elif self.env.get("GATLING_FAIL_PCT_LT"):
            props["failPctLt"] = str(self.env.get("GATLING_FAIL_PCT_LT"))

        if getattr(params, "p95_lt", None) is not None:
            props["p95Lt"] = str(params.p95_lt)
        elif self.env.get("GATLING_P95_LT"):
            props["p95Lt"] = str(self.env.get("GATLING_P95_LT"))

        if getattr(params, "p99_lt", None) is not None:
            props["p99Lt"] = str(params.p99_lt)
        elif self.env.get("GATLING_P99_LT"):
            props["p99Lt"] = str(self.env.get("GATLING_P99_LT"))

        if getattr(params, "mean_rt_lt", None) is not None:
            props["meanRtLt"] = str(params.mean_rt_lt)
        elif self.env.get("GATLING_MEAN_RT_LT"):
            props["meanRtLt"] = str(self.env.get("GATLING_MEAN_RT_LT"))

        # Optional injection profile via SimulationParams or environment variables
        if getattr(params, "injection", None):
            props["injection"] = str(params.injection)
        elif self.env.get("GATLING_INJECTION"):
            props["injection"] = str(self.env.get("GATLING_INJECTION"))

        if getattr(params, "ramp_up", None) is not None:
            props["rampUp"] = str(params.ramp_up)
        elif self.env.get("GATLING_RAMP_UP"):
            props["rampUp"] = str(self.env.get("GATLING_RAMP_UP"))

        if getattr(params, "hold_for", None) is not None:
            props["holdFor"] = str(params.hold_for)
        elif self.env.get("GATLING_HOLD_FOR"):
            props["holdFor"] = str(self.env.get("GATLING_HOLD_FOR"))

        if getattr(params, "ramp_down", None) is not None:
            props["rampDown"] = str(params.ramp_down)
        elif self.env.get("GATLING_RAMP_DOWN"):
            props["rampDown"] = str(self.env.get("GATLING_RAMP_DOWN"))

        if getattr(params, "to_users", None) is not None:
            props["toUsers"] = str(params.to_users)
        elif self.env.get("GATLING_TO_USERS"):
            props["toUsers"] = str(self.env.get("GATLING_TO_USERS"))

        if getattr(params, "pause_ms", None) is not None:
            props["pauseMs"] = str(params.pause_ms)
        elif self.env.get("GATLING_PAUSE_MS"):
            props["pauseMs"] = str(self.env.get("GATLING_PAUSE_MS"))

        # Assemble mvn command
        mvnw = "./mvnw" if os.name != "nt" else "mvnw.cmd"
        cmd = [mvnw, "-q"]
        for k, v in props.items():
            cmd.append(f"-D{k}={v}")
        cmd += ["gatling:test"]

        # Echo mode for smoke tests
        if self.env.get("GATLING_MAVEN_ECHO"):
            cmd = ["sh", "-lc", " ".join(shlex.quote(c) for c in cmd)]

        return cmd

    def _run_process(self, execution_id: str, cmd: list[str], cwd: Path) -> None:
        log_dir = RUNS_BASE / execution_id / "results"
        log_dir.mkdir(parents=True, exist_ok=True)
        log_path = log_dir / "runner.log"
        self.status_store.set_status(execution_id, "running")
        start_t = time.monotonic()
        try:
            self._init_metrics()
            try:
                if self._metrics:
                    self._metrics[0].labels(runner="maven").inc()  # type: ignore[index]
            except Exception:
                pass
            with log_path.open("w", encoding="utf-8") as logf:
                proc = subprocess.Popen(cmd, cwd=str(cwd), env=self.env, stdout=logf, stderr=subprocess.STDOUT)
                rc = proc.wait()
            # Try to parse and persist a summary for downstream consumers
            try:
                # Prefer parsing from the Maven target/gatling latest report directory
                report_root = GATLING_PROJECT_DIR / "target" / "gatling"
                parsed_summary = None
                enhanced_summary = None
                if report_root.exists():
                    try:
                        latest_dir = None
                        latest_mtime = 0.0
                        for p in report_root.iterdir():
                            if p.is_dir():
                                mt = p.stat().st_mtime
                                if mt > latest_mtime:
                                    latest_mtime = mt
                                    latest_dir = p
                        if latest_dir is not None:
                            # Use enhanced summary for better data extraction
                            enhanced_summary = create_enhanced_summary(latest_dir)
                            parsed_summary = parse_gatling_results(latest_dir)  # Keep for backward compatibility
                            # Also write a small pointer for convenience
                            (log_dir / "report_path.txt").write_text(str(latest_dir))
                    except Exception:
                        parsed_summary = None
                        enhanced_summary = None
                
                # Fallback to our run results dir (rarely used for Maven) or when parsing failed
                if not enhanced_summary or not enhanced_summary.get("parsed"):
                    if not parsed_summary or not parsed_summary.get("parsed"):
                        parsed_summary = parse_gatling_results(log_dir)
                    enhanced_summary = create_enhanced_summary(log_dir)
                
                # Write enhanced summary (with fallback to basic summary if enhanced fails)
                summary_to_write = enhanced_summary if enhanced_summary and enhanced_summary.get("parsed") else parsed_summary
                (log_dir / "summary.json").write_text(json.dumps(summary_to_write, indent=2))
            except Exception:
                pass
            if rc == 0:
                self.status_store.set_status(execution_id, "succeeded")
                try:
                    if self._metrics:
                        self._metrics[1].labels(runner="maven", status="succeeded").inc()  # type: ignore[index]
                except Exception:
                    pass
            else:
                self.status_store.set_status(execution_id, "failed")
                try:
                    if self._metrics:
                        self._metrics[1].labels(runner="maven", status="failed").inc()  # type: ignore[index]
                except Exception:
                    pass
        except Exception:
            self.status_store.set_status(execution_id, "failed")
            try:
                if self._metrics:
                    self._metrics[1].labels(runner="maven", status="error").inc()  # type: ignore[index]
            except Exception:
                pass
        finally:
            try:
                if self._metrics:
                    duration = max(0.0, time.monotonic() - start_t)
                    self._metrics[2].labels(runner="maven").observe(duration)  # type: ignore[index]
            except Exception:
                pass

    def submit(self, params: SimulationParams) -> str:
        execution_id = str(uuid.uuid4())
        self.status_store.mark_queued(execution_id, params)

        # Build command and run in tools/gatling
        run_dir = RUNS_BASE / execution_id
        run_dir.mkdir(parents=True, exist_ok=True)
        cmd = self._build_cmd(params, run_dir)

        # If project folder missing, fail fast
        if not GATLING_PROJECT_DIR.joinpath("pom.xml").exists():
            self.status_store.set_status(execution_id, "failed")
            return execution_id

        t = threading.Thread(target=self._run_process, args=(execution_id, cmd, GATLING_PROJECT_DIR), daemon=True)
        t.start()
        return execution_id
