from __future__ import annotations

"""Shell/Docker Gatling runner.

Environment variables:
- GATLING_CMD: a shell command template with placeholders {SIM_CLASS} {RUN_DIR} {CONFIG} {RESULTS_DIR}
  Example: "$GATLING_HOME/bin/gatling.sh -s {SIM_CLASS} -rf {RESULTS_DIR} -Dqai.config={CONFIG}"
- GATLING_DOCKER_IMAGE: if set, runs docker with the given image.
- GATLING_SIMULATION_CLASS: default "com.qai.GenericHttpSimulation"

This runner expects that the Gatling simulation can read a JSON config at {CONFIG}.
"""

import json
import os
import shlex
import subprocess
import threading
import time
import uuid
from pathlib import Path
from typing import Dict, Optional

try:
    from src.application.performance.config_builder import ConfigBuilder
    from src.application.performance.dto import SimulationParams
    from src.infrastructure.gatling.results_parser import (
        create_enhanced_summary,
        parse_gatling_results,
    )
    from src.infrastructure.gatling.status_reader import InMemoryStatusStore
except ImportError:  # pragma: no cover
    import sys

    sys.path.append(str(Path(__file__).resolve().parents[2]))
    from src.application.performance.config_builder import ConfigBuilder  # type: ignore
    from src.application.performance.dto import SimulationParams  # type: ignore
    from src.infrastructure.gatling.results_parser import (  # type: ignore
        create_enhanced_summary,
        parse_gatling_results,
    )
    from src.infrastructure.gatling.status_reader import (
        InMemoryStatusStore,  # type: ignore
    )


RUNS_BASE = Path("data/perf_runs")


class ShellGatlingRunner:
    def __init__(
        self, status_store: InMemoryStatusStore, env: Optional[Dict[str, str]] = None
    ):
        self.status_store = status_store
        self.env = {**os.environ, **(env or {})}
        self._metrics = None  # lazy-init prometheus metrics
        RUNS_BASE.mkdir(parents=True, exist_ok=True)

    def _init_metrics(self) -> None:
        if self._metrics is not None:
            return
        try:  # pragma: no cover
            from prometheus_client import Counter, Histogram

            started = Counter(
                "qa_perf_runs_started_total",
                "Runs started by runner",
                labelnames=("runner",),
            )
            finished = Counter(
                "qa_perf_runs_finished_total",
                "Runs finished by status",
                labelnames=("runner", "status"),
            )
            duration = Histogram(
                "qa_perf_run_duration_seconds",
                "Run duration seconds",
                labelnames=("runner",),
            )
            self._metrics = (started, finished, duration)
        except Exception:
            self._metrics = ()

    def _persist_config(self, execution_id: str, params: SimulationParams) -> Path:
        run_dir = RUNS_BASE / execution_id
        run_dir.mkdir(parents=True, exist_ok=True)
        results_dir = run_dir / "results"
        results_dir.mkdir(exist_ok=True)

        resolved_url = (
            params.endpoint_slug
            if params.endpoint_slug and params.endpoint_slug.startswith("http")
            else None
        )
        resolved_scenarios = [
            sp.endpoint_slug or "" for sp in (params.scenarios or [])
        ] or None

        cfg = ConfigBuilder.build(params, resolved_url, resolved_scenarios)
        cfg_path = run_dir / "config.json"
        with cfg_path.open("w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
        return cfg_path

    def _build_command(
        self, execution_id: str, cfg_path: Path
    ) -> tuple[list[str], Path]:
        sim_class = self.env.get(
            "GATLING_SIMULATION_CLASS", "com.qai.GenericHttpSimulation"
        )
        run_dir = cfg_path.parent
        results_dir = run_dir / "results"

        docker_image = self.env.get("GATLING_DOCKER_IMAGE")
        cmd_tmpl = self.env.get(
            "GATLING_CMD",
            None,
        )

        if docker_image:
            # Mount run dir as /work; use default gatling entrypoint
            # User should build an image with the desired simulation class present
            inner_cfg = "/work/config.json"
            return (
                [
                    "docker",
                    "run",
                    "--rm",
                    "-v",
                    f"{str(run_dir)}:/work",
                    "-w",
                    "/work",
                    docker_image,
                    "sh",
                    "-lc",
                    f"bin/gatling.sh -s {shlex.quote(sim_class)} -rf {shlex.quote(str(results_dir))} -Dqai.config={shlex.quote(inner_cfg)}",
                ],
                results_dir,
            )

        if not cmd_tmpl:
            raise RuntimeError(
                "GATLING_CMD or GATLING_DOCKER_IMAGE must be set to run Gatling."
            )

        cmd_str = cmd_tmpl.format(
            SIM_CLASS=sim_class,
            RUN_DIR=str(run_dir),
            CONFIG=str(cfg_path),
            RESULTS_DIR=str(results_dir),
        )
        # Use shell for templated string; caller controls safety
        return (["sh", "-lc", cmd_str], results_dir)

    def _run_process(self, execution_id: str, cmd: list[str], cwd: Path) -> None:
        results_dir = cwd / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        log_path = results_dir / "runner.log"
        self.status_store.set_status(execution_id, "running")
        try:
            self._init_metrics()
            start_t = time.monotonic()
            try:
                if self._metrics:
                    self._metrics[0].labels(runner="shell").inc()  # type: ignore[index]
            except Exception:
                pass
            with log_path.open("w", encoding="utf-8") as logf:
                proc = subprocess.Popen(
                    cmd,
                    cwd=str(cwd),
                    env=self.env,
                    stdout=logf,
                    stderr=subprocess.STDOUT,
                )
                rc = proc.wait()
            # Attempt to parse results regardless of rc to aid debugging
            try:
                # Use enhanced summary for better data extraction
                enhanced_summary = create_enhanced_summary(results_dir)
                summary_to_write = (
                    enhanced_summary
                    if enhanced_summary.get("parsed")
                    else parse_gatling_results(results_dir)
                )
                (results_dir / "summary.json").write_text(
                    json.dumps(summary_to_write, indent=2)
                )
            except Exception:
                # best-effort only
                pass

            if rc == 0:
                self.status_store.set_status(execution_id, "succeeded")
                try:
                    if self._metrics:
                        self._metrics[1].labels(runner="shell", status="succeeded").inc()  # type: ignore[index]
                except Exception:
                    pass
            else:
                self.status_store.set_status(execution_id, "failed")
                try:
                    if self._metrics:
                        self._metrics[1].labels(runner="shell", status="failed").inc()  # type: ignore[index]
                except Exception:
                    pass
        except Exception:
            self.status_store.set_status(execution_id, "failed")
            try:
                if self._metrics:
                    self._metrics[1].labels(runner="shell", status="error").inc()  # type: ignore[index]
            except Exception:
                pass
        finally:
            try:
                if self._metrics:
                    duration = max(0.0, time.monotonic() - start_t)
                    self._metrics[2].labels(runner="shell").observe(duration)  # type: ignore[index]
            except Exception:
                pass

    def submit(self, params: SimulationParams) -> str:
        execution_id = str(uuid.uuid4())
        self.status_store.mark_queued(execution_id, params)

        cfg_path = self._persist_config(execution_id, params)
        cmd, results_dir = self._build_command(execution_id, cfg_path)

        t = threading.Thread(
            target=self._run_process,
            args=(execution_id, cmd, cfg_path.parent),
            daemon=True,
        )
        t.start()
        return execution_id
