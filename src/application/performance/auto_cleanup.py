#!/usr/bin/env python3
"""
Auto-cleanup functionality for performance test orchestrator.
Integrates with the performance test workflow to maintain clean perf_runs directory.
"""

import shutil
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

# Database imports
try:
    from sqlmodel import select

    from database.models.performance_test_executions import PerformanceTestExecution
    from database.repositories.performance_test_executions import (
        PerformanceTestExecutionRepository,
    )
    from database.repositories.unit_of_work import UnitOfWorkFactory
except ImportError:  # pragma: no cover - fallback for direct runs
    import os
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from sqlmodel import select  # type: ignore

    from database.models.performance_test_executions import (
        PerformanceTestExecution,  # type: ignore
    )
    from database.repositories.performance_test_executions import (
        PerformanceTestExecutionRepository,  # type: ignore
    )
    from database.repositories.unit_of_work import UnitOfWorkFactory  # type: ignore

logger = get_logger("PerformanceAutoCleanup")


class PerformanceAutoCleanup:
    """
    Automatic cleanup for performance test runs.
    Integrates with orchestrator to maintain clean workspace.
    """

    def __init__(self, uow_factory: Optional[UnitOfWorkFactory] = None):
        self.uow_factory = uow_factory
        self.perf_runs_dir = Path("data/perf_runs")
        self.archive_dir = Path("data/perf_archive")

        # Ensure directories exist
        self.perf_runs_dir.mkdir(parents=True, exist_ok=True)
        self.archive_dir.mkdir(parents=True, exist_ok=True)

    def post_execution_cleanup(self, keep_recent: Optional[int] = None) -> None:
        """
        Clean up after a successful performance test execution.

        Args:
            keep_recent: Number of recent executions to keep in perf_runs.
                        If None, uses configuration default.
        """
        try:
            # Get configuration or use default
            if keep_recent is None:
                try:
                    import yaml

                    config_path = Path("agent_config.yaml")
                    if config_path.exists():
                        with open(config_path) as f:
                            config = yaml.safe_load(f)
                        keep_recent = (
                            config.get("performance", {})
                            .get("auto_cleanup", {})
                            .get("keep_recent", 1)
                        )
                    else:
                        keep_recent = 1
                except Exception:
                    keep_recent = 1

            # Ensure keep_recent is an int
            try:
                keep_recent = int(keep_recent) if keep_recent is not None else 1
            except (ValueError, TypeError):
                logger.warning(
                    f"⚠️  Invalid value for 'keep_recent' in configuration: {keep_recent!r}. Using default value 1."
                )
                keep_recent = 1

            # Check if auto-cleanup is enabled
            try:
                import yaml

                config_path = Path("agent_config.yaml")
                if config_path.exists():
                    with open(config_path) as f:
                        config = yaml.safe_load(f)
                    if (
                        not config.get("performance", {})
                        .get("auto_cleanup", {})
                        .get("enabled", True)
                    ):
                        logger.info("🔕 Auto-cleanup is disabled in configuration")
                        return
            except Exception:
                # If config can't be loaded, proceed with cleanup (fail-safe)
                pass

            logger.info(
                f"🧹 Starting post-execution cleanup (keeping {keep_recent} recent)"
            )

            # Get all execution directories sorted by modification time
            execution_dirs = []
            if self.perf_runs_dir.exists():
                for item in self.perf_runs_dir.iterdir():
                    if item.is_dir() and len(item.name) >= 32:  # UUID-like directory
                        execution_dirs.append((item, item.stat().st_mtime))

            # Sort by modification time (newest first)
            execution_dirs.sort(key=lambda x: x[1], reverse=True)

            # Keep the most recent ones, archive the rest
            archived_count = 0
            for i, (exec_dir, _) in enumerate(execution_dirs):
                if i >= keep_recent:  # Archive older executions
                    if self._archive_execution(exec_dir):
                        archived_count += 1

            logger.info(
                f"📦 Post-execution cleanup completed: {archived_count} executions archived"
            )

        except Exception as e:
            logger.warning(f"⚠️  Post-execution cleanup encountered an issue: {e}")
            # Don't fail the performance test if cleanup has issues

    def pre_execution_cleanup(self, keep_recent: Optional[int] = None) -> None:
        """
        Alias for post_execution_cleanup for backward compatibility.

        Args:
            keep_recent: Number of recent executions to keep in perf_runs.
        """
        logger.warning(
            "🔄 pre_execution_cleanup is deprecated, use post_execution_cleanup"
        )
        self.post_execution_cleanup(keep_recent)

    def _archive_execution(self, exec_dir: Path) -> bool:
        """
        Archive a single execution directory.

        Args:
            exec_dir: Path to execution directory

        Returns:
            True if archived successfully, False otherwise
        """
        try:
            execution_id = exec_dir.name

            # Verify data is safely persisted in database before archiving
            if not self._verify_data_persistence(execution_id):
                logger.warning(f"⚠️  Keeping {execution_id} - data not verified in DB")
                return False

            # Archive the execution
            archive_path = self.archive_dir / execution_id
            if archive_path.exists():
                shutil.rmtree(archive_path)  # Remove old archive if exists

            shutil.move(str(exec_dir), str(archive_path))
            logger.info(f"📦 Archived: {execution_id}")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to archive {exec_dir.name}: {e}")
            return False

    def _verify_data_persistence(self, execution_id: str) -> bool:
        """
        Verify that execution data is safely persisted in database.

        Args:
            execution_id: The execution ID to verify

        Returns:
            True if data is verified as persisted, False otherwise
        """
        if not self.uow_factory:
            # Without database access, be conservative and keep data
            return False

        try:
            with self.uow_factory.create_scope() as uow:
                exec_repo = uow.get_repository(PerformanceTestExecutionRepository)
                execution = exec_repo.find_by_execution_id(execution_id)

                # Verify execution exists and has meaningful data
                if execution is None:
                    return False

                # More permissive check - just verify the execution record exists
                # Even failed tests or tests with 0 requests are valid DB records
                return execution.status is not None

        except Exception as e:
            logger.warning(
                f"⚠️  Could not verify data persistence for {execution_id}: {e}"
            )
            return False

    def cleanup_old_archives(self, retention_days: int = 7) -> None:
        """
        Clean up old archived executions beyond retention period.

        Args:
            retention_days: Number of days to retain archived data
        """
        try:
            if not self.archive_dir.exists():
                return

            cutoff_time = datetime.now().timestamp() - (retention_days * 24 * 60 * 60)
            deleted_count = 0

            for item in self.archive_dir.iterdir():
                if item.is_dir() and item.stat().st_mtime < cutoff_time:
                    try:
                        shutil.rmtree(item)
                        deleted_count += 1
                        logger.info(f"🗑️  Deleted old archive: {item.name}")
                    except Exception as e:
                        logger.warning(
                            f"⚠️  Could not delete old archive {item.name}: {e}"
                        )

            if deleted_count > 0:
                logger.info(
                    f"🗑️  Cleaned {deleted_count} old archives (>{retention_days} days)"
                )

        except Exception as e:
            logger.warning(f"⚠️  Archive cleanup encountered an issue: {e}")
