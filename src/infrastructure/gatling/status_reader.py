from __future__ import annotations

"""Status reader adapter with simple in-memory store (temporary)."""

from datetime import datetime
from typing import Dict

try:
    from src.application.performance.dto import RunStatus, SimulationParams
except ImportError:  # pragma: no cover - fallback for direct runs
    import os
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
    from src.application.performance.dto import (  # type: ignore
        RunStatus,
        SimulationParams,
    )


class InMemoryStatusStore:
    def __init__(self):
        self._status: Dict[str, RunStatus] = {}

    def mark_queued(self, execution_id: str, params: SimulationParams) -> None:
        self._status[execution_id] = RunStatus(
            execution_id=execution_id, status="queued"
        )

    def set_status(self, execution_id: str, status: str) -> None:
        rs = self._status.get(execution_id)
        if rs is None:
            rs = RunStatus(execution_id=execution_id)
            self._status[execution_id] = rs
        rs.status = status  # type: ignore
        if status == "running" and not rs.started_at:
            rs.started_at = datetime.utcnow()
        if status in {"succeeded", "failed"} and not rs.finished_at:
            rs.finished_at = datetime.utcnow()


class GatlingStatusReader:
    def __init__(self, store: InMemoryStatusStore):
        self.store = store

    def get_status(self, execution_id: str) -> RunStatus:
        return self.store._status.get(
            execution_id,
            RunStatus(
                execution_id=execution_id, status="failed", summary="unknown execution"
            ),
        )
