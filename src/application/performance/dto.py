from __future__ import annotations

"""
DTOs for the performance execution flow.

These types define the contract between agent tools, application layer, and
infrastructure adapters. Keep them minimal and explicit—AI will fill them.
"""

from datetime import datetime
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field


class ScenarioParams(BaseModel):
    """One scenario within a simulation.

    - scenario_slug: logical scenario name to map to Gatling scenario template(s)
    - endpoint_slug: logical endpoint name; may also be a direct URL (http...)
    - rps_target: desired RPS throttle for this scenario (optional)
    - feeder_file: optional path to a CSV/JSON feeder consumed by Gatling
    - injection_profile: list of opaque steps for flexibility; AI/process can craft them
    """

    scenario_slug: Optional[str] = Field(
        default=None, description="Logical scenario name"
    )
    endpoint_slug: Optional[str] = Field(
        default=None, description="Logical endpoint or full URL"
    )
    rps_target: Optional[float] = Field(
        default=None, ge=0, description="Target requests per second"
    )
    feeder_file: Optional[str] = Field(
        default=None, description="Path to feeder file (CSV/JSON)"
    )
    injection_profile: Optional[List[dict[str, Any]]] = Field(
        default=None,
        description="List of injection steps, e.g., [{'type':'ramp_users','users':50,'duration_sec':60}]",
    )


class SimulationParams(BaseModel):
    """Parameters required to launch a Gatling run.

    Backward-compatible single-scenario fields remain (users, duration_sec, endpoint_slug);
    for multi-scenario runs, fill `scenarios` with one or more ScenarioParams.
    """

    app_slug: str = Field(
        ..., description="Application identifier, e.g., ecommerce, payments"
    )
    country_code: str = Field(..., description="ISO country code, e.g., AR, CL, PE")
    environment: str = Field(..., description="Target env, e.g., dev, qa, uat, prod")

    test_type: Literal["smoke", "baseline", "load", "stress"] = Field(
        default="smoke", description="Type of performance test"
    )

    # Single-scenario convenience (legacy)
    users: int = Field(10, ge=1, le=100000, description="Virtual users")
    duration_sec: int = Field(
        60, ge=1, le=86400, description="Test duration in seconds"
    )
    endpoint_slug: Optional[str] = Field(
        default=None,
        description="Optional logical endpoint id; can be a full URL; runner resolves from DB",
    )
    # New single-scenario optional fields for convenience
    scenario_slug: Optional[str] = Field(
        default=None, description="Scenario name for single-scenario runs"
    )
    rps_target: Optional[float] = Field(
        default=None, ge=0, description="Target RPS for single-scenario"
    )
    feeder_file: Optional[str] = Field(
        default=None, description="Feeder file for single-scenario"
    )
    injection_profile: Optional[List[dict[str, Any]]] = Field(
        default=None, description="Injection steps for single-scenario"
    )

    # Multi-scenario support
    scenarios: Optional[List[ScenarioParams]] = Field(
        default=None,
        description="List of scenarios for multi-endpoint/multi-profile runs",
    )
    notes: Optional[str] = Field(
        default=None, description="Free-text notes for the execution"
    )

    # Optional: Assertions tuning (runner may map to -D props)
    enable_assertions: Optional[bool] = Field(
        default=None, description="Enable/disable assertions"
    )
    fail_pct_lt: Optional[float] = Field(
        default=None, ge=0, description="Max failed requests percentage"
    )
    p95_lt: Optional[float] = Field(
        default=None,
        ge=0,
        description="p95 (percentile3) response time upper bound in ms",
    )
    p99_lt: Optional[float] = Field(
        default=None,
        ge=0,
        description="p99 (percentile4) response time upper bound in ms",
    )
    mean_rt_lt: Optional[float] = Field(
        default=None, ge=0, description="Mean response time upper bound in ms"
    )

    # Optional: Injection profile tuning
    injection: Optional[str] = Field(default=None, description="constantRps|rampRps")
    ramp_up: Optional[int] = Field(default=None, ge=0, description="Ramp-up seconds")
    hold_for: Optional[int] = Field(default=None, ge=0, description="Hold-for seconds")
    ramp_down: Optional[int] = Field(
        default=None, ge=0, description="Ramp-down seconds"
    )
    to_users: Optional[int] = Field(
        default=None, ge=1, description="Target users (if applicable)"
    )
    pause_ms: Optional[int] = Field(
        default=None, ge=0, description="Pause between chained endpoints in ms"
    )


class RunSubmitted(BaseModel):
    execution_id: str
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    params: SimulationParams


class RunStatus(BaseModel):
    execution_id: str
    status: Literal["queued", "running", "succeeded", "failed"] = "queued"
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    progress: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    summary: Optional[str] = None


class RunList(BaseModel):
    items: List[RunStatus] = []
