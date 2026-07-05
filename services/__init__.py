"""Shared services for projection, scenario analysis, and asset configuration."""

from services.projection import ProjectionService, ScenarioSpec

__all__ = [
    "ProjectionService",
    "ScenarioSpec",
    "LongHorizonService",
    "LongHorizonResult",
    "ScenarioBacktestService",
    "ScenarioBacktestResult",
    "refresh_all_assets",
    "refresh_asset_via_api",
]


def __getattr__(name: str):
    if name == "LongHorizonService":
        from services.long_horizon import LongHorizonService
        return LongHorizonService
    if name == "LongHorizonResult":
        from services.long_horizon import LongHorizonResult
        return LongHorizonResult
    if name == "ScenarioBacktestService":
        from services.scenario_backtest import ScenarioBacktestService
        return ScenarioBacktestService
    if name == "ScenarioBacktestResult":
        from services.scenario_backtest import ScenarioBacktestResult
        return ScenarioBacktestResult
    if name == "refresh_all_assets":
        from services.data_refresh import refresh_all_assets
        return refresh_all_assets
    if name == "refresh_asset_via_api":
        from services.data_refresh import refresh_asset_via_api
        return refresh_asset_via_api
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
