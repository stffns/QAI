from __future__ import annotations

"""Ports (interfaces) for performance infrastructure adapters."""

from typing import Protocol

from .dto import RunStatus, SimulationParams


class RunnerPort(Protocol):
    def submit(self, params: SimulationParams) -> str:
        """Submit a run and return execution_id."""
        ...


class StatusReaderPort(Protocol):
    def get_status(self, execution_id: str) -> RunStatus:
        ...
