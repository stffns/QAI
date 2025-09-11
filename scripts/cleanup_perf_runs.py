#!/usr/bin/env python3
"""
Performance Runs Cleanup Script

Strategy:
1. Keep only the most recent execution in perf_runs/ for easy access
2. Move older executions to perf_archive/ with 7-day retention
3. Verify data persistence in database before cleanup
4. Clean up Gatling target directory (HTML reports)
"""

import os
import shutil
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Tuple

# Add project root to path for imports
sys.path.append(str(Path(__file__).parent.parent))

try:
    from database.connection import db_manager
    from sqlmodel import Session, select
    from database.models.performance_test_executions import PerformanceTestExecution
    from database.models.performance_endpoint_results import PerformanceEndpointResults
except ImportError as e:
    print(f"❌ Error importing database modules: {e}")
    sys.exit(1)


class PerformanceCleanupManager:
    """Manages cleanup of performance test artifacts with data preservation."""
    
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.perf_runs_dir = Path("data/perf_runs")
        self.archive_dir = Path("data/perf_archive")
        self.gatling_target = Path("tools/gatling/target")
        
        # Ensure archive directory exists
        self.archive_dir.mkdir(parents=True, exist_ok=True)
        
    def get_execution_directories(self) -> List[Tuple[str, datetime]]:
        """Get list of execution directories with their creation timestamps."""
        if not self.perf_runs_dir.exists():
            return []
            
        dirs = []
        for item in self.perf_runs_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                # Get creation time from directory
                creation_time = datetime.fromtimestamp(item.stat().st_ctime)
                dirs.append((item.name, creation_time))
        
        # Sort by creation time (newest first)
        dirs.sort(key=lambda x: x[1], reverse=True)
        return dirs
    
    def verify_data_persistence(self, execution_id: str) -> bool:
        """Verify that execution data is properly persisted in database."""
        try:
            with Session(db_manager.engine) as session:
                # Check execution exists
                execution = session.exec(
                    select(PerformanceTestExecution).where(
                        PerformanceTestExecution.execution_id == execution_id
                    )
                ).first()
                
                if not execution:
                    return False
                
                # More permissive check - just verify execution exists with status
                # Even failed tests (total_requests=0) should be archived if they're in DB
                has_execution_record = execution.status is not None
                
                return has_execution_record
                
        except Exception as e:
            print(f"⚠️  Error verifying persistence for {execution_id}: {e}")
            return False
    
    def move_to_archive(self, execution_id: str) -> bool:
        """Move execution directory to archive."""
        source = self.perf_runs_dir / execution_id
        target = self.archive_dir / execution_id
        
        if not source.exists():
            return False
            
        try:
            if self.dry_run:
                print(f"[DRY RUN] Would move: {source} → {target}")
                return True
            else:
                shutil.move(str(source), str(target))
                print(f"📦 Archived: {execution_id}")
                return True
        except Exception as e:
            print(f"❌ Failed to archive {execution_id}: {e}")
            return False
    
    def cleanup_old_archives(self, retention_days: int = 7) -> int:
        """Remove archived executions older than retention_days."""
        if not self.archive_dir.exists():
            return 0
            
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        removed_count = 0
        
        for item in self.archive_dir.iterdir():
            if item.is_dir():
                # Check creation time
                creation_time = datetime.fromtimestamp(item.stat().st_ctime)
                if creation_time < cutoff_date:
                    # Double-check persistence before final deletion
                    if self.verify_data_persistence(item.name):
                        try:
                            if self.dry_run:
                                print(f"[DRY RUN] Would delete: {item}")
                            else:
                                shutil.rmtree(item)
                                print(f"🗑️  Deleted old archive: {item.name}")
                            removed_count += 1
                        except Exception as e:
                            print(f"❌ Failed to delete {item.name}: {e}")
                    else:
                        print(f"⚠️  Keeping {item.name} - data not verified in DB")
        
        return removed_count
    
    def cleanup_gatling_reports(self, keep_latest: int = 1) -> int:
        """Clean up Gatling HTML reports, keeping only the latest N."""
        if not self.gatling_target.exists():
            return 0
            
        gatling_dir = self.gatling_target / "gatling"
        if not gatling_dir.exists():
            return 0
        
        # Get all gatling report directories
        report_dirs = []
        for item in gatling_dir.iterdir():
            if item.is_dir() and item.name.startswith('universalsimulation-'):
                creation_time = datetime.fromtimestamp(item.stat().st_ctime)
                report_dirs.append((item, creation_time))
        
        # Sort by creation time (newest first)
        report_dirs.sort(key=lambda x: x[1], reverse=True)
        
        # Remove all except the latest keep_latest
        removed_count = 0
        for report_dir, _ in report_dirs[keep_latest:]:
            try:
                if self.dry_run:
                    print(f"[DRY RUN] Would delete Gatling report: {report_dir}")
                else:
                    shutil.rmtree(report_dir)
                    print(f"🗑️  Deleted Gatling report: {report_dir.name}")
                removed_count += 1
            except Exception as e:
                print(f"❌ Failed to delete Gatling report {report_dir.name}: {e}")
        
        return removed_count
    
    def run_cleanup(self, keep_recent_count: int = 1, retention_days: int = 7) -> dict:
        """Run complete cleanup process."""
        results = {
            'archived': 0,
            'deleted_archives': 0,
            'deleted_reports': 0,
            'kept_recent': 0,
            'errors': []
        }
        
        print(f"🧹 Starting Performance Cleanup {'(DRY RUN)' if self.dry_run else ''}")
        print(f"📋 Strategy: Keep {keep_recent_count} recent, archive others, {retention_days}-day retention")
        print()
        
        # Get all execution directories
        execution_dirs = self.get_execution_directories()
        
        if not execution_dirs:
            print("📂 No execution directories found")
            return results
        
        print(f"📊 Found {len(execution_dirs)} execution directories")
        
        # Keep the most recent N executions
        recent_executions = execution_dirs[:keep_recent_count]
        archive_candidates = execution_dirs[keep_recent_count:]
        
        # Report what we're keeping
        print(f"✅ Keeping {len(recent_executions)} recent executions:")
        for exec_id, created in recent_executions:
            print(f"   📍 {exec_id} ({created.strftime('%Y-%m-%d %H:%M')})")
        results['kept_recent'] = len(recent_executions)
        
        # Archive older executions (but only if data is persisted)
        if archive_candidates:
            print(f"\n📦 Archiving {len(archive_candidates)} older executions:")
            for exec_id, created in archive_candidates:
                if self.verify_data_persistence(exec_id):
                    if self.move_to_archive(exec_id):
                        results['archived'] += 1
                else:
                    print(f"⚠️  Keeping {exec_id} - data not verified in DB")
                    results['errors'].append(f"Data not verified: {exec_id}")
        
        # Clean up old archives
        print(f"\n🗑️  Cleaning archives older than {retention_days} days:")
        results['deleted_archives'] = self.cleanup_old_archives(retention_days)
        
        # Clean up Gatling reports
        print(f"\n🎯 Cleaning Gatling reports (keeping latest 2):")
        results['deleted_reports'] = self.cleanup_gatling_reports(keep_latest=2)
        
        # Summary
        print(f"\n📋 Cleanup Summary:")
        print(f"   ✅ Kept recent: {results['kept_recent']}")
        print(f"   📦 Archived: {results['archived']}")
        print(f"   🗑️  Deleted archives: {results['deleted_archives']}")
        print(f"   🎯 Deleted reports: {results['deleted_reports']}")
        if results['errors']:
            print(f"   ⚠️  Errors: {len(results['errors'])}")
        
        return results


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Clean up performance test artifacts")
    parser.add_argument('--dry-run', action='store_true', 
                       help='Show what would be done without making changes')
    parser.add_argument('--keep-recent', type=int, default=1,
                       help='Number of recent executions to keep in perf_runs (default: 1)')
    parser.add_argument('--retention-days', type=int, default=7,
                       help='Days to keep archived executions (default: 7)')
    
    args = parser.parse_args()
    
    cleanup_manager = PerformanceCleanupManager(dry_run=args.dry_run)
    results = cleanup_manager.run_cleanup(
        keep_recent_count=args.keep_recent,
        retention_days=args.retention_days
    )
    
    if results['errors']:
        print(f"\n⚠️  Some operations had issues. Consider running with --dry-run first.")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
