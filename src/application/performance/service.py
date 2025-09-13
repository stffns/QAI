from __future__ import annotations

"""Service facade exposing a compact API for agent tools."""

from .dto import RunList, RunStatus, RunSubmitted, SimulationParams
from .orchestrator import PerformanceOrchestrator


class PerformanceService:
    def __init__(self, orchestrator: PerformanceOrchestrator):
        self.orchestrator = orchestrator

    def submit(self, params: SimulationParams) -> RunSubmitted:
        return self.orchestrator.submit(params)

    def status(self, execution_id: str) -> RunStatus:
        return self.orchestrator.status(execution_id)

    def list_recent(self, limit: int = 10) -> RunList:
        items = self.orchestrator.list_recent(limit)
        return RunList(items=items)

    def discover_endpoints(
        self, app_slug: str, environment: str, country_code: str
    ) -> list[dict]:
        return self.orchestrator.discover_endpoints(app_slug, environment, country_code)

    def get_execution(self, execution_id: str) -> dict:
        return self.orchestrator.get_execution(execution_id)
