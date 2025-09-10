from __future__ import annotations

"""Build normalized config for the underlying Gatling runner."""

from typing import Any, Dict, List

from .dto import ScenarioParams, SimulationParams


class ConfigBuilder:
    @staticmethod
    def build(params: SimulationParams, resolved_url: str | None, resolved_scenarios: List[str] | None = None) -> Dict:
        def scenario_to_dict(sp: ScenarioParams, default_url: str) -> Dict[str, Any]:
            # If the scenario provides a full URL, use it; otherwise prefer the resolved default_url
            endpoint = sp.endpoint_slug if (sp.endpoint_slug and sp.endpoint_slug.startswith("http")) else default_url
            return {
                "scenario_slug": sp.scenario_slug,
                "endpoint": endpoint,
                "rps_target": sp.rps_target,
                "feeder_file": sp.feeder_file,
                "injection_profile": sp.injection_profile,
            }

        config: Dict[str, Any] = {
            "app": params.app_slug,
            "country": params.country_code,
            "environment": params.environment,
            "test_type": params.test_type,
            "metadata": {
                "endpoint_slug": params.endpoint_slug,
                "scenario_slug": params.scenario_slug,
                "notes": params.notes,
            },
        }

        # Multi-scenario preferred
        if params.scenarios:
            scenarios: List[Dict[str, Any]] = []
            for idx, sp in enumerate(params.scenarios):
                # When multi-scenario, prefer resolved_scenarios[idx] if provided
                default = resolved_scenarios[idx] if (resolved_scenarios and idx < len(resolved_scenarios)) else (resolved_url or "")
                scenarios.append(scenario_to_dict(sp, default))
            config["scenarios"] = scenarios
        else:
            # Backward compatible single-scenario
            single = ScenarioParams(
                scenario_slug=params.scenario_slug,
                endpoint_slug=params.endpoint_slug,
                rps_target=params.rps_target,
                feeder_file=params.feeder_file,
                injection_profile=params.injection_profile,
            )
            safe_url = resolved_url or ""
            config.update(
                {
                    "endpoint": safe_url,
                    "load": {"users": params.users, "duration_sec": params.duration_sec},
                    "scenario": scenario_to_dict(single, safe_url),
                }
            )

        return config
