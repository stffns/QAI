"""
Performance Test Executions Repository
======================================

Repository implementation for performance test executions with enhanced tracking and analysis capabilities.
"""

from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timedelta
from sqlmodel import Session, select, and_, or_, func, desc, asc

try:
    from database.repositories.base import BaseRepository
    from database.models.performance_test_executions import (
        PerformanceTestExecution,
        PerformanceTestExecutionCreate,
        PerformanceTestExecutionUpdate,
        PerformanceTestExecutionQuery,
        PerformanceTestExecutionSummary,
        PerformanceTestExecutionComparison,
        BaselineComparisonResult,
        ExecutionStatus,
        ValidationStatus,
        SLACompliance,
        ExecutionScope,
        PerformanceGrade
    )
    from database.repositories.exceptions import (
        EntityNotFoundError,
        InvalidEntityError,
        DuplicateEntityError
    )
except ImportError:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
    from database.repositories.base import BaseRepository
    from database.models.performance_test_executions import (
        PerformanceTestExecution,
        PerformanceTestExecutionCreate,
        PerformanceTestExecutionUpdate,
        PerformanceTestExecutionQuery,
        PerformanceTestExecutionSummary,
        PerformanceTestExecutionComparison,
        BaselineComparisonResult,
        ExecutionStatus,
        ValidationStatus,
        SLACompliance,
        ExecutionScope,
        PerformanceGrade
    )
    from database.repositories.exceptions import (
        EntityNotFoundError,
        InvalidEntityError,
        DuplicateEntityError
    )


class PerformanceTestExecutionRepository(BaseRepository[PerformanceTestExecution]):
    """Repository for performance test executions with enhanced tracking capabilities."""
    
    def __init__(self, session: Session):
        super().__init__(session, PerformanceTestExecution)

    def create(self, data: Dict[str, Any]) -> PerformanceTestExecution:
        """Create a new execution from data dictionary."""
        execution = PerformanceTestExecution(**data)
        return self.save(execution)

    def find_by_execution_id(self, execution_id: str) -> Optional[PerformanceTestExecution]:
        """Find execution by execution_id."""
        stmt = select(PerformanceTestExecution).where(PerformanceTestExecution.execution_id == execution_id)
        return self.session.exec(stmt).first()

    def find_by_config(
        self, 
        test_config_id: int, 
        status: Optional[ExecutionStatus] = None,
        limit: Optional[int] = None
    ) -> List[PerformanceTestExecution]:
        """Find executions by test configuration."""
        stmt = select(PerformanceTestExecution).where(PerformanceTestExecution.test_config_id == test_config_id)
        
        if status:
            stmt = stmt.where(PerformanceTestExecution.status == status)
        
        stmt = stmt.order_by(desc(PerformanceTestExecution.created_at))
        
        if limit:
            stmt = stmt.limit(limit)
        
        return list(self.session.exec(stmt).all())

    def find_baselines(self, test_config_id: Optional[int] = None) -> List[PerformanceTestExecution]:
        """Find baseline executions."""
        stmt = (
            select(PerformanceTestExecution)
            .where(PerformanceTestExecution.is_baseline == True)
        )
        
        if test_config_id:
            stmt = stmt.where(PerformanceTestExecution.test_config_id == test_config_id)
        
        stmt = stmt.order_by(desc(PerformanceTestExecution.created_at))
        
        return list(self.session.exec(stmt).all())

    def find_by_status(self, status: ExecutionStatus) -> List[PerformanceTestExecution]:
        """Find executions by status."""
        stmt = (
            select(PerformanceTestExecution)
            .where(PerformanceTestExecution.status == status)
            .order_by(desc(PerformanceTestExecution.created_at))
        )
        
        return list(self.session.exec(stmt).all())

    def find_pending_validation(self) -> List[PerformanceTestExecution]:
        """Find executions pending validation."""
        stmt = (
            select(PerformanceTestExecution)
            .where(
                and_(
                    PerformanceTestExecution.validation_status == ValidationStatus.PENDING,
                    PerformanceTestExecution.status == ExecutionStatus.COMPLETED
                )
            )
            .order_by(asc(PerformanceTestExecution.created_at))
        )
        
        return list(self.session.exec(stmt).all())

    def find_by_time_range(
        self, 
        start_date: datetime, 
        end_date: datetime,
        test_config_id: Optional[int] = None
    ) -> List[PerformanceTestExecution]:
        """Find executions within time range."""
        # Get all executions and filter in Python to avoid type issues
        stmt = select(PerformanceTestExecution)
        
        if test_config_id:
            stmt = stmt.where(PerformanceTestExecution.test_config_id == test_config_id)
        
        all_executions = list(self.session.exec(stmt).all())
        
        # Filter by time range in Python
        filtered = []
        for execution in all_executions:
            if (execution.start_time and 
                execution.start_time >= start_date and 
                execution.start_time <= end_date):
                filtered.append(execution)
        
        # Sort by start_time
        filtered.sort(key=lambda x: x.start_time or datetime.min)
        
        return filtered

    def find_by_comparison_group(self, comparison_group: str) -> List[PerformanceTestExecution]:
        """Find executions by comparison group."""
        stmt = (
            select(PerformanceTestExecution)
            .where(PerformanceTestExecution.comparison_group == comparison_group)
            .order_by(asc(PerformanceTestExecution.created_at))
        )
        
        return list(self.session.exec(stmt).all())

    def find_by_sla_compliance(self, compliance: SLACompliance) -> List[PerformanceTestExecution]:
        """Find executions by SLA compliance."""
        stmt = (
            select(PerformanceTestExecution)
            .where(PerformanceTestExecution.sla_compliance == compliance)
            .order_by(desc(PerformanceTestExecution.created_at))
        )
        
        return list(self.session.exec(stmt).all())

    def update_status(
        self, 
        execution_id: str, 
        status: ExecutionStatus,
        updated_by: Optional[str] = None,
        end_time: Optional[datetime] = None
    ) -> PerformanceTestExecution:
        """Update execution status."""
        execution = self.find_by_execution_id(execution_id)
        if not execution:
            raise EntityNotFoundError("PerformanceTestExecution", execution_id)
        
        execution.status = status
        execution.updated_at = datetime.utcnow()
        if updated_by:
            execution.updated_by = updated_by
        if end_time:
            execution.end_time = end_time
            if execution.start_time:
                execution.duration_seconds = (end_time - execution.start_time).total_seconds()
        
        self.session.add(execution)
        self.session.commit()
        self.session.refresh(execution)
        
        return execution

    def update_metrics(self, execution_id: str, fields: Dict[str, Any]) -> PerformanceTestExecution:
        """Update execution metrics and related paths.

        Accepts a dictionary with keys matching PerformanceTestExecution fields, such as:
        total_requests, successful_requests, failed_requests, avg_rps,
        avg_response_time, p95_response_time, p99_response_time,
        min_response_time, max_response_time, error_rate, gatling_report_path.
        """
        execution = self.find_by_execution_id(execution_id)
        if not execution:
            raise EntityNotFoundError("PerformanceTestExecution", execution_id)

        allowed = {
            "total_requests",
            "successful_requests",
            "failed_requests",
            "avg_rps",
            "avg_response_time",
            "p95_response_time",
            "p99_response_time",
            "min_response_time",
            "max_response_time",
            "error_rate",
            "gatling_report_path",
        }
        for k, v in fields.items():
            if k in allowed:
                setattr(execution, k, v)

        execution.updated_at = datetime.utcnow()
        self.session.add(execution)
        self.session.commit()
        self.session.refresh(execution)
        return execution

    def update_validation_status(
        self, 
        execution_id: str, 
        validation_status: ValidationStatus,
        sla_compliance: Optional[SLACompliance] = None,
        performance_grade: Optional[PerformanceGrade] = None,
        validated_by: Optional[str] = None
    ) -> PerformanceTestExecution:
        """Update validation status and related fields."""
        execution = self.find_by_execution_id(execution_id)
        if not execution:
            raise EntityNotFoundError("PerformanceTestExecution", execution_id)
        
        execution.validation_status = validation_status
        if sla_compliance:
            execution.sla_compliance = sla_compliance
        if performance_grade:
            execution.performance_grade = performance_grade
        if validated_by:
            execution.updated_by = validated_by
        execution.updated_at = datetime.utcnow()
        
        self.session.add(execution)
        self.session.commit()
        self.session.refresh(execution)
        
        return execution

    def mark_as_baseline(
        self, 
        execution_id: str, 
        marked_by: Optional[str] = None
    ) -> PerformanceTestExecution:
        """Mark execution as baseline."""
        execution = self.find_by_execution_id(execution_id)
        if not execution:
            raise EntityNotFoundError("PerformanceTestExecution", execution_id)
        
        if execution.status != ExecutionStatus.COMPLETED:
            raise InvalidEntityError("PerformanceTestExecution", ["Cannot mark incomplete execution as baseline"])
        
        execution.is_baseline = True
        execution.updated_at = datetime.utcnow()
        if marked_by:
            execution.updated_by = marked_by
        
        self.session.add(execution)
        self.session.commit()
        self.session.refresh(execution)
        
        return execution

    def get_latest_baseline(self, test_config_id: int) -> Optional[PerformanceTestExecution]:
        """Get latest baseline execution for a test configuration."""
        stmt = (
            select(PerformanceTestExecution)
            .where(
                and_(
                    PerformanceTestExecution.test_config_id == test_config_id,
                    PerformanceTestExecution.is_baseline == True,
                    PerformanceTestExecution.status == ExecutionStatus.COMPLETED
                )
            )
            .order_by(desc(PerformanceTestExecution.created_at))
            .limit(1)
        )
        
        return self.session.exec(stmt).first()

    def compare_with_baseline(
        self, 
        execution_id: str
    ) -> Optional[BaselineComparisonResult]:
        """Compare execution with baseline."""
        execution = self.find_by_execution_id(execution_id)
        if not execution or not execution.test_config_id:
            return None
        
        baseline = self.get_latest_baseline(execution.test_config_id)
        if not baseline:
            return None
        
        # Calculate deltas
        response_time_delta = self._calculate_percentage_delta(
            baseline.avg_response_time, execution.avg_response_time
        )
        throughput_delta = self._calculate_percentage_delta(
            baseline.avg_rps, execution.avg_rps
        )
        error_rate_delta = self._calculate_percentage_delta(
            baseline.error_rate or 0, execution.error_rate or 0
        )
        
        # Calculate overall performance delta (weighted average)
        performance_delta = (
            response_time_delta * -0.4 +  # Lower is better
            throughput_delta * 0.4 +      # Higher is better
            error_rate_delta * -0.2       # Lower is better
        )
        
        # Determine grade and recommendation
        overall_grade = self._calculate_overall_grade(performance_delta, error_rate_delta)
        recommendation = self._generate_recommendation(performance_delta, response_time_delta, throughput_delta, error_rate_delta)
        
        return BaselineComparisonResult(
            current_execution_id=execution_id,
            baseline_execution_id=baseline.execution_id,
            performance_delta=performance_delta,
            response_time_delta=response_time_delta,
            throughput_delta=throughput_delta,
            error_rate_delta=error_rate_delta,
            overall_grade=overall_grade,
            recommendation=recommendation
        )

    def get_execution_statistics(
        self, 
        test_config_id: Optional[int] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """Get execution statistics."""
        since_date = datetime.utcnow() - timedelta(days=days)
        
        base_filter = PerformanceTestExecution.created_at >= since_date
        if test_config_id:
            base_filter = and_(base_filter, PerformanceTestExecution.test_config_id == test_config_id)
        
        # Get all executions in period
        executions = list(self.session.exec(
            select(PerformanceTestExecution).where(base_filter)
        ).all())
        
        if not executions:
            return {
                "total_executions": 0,
                "period_days": days,
                "test_config_id": test_config_id
            }
        
        # Calculate statistics
        total = len(executions)
        completed = len([e for e in executions if e.status == ExecutionStatus.COMPLETED])
        failed = len([e for e in executions if e.status == ExecutionStatus.FAILED])
        
        # SLA compliance
        sla_pass = len([e for e in executions if e.sla_compliance == SLACompliance.PASS])
        sla_fail = len([e for e in executions if e.sla_compliance == SLACompliance.FAIL])
        
        # Performance grades
        grade_distribution = {}
        for grade in PerformanceGrade:
            grade_distribution[grade.value] = len([e for e in executions if e.performance_grade == grade])
        
        # Average metrics (for completed executions)
        completed_executions = [e for e in executions if e.status == ExecutionStatus.COMPLETED]
        avg_response_time = None
        avg_throughput = None
        avg_error_rate = None
        
        if completed_executions:
            response_times = [e.avg_response_time for e in completed_executions if e.avg_response_time]
            throughputs = [e.avg_rps for e in completed_executions if e.avg_rps]
            error_rates = [e.error_rate for e in completed_executions if e.error_rate]
            
            if response_times:
                avg_response_time = sum(response_times) / len(response_times)
            if throughputs:
                avg_throughput = sum(throughputs) / len(throughputs)
            if error_rates:
                avg_error_rate = sum(error_rates) / len(error_rates)
        
        return {
            "total_executions": total,
            "completed": completed,
            "failed": failed,
            "success_rate": completed / total if total > 0 else 0,
            "sla_compliance": {
                "pass": sla_pass,
                "fail": sla_fail,
                "pass_rate": sla_pass / (sla_pass + sla_fail) if (sla_pass + sla_fail) > 0 else 0
            },
            "grade_distribution": grade_distribution,
            "average_metrics": {
                "response_time_ms": avg_response_time,
                "throughput_rps": avg_throughput,
                "error_rate": avg_error_rate
            },
            "period_days": days,
            "test_config_id": test_config_id
        }

    def get_trend_analysis(
        self, 
        test_config_id: int, 
        days: int = 30,
        interval_days: int = 7
    ) -> List[Dict[str, Any]]:
        """Get trend analysis over time periods."""
        end_date = datetime.utcnow()
        trends = []
        
        for i in range(0, days, interval_days):
            period_end = end_date - timedelta(days=i)
            period_start = period_end - timedelta(days=interval_days)
            
            executions = self.find_by_time_range(period_start, period_end, test_config_id)
            completed = [e for e in executions if e.status == ExecutionStatus.COMPLETED]
            
            if completed:
                avg_response = sum(e.avg_response_time for e in completed if e.avg_response_time) / len(completed)
                avg_throughput = sum(e.avg_rps for e in completed if e.avg_rps) / len(completed)
                avg_error_rate = sum(e.error_rate for e in completed if e.error_rate) / len(completed)
                
                trends.append({
                    "period_start": period_start,
                    "period_end": period_end,
                    "executions_count": len(executions),
                    "completed_count": len(completed),
                    "avg_response_time": avg_response,
                    "avg_throughput": avg_throughput,
                    "avg_error_rate": avg_error_rate
                })
        
        return list(reversed(trends))  # Return chronological order

    def _calculate_percentage_delta(self, baseline: Optional[float], current: Optional[float]) -> float:
        """Calculate percentage delta between baseline and current value."""
        if baseline is None or current is None or baseline == 0:
            return 0.0
        return ((current - baseline) / baseline) * 100

    def _calculate_overall_grade(self, performance_delta: float, error_rate_delta: float) -> PerformanceGrade:
        """Calculate overall performance grade."""
        if error_rate_delta > 50:  # Error rate increased by more than 50%
            return PerformanceGrade.F
        elif performance_delta >= 10:
            return PerformanceGrade.A
        elif performance_delta >= 5:
            return PerformanceGrade.B
        elif performance_delta >= -5:
            return PerformanceGrade.C
        elif performance_delta >= -15:
            return PerformanceGrade.D
        else:
            return PerformanceGrade.F

    def _generate_recommendation(
        self, 
        performance_delta: float, 
        response_time_delta: float, 
        throughput_delta: float, 
        error_rate_delta: float
    ) -> str:
        """Generate performance recommendation."""
        recommendations = []
        
        if error_rate_delta > 20:
            recommendations.append("High error rate increase detected - investigate error causes")
        elif error_rate_delta < -20:
            recommendations.append("Error rate significantly improved")
        
        if response_time_delta > 20:
            recommendations.append("Response times degraded - check system resources")
        elif response_time_delta < -20:
            recommendations.append("Response times improved significantly")
        
        if throughput_delta > 20:
            recommendations.append("Throughput improved - good performance")
        elif throughput_delta < -20:
            recommendations.append("Throughput decreased - investigate bottlenecks")
        
        if performance_delta >= 10:
            recommendations.append("Overall performance excellent")
        elif performance_delta <= -15:
            recommendations.append("Overall performance needs attention")
        
        return "; ".join(recommendations) if recommendations else "Performance within normal range"

    def get_summary_list(
        self, 
        query: Optional[PerformanceTestExecutionQuery] = None
    ) -> List[PerformanceTestExecutionSummary]:
        """Get summary list of executions with filters."""
        # This would typically use a complex query with joins
        # For simplicity, using basic filtering
        all_executions = self.get_all()
        
        # Apply filters if query provided
        if query:
            filtered = []
            for execution in all_executions:
                if query.test_config_id and execution.test_config_id != query.test_config_id:
                    continue
                if query.status and execution.status != query.status:
                    continue
                if query.validation_status and execution.validation_status != query.validation_status:
                    continue
                if query.sla_compliance and execution.sla_compliance != query.sla_compliance:
                    continue
                if query.execution_scope and execution.execution_scope != query.execution_scope:
                    continue
                if query.is_baseline is not None and execution.is_baseline != query.is_baseline:
                    continue
                if not query.include_failed and execution.status == ExecutionStatus.FAILED:
                    continue
                filtered.append(execution)
            all_executions = filtered
        
        # Convert to summary format
        summaries = []
        for execution in all_executions:
            if execution.id is not None:  # Only include executions with valid IDs
                summary = PerformanceTestExecutionSummary(
                    id=execution.id,
                    execution_id=execution.execution_id,
                    execution_name=execution.execution_name,
                    status=execution.status,
                    validation_status=execution.validation_status,
                    sla_compliance=execution.sla_compliance,
                    execution_scope=execution.execution_scope,
                    performance_grade=execution.performance_grade,
                    is_baseline=execution.is_baseline,
                    start_time=execution.start_time,
                    end_time=execution.end_time,
                    duration_seconds=execution.duration_seconds,
                    error_rate=execution.error_rate,
                    total_requests=execution.total_requests,
                    created_at=execution.created_at
                )
                summaries.append(summary)
        
        return summaries
