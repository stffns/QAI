from __future__ import annotations

"""Guardrails and simple policy checks for safe performance runs."""

from .dto import SimulationParams


class Guardrails:
    @staticmethod
    def validate(params: SimulationParams) -> None:
        # Disallow extreme runs in prod by default
        if params.environment.lower() in {"prod", "production"}:
            if params.test_type not in {"smoke", "baseline"}:
                raise ValueError("In production, only 'smoke' or 'baseline' tests are allowed")
            if params.users > 200:
                raise ValueError("In production, users must be <= 200")
            if params.duration_sec > 1800:
                raise ValueError("In production, duration must be <= 1800s (30m)")
