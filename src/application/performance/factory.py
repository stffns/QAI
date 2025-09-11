from __future__ import annotations

"""Factory to build a PerformanceService with default adapters."""

import asyncio
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
from src.infrastructure.gatling.database_syncer import DatabaseStatusSyncer
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
            
            # Start database syncer as a separate service
            if uow_factory:
                _start_database_syncer(store, uow_factory)
            
    except Exception as e:
        logger.warning(f"UnitOfWorkFactory not available, proceeding without DB: {e}")

    orchestrator = PerformanceOrchestrator(runner=runner, status_reader=reader, uow_factory=uow_factory)
    return PerformanceService(orchestrator)


def _start_database_syncer(store: InMemoryStatusStore, uow_factory):
    """Start database syncer as background task"""
    try:
        database_syncer = DatabaseStatusSyncer(store, uow_factory, sync_interval=5)
        # Start background sync in a separate thread since we don't have an event loop
        import threading
        import asyncio
        
        def run_syncer():
            """Run the syncer in a new event loop"""
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(database_syncer.start_background_sync())
            except Exception as e:
                logger.error(f"Database syncer error: {e}")
            finally:
                loop.close()
        
        sync_thread = threading.Thread(target=run_syncer, daemon=True)
        sync_thread.start()
        logger.info("✅ Database syncer started in background thread for performance executions")
    except Exception as e:
        logger.warning(f"Could not start database syncer: {e}")
