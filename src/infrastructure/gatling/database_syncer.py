"""
Database Synchronizer for Performance Executions
Syncs InMemoryStatusStore states with database records
"""

from __future__ import annotations

import asyncio
import time
from datetime import datetime
from typing import Optional

try:
    from src.logging_config import get_logger
except ImportError:
    import os
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from src.logging_config import get_logger

try:
    from database.models.performance_test_executions import ExecutionStatus
    from database.repositories.performance_test_executions import (
        PerformanceTestExecutionRepository,
    )
    from database.repositories.unit_of_work import UnitOfWorkFactory
    from src.infrastructure.gatling.status_reader import InMemoryStatusStore
except ImportError:
    import os
    import sys

    sys.path.append(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from database.models.performance_test_executions import ExecutionStatus
    from database.repositories.performance_test_executions import (
        PerformanceTestExecutionRepository,
    )
    from database.repositories.unit_of_work import UnitOfWorkFactory
    from src.infrastructure.gatling.status_reader import InMemoryStatusStore

logger = get_logger("DatabaseStatusSyncer")


class DatabaseStatusSyncer:
    """
    Syncs InMemoryStatusStore states with database records
    Runs as background task to keep database updated
    """

    def __init__(
        self,
        status_store: InMemoryStatusStore,
        uow_factory: UnitOfWorkFactory,
        sync_interval: int = 5,
    ):
        self.status_store = status_store
        self.uow_factory = uow_factory
        self.sync_interval = sync_interval
        self.running = False

    def _map_status_to_db(self, memory_status: str) -> ExecutionStatus:
        """Map InMemoryStatusStore status to database status"""
        status_map = {
            "queued": ExecutionStatus.PENDING,
            "running": ExecutionStatus.RUNNING,
            "succeeded": ExecutionStatus.COMPLETED,
            "failed": ExecutionStatus.FAILED,
            "cancelled": ExecutionStatus.CANCELLED,
        }
        return status_map.get(memory_status, ExecutionStatus.FAILED)

    def sync_once(self) -> dict:
        """
        Perform one sync cycle
        Returns stats about sync operation
        """
        stats = {
            "synced_count": 0,
            "error_count": 0,
            "pending_found": 0,
            "memory_executions": 0,
        }

        try:
            with self.uow_factory.create_scope() as uow:
                exec_repo = uow.get_repository(PerformanceTestExecutionRepository)

                # Get all PENDING executions from database
                pending_executions = exec_repo.find_by_status(ExecutionStatus.PENDING)
                stats["pending_found"] = len(pending_executions)

                # Get all executions from memory store
                memory_statuses = self.status_store._status
                stats["memory_executions"] = len(memory_statuses)

                logger.debug(
                    f"Found {len(pending_executions)} pending DB executions, {len(memory_statuses)} in memory"
                )

                # Sync each pending execution with memory store
                for db_execution in pending_executions:
                    execution_id = db_execution.execution_id

                    if execution_id in memory_statuses:
                        memory_run = memory_statuses[execution_id]
                        new_status = self._map_status_to_db(memory_run.status)

                        # Only update if status changed
                        if new_status != db_execution.status:
                            # Determine end_time for completed executions
                            end_time = None
                            if new_status in [
                                ExecutionStatus.COMPLETED,
                                ExecutionStatus.FAILED,
                                ExecutionStatus.CANCELLED,
                            ]:
                                if not db_execution.end_time:
                                    end_time = (
                                        memory_run.finished_at or datetime.utcnow()
                                    )

                            # Update database using repository method
                            exec_repo.update_status(
                                execution_id=execution_id,
                                status=new_status,
                                updated_by="database_syncer",
                                end_time=end_time,
                            )

                            # Set start_time separately if moving to RUNNING (using update_metrics)
                            if (
                                new_status == ExecutionStatus.RUNNING
                                and not db_execution.start_time
                            ):
                                start_time = memory_run.started_at or datetime.utcnow()
                                exec_repo.update_metrics(
                                    execution_id, {"start_time": start_time}
                                )

                            stats["synced_count"] += 1

                            logger.info(
                                f"Synced execution {execution_id[:8]}... from {db_execution.status} to {new_status}"
                            )
                    else:
                        # Execution not found in memory - check if completed or stuck
                        age_minutes = (
                            datetime.utcnow() - db_execution.created_at
                        ).total_seconds() / 60
                        if age_minutes > 10:  # Consider for processing after 10 minutes
                            # Check if execution actually completed by looking for results
                            completed_status = self._check_execution_completion(
                                execution_id
                            )

                            if completed_status:
                                # Execution completed - update to COMPLETED
                                exec_repo.update_status(
                                    execution_id=execution_id,
                                    status=ExecutionStatus.COMPLETED,
                                    updated_by="database_syncer",
                                    end_time=datetime.utcnow(),
                                )
                                # Try to get and update metrics from results
                                try:
                                    metrics = self._extract_completion_metrics(
                                        execution_id
                                    )
                                    if metrics:
                                        exec_repo.update_metrics(execution_id, metrics)
                                except Exception as e:
                                    logger.warning(
                                        f"Could not extract metrics for {execution_id[:8]}...: {e}"
                                    )

                                stats["synced_count"] += 1
                                logger.info(
                                    f"Marked completed execution {execution_id[:8]}... as COMPLETED after {age_minutes:.1f} minutes"
                                )
                            else:
                                # Execution truly stuck - mark as failed
                                exec_repo.update_status(
                                    execution_id=execution_id,
                                    status=ExecutionStatus.FAILED,
                                    updated_by="database_syncer",
                                    end_time=datetime.utcnow(),
                                )
                                # Add failure note
                                exec_repo.update_metrics(
                                    execution_id,
                                    {
                                        "execution_notes": f"Failed: execution not found in memory store and no results after {age_minutes:.1f} minutes"
                                    },
                                )
                                stats["synced_count"] += 1
                                logger.warning(
                                    f"Marked stuck execution {execution_id[:8]}... as FAILED after {age_minutes:.1f} minutes"
                                )

        except Exception as e:
            logger.error(f"Error during sync: {e}")
            stats["error_count"] += 1

        return stats

    async def start_background_sync(self):
        """Start background sync loop"""
        self.running = True
        logger.info(f"Starting database sync with {self.sync_interval}s interval")

        while self.running:
            try:
                stats = self.sync_once()
                if stats["synced_count"] > 0 or stats["error_count"] > 0:
                    logger.info(
                        f"Sync cycle: {stats['synced_count']} synced, {stats['error_count']} errors, "
                        f"{stats['pending_found']} pending, {stats['memory_executions']} in memory"
                    )

                await asyncio.sleep(self.sync_interval)

            except Exception as e:
                logger.error(f"Error in sync loop: {e}")
                await asyncio.sleep(self.sync_interval)

    def stop_background_sync(self):
        """Stop background sync"""
        self.running = False
        logger.info("Stopping database sync")

    def _check_execution_completion(self, execution_id: str) -> bool:
        """Check if execution has completed by looking for results files"""
        try:
            from pathlib import Path

            # Check for results in the expected location
            results_dir = Path("data/perf_runs") / execution_id / "results"
            summary_file = results_dir / "summary.json"

            if summary_file.exists():
                # Check if summary indicates completion
                import json

                try:
                    summary = json.loads(summary_file.read_text())
                    # Consider it completed if it has parsed data and total requests
                    # Support both 'total_requests' and 'total' keys
                    total = summary.get("total_requests") or summary.get("total", 0)
                    return (
                        summary.get("parsed", False)
                        and isinstance(total, (int, float))
                        and total > 0
                    )
                except (json.JSONDecodeError, KeyError):
                    return False

            return False

        except Exception as e:
            logger.warning(f"Error checking completion for {execution_id[:8]}...: {e}")
            return False

    def _extract_completion_metrics(self, execution_id: str) -> dict:
        """Extract metrics from completed execution results"""
        try:
            import json
            from pathlib import Path

            results_dir = Path("data/perf_runs") / execution_id / "results"
            summary_file = results_dir / "summary.json"

            if not summary_file.exists():
                return {}

            summary = json.loads(summary_file.read_text())

            # Extract metrics from summary - support multiple key formats
            metrics = {}

            # Total requests
            total = summary.get("total_requests") or summary.get("total")
            if total is not None:
                metrics["total_requests"] = int(total)

            # Successful/failed requests
            ok = summary.get("successful_requests") or summary.get("ok")
            if ok is not None:
                metrics["successful_requests"] = int(ok)

            ko = summary.get("failed_requests") or summary.get("ko")
            if ko is not None:
                metrics["failed_requests"] = int(ko)

            # Error rate - calculate if not present
            if summary.get("error_rate") is not None:
                metrics["error_rate"] = (
                    float(summary["error_rate"]) / 100.0
                )  # Convert percentage to ratio
            elif (
                "global_stats" in summary
                and summary["global_stats"].get("error_rate") is not None
            ):
                metrics["error_rate"] = (
                    float(summary["global_stats"]["error_rate"]) / 100.0
                )
            elif total and total > 0:
                error_rate = (ko or 0) / total
                metrics["error_rate"] = float(error_rate)

            # Response times
            if summary.get("avg_response_time") is not None:
                metrics["avg_response_time"] = float(summary["avg_response_time"])
            elif summary.get("mean_rt") is not None:
                metrics["avg_response_time"] = float(summary["mean_rt"])

            if summary.get("p95_response_time") is not None:
                metrics["p95_response_time"] = float(summary["p95_response_time"])
            elif summary.get("p95") is not None:
                metrics["p95_response_time"] = float(summary["p95"])

            if summary.get("p99_response_time") is not None:
                metrics["p99_response_time"] = float(summary["p99_response_time"])
            elif summary.get("p99") is not None:
                metrics["p99_response_time"] = float(summary["p99"])

            if summary.get("min_response_time") is not None:
                metrics["min_response_time"] = float(summary["min_response_time"])
            elif summary.get("min_rt") is not None:
                metrics["min_response_time"] = float(summary["min_rt"])

            if summary.get("max_response_time") is not None:
                metrics["max_response_time"] = float(summary["max_response_time"])
            elif summary.get("max_rt") is not None:
                metrics["max_response_time"] = float(summary["max_rt"])

            # RPS
            if summary.get("rps") is not None:
                metrics["rps"] = float(summary["rps"])
            elif summary.get("mean_rps") is not None:
                metrics["rps"] = float(summary["mean_rps"])

            return metrics

        except Exception as e:
            logger.warning(f"Error extracting metrics for {execution_id[:8]}...: {e}")
            return {}
