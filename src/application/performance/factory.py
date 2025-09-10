from __future__ import annotations

"""Factory to build a PerformanceService with default adapters."""

from .orchestrator import PerformanceOrchestrator
from .service import PerformanceService

# Logging import with absolute-first pattern and fallback
try:
    from src.logging_config import get_logger
except ImportError:  # pragma: no cover - fallback for direct module runs
    import sys, os
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from src.logging_config import get_logger  # type: ignore

import os
from pathlib import Path
from src.infrastructure.gatling.runner import GatlingRunner
from src.infrastructure.gatling.shell_runner import ShellGatlingRunner
from src.infrastructure.gatling.maven_runner import MavenGatlingRunner
from src.infrastructure.gatling.status_reader import GatlingStatusReader, InMemoryStatusStore
from database.repositories.unit_of_work import create_unit_of_work_factory
from config import get_settings
from database.connection import db_manager


logger = get_logger("PerformanceFactory")


def build_default_service() -> PerformanceService:
    store = InMemoryStatusStore()
    # Always use Maven-based Gatling runner
    runner = MavenGatlingRunner(store)
    reader = GatlingStatusReader(store)

    # Try to build a UnitOfWorkFactory using configured DB URL
    uow_factory = None
    try:
        settings = get_settings()
        db_url = settings.database.url
        if db_url:
            # Make sure DB is initialized (idempotent)
            try:
                db_manager.create_db_and_tables()
            except Exception:
                pass
            uow_factory = create_unit_of_work_factory(db_url)
    except Exception as e:
        logger.warning(f"UnitOfWorkFactory not available, proceeding without DB: {e}")

    orchestrator = PerformanceOrchestrator(runner=runner, status_reader=reader, uow_factory=uow_factory)
    return PerformanceService(orchestrator)
