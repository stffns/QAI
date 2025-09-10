from __future__ import annotations

"""Gatling runner adapter with lightweight local execution simulation.

This writes a per-run config into data/perf_runs/<execution_id>/config.json
and advances status from queued -> running -> succeeded after a short delay.

It prepares the ground for a real shell/Docker-based Gatling invocation without
changing the public RunnerPort interface.
"""

import json
import os
import threading
import time
import uuid
from pathlib import Path

# Absolute-first imports with fallback to add project root to sys.path
try:
    from src.infrastructure.gatling.status_reader import InMemoryStatusStore
    from src.application.performance.dto import SimulationParams
    from src.application.performance.config_builder import ConfigBuilder
except ImportError:  # pragma: no cover - fallback for direct runs
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
    from src.infrastructure.gatling.status_reader import InMemoryStatusStore  # type: ignore
    from src.application.performance.dto import SimulationParams  # type: ignore
    from src.application.performance.config_builder import ConfigBuilder  # type: ignore


RUNS_BASE = Path("data/perf_runs")


class GatlingRunner:
    def __init__(self, status_store: InMemoryStatusStore):
        self.status_store = status_store
        RUNS_BASE.mkdir(parents=True, exist_ok=True)

    def _persist_config(self, execution_id: str, params: SimulationParams) -> None:
        run_dir = RUNS_BASE / execution_id
        run_dir.mkdir(parents=True, exist_ok=True)

        # Derive resolved URLs from mutated params provided by the orchestrator
        resolved_url = params.endpoint_slug if params.endpoint_slug and params.endpoint_slug.startswith("http") else None
        resolved_scenarios = None
        if params.scenarios:
            resolved_scenarios = [sp.endpoint_slug or "" for sp in params.scenarios]

        cfg = ConfigBuilder.build(params, resolved_url, resolved_scenarios)
        cfg_path = run_dir / "config.json"
        with cfg_path.open("w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)

    def _simulate_execution(self, execution_id: str, params: SimulationParams) -> None:
        # Move to running
        self.status_store.set_status(execution_id, "running")
        # Sleep roughly the intended duration but clamp for dev (~max 10s)
        duration = getattr(params, "duration_sec", 5) or 5
        sleep_time = min(max(int(duration * 0.1), 2), 10)
        time.sleep(sleep_time)
        # Mark as succeeded
        self.status_store.set_status(execution_id, "succeeded")

    def submit(self, params: SimulationParams) -> str:
        execution_id = str(uuid.uuid4())
        self.status_store.mark_queued(execution_id, params)
        try:
            self._persist_config(execution_id, params)
        except Exception:
            # Non-fatal; continue the run even if config write fails
            pass

        t = threading.Thread(target=self._simulate_execution, args=(execution_id, params), daemon=True)
        t.start()
        return execution_id
