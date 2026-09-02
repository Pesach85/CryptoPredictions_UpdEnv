"""FastAPI server for projections, long-horizon forecasts, scenario backtests, and data refresh."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from services.data_refresh import refresh_all_assets, refresh_asset_via_api, stealth_browser_instructions
from services.long_horizon import LongHorizonService
from services.multi_model_paths import ALL_MODELS, FAST_MODELS, MultiModelPathService
from services.projection import ProjectionService, ScenarioSpec
from services.scenario_backtest import ScenarioBacktestService
from services.volatility_events import VolatilityEventService

app = FastAPI(
    title="CryptoPredictions API",
    description="Experimental projection and scenario API — simulation only, not investment advice.",
    version="1.0.0",
)

projection_svc = ProjectionService()
long_svc = LongHorizonService()
backtest_svc = ScenarioBacktestService()
multi_model_svc = MultiModelPathService()
volatility_svc = VolatilityEventService()


class ScenarioInput(BaseModel):
    name: str
    price_shock_pct: float = 0.0
    volatility_multiplier: float = 1.0
    volume_multiplier: float = 1.0
    shock_day: int = 0


class ProjectRequest(BaseModel):
    asset: str
    horizon_days: int = Field(default=30, ge=1, le=365)
    as_of_date: str | None = None
    lags: int | None = None
    feature_mode: Literal["close", "focused", "enhanced"] | None = None
    n_estimators: int | None = None
    scenarios: list[ScenarioInput] = Field(default_factory=list)
    persist: bool = True


class LongProjectRequest(BaseModel):
    asset: str
    horizon_days: int = Field(default=180, ge=90, le=365)
    as_of_date: str | None = None
    model: Literal["prophet", "orbit"] = "prophet"
    persist: bool = True


class ScenarioBacktestRequest(BaseModel):
    asset: str
    horizon_days: int = Field(default=30, ge=1, le=365)
    as_of_date: str | None = None
    scenarios: list[ScenarioInput] = Field(default_factory=list)
    history_days: int = Field(default=60, ge=10, le=365)


class RefreshRequest(BaseModel):
    assets: list[str] | None = None
    backup: bool = True


class MultiModelPathRequest(BaseModel):
    asset: str
    window_start: str = "2026-08-01"
    window_end: str | None = None
    models: list[str] | None = None
    fast: bool = False
    persist: bool = False


class VolatilityForecastRequest(BaseModel):
    asset: str
    threshold_pct: float = Field(default=10.0, ge=5.0, le=25.0)
    as_of_date: str | None = None


def _to_scenarios(items: list[ScenarioInput]) -> list[ScenarioSpec]:
    return [ScenarioSpec(**s.model_dump()) for s in items]


def _frame_to_records(df) -> list[dict[str, Any]]:
    out = df.copy()
    out["date"] = out["date"].astype(str)
    return out.to_dict(orient="records")


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "disclaimer": "Simulation only — not investment advice."}


@app.get("/api/v1/assets")
def list_assets(interval: str = "1d"):
    return {"assets": projection_svc.list_assets(interval=interval)}


@app.get("/api/v1/assets/{asset}/profile")
def asset_profile(asset: str):
    try:
        return projection_svc.get_profile(asset)
    except Exception as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/project")
def project(req: ProjectRequest):
    try:
        result = projection_svc.project_forward(
            asset_symbol=req.asset,
            horizon_days=req.horizon_days,
            as_of_date=req.as_of_date,
            lags=req.lags,
            feature_mode=req.feature_mode,
            n_estimators=req.n_estimators,
            scenarios=_to_scenarios(req.scenarios),
            persist=req.persist,
        )
        return {
            "asset_symbol": result.asset_symbol,
            "as_of_date": result.as_of_date,
            "horizon_days": result.horizon_days,
            "profile": result.profile,
            "metadata": result.metadata,
            "base_path": _frame_to_records(result.base_path),
            "scenario_paths": {k: _frame_to_records(v) for k, v in result.scenario_paths.items()},
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/project/long")
def project_long(req: LongProjectRequest):
    try:
        result = long_svc.project(
            asset_symbol=req.asset,
            horizon_days=req.horizon_days,
            as_of_date=req.as_of_date,
            model=req.model,
            persist=req.persist,
        )
        return {
            "asset_symbol": result.asset_symbol,
            "as_of_date": result.as_of_date,
            "horizon_days": result.horizon_days,
            "model": result.model,
            "metadata": result.metadata,
            "forecast": _frame_to_records(result.forecast),
        }
    except ImportError as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/scenarios/compare")
def compare_scenarios(req: ProjectRequest):
    if not req.scenarios:
        raise HTTPException(status_code=400, detail="At least one scenario required.")
    return project(req)


@app.post("/api/v1/paths/compare")
def compare_model_paths(req: MultiModelPathRequest):
    """Real vs multi-model closes over a historical window (simulation only)."""
    try:
        if req.fast:
            models = list(FAST_MODELS)
        elif req.models:
            models = req.models
        else:
            models = None
        if models:
            bad = set(models) - set(ALL_MODELS)
            if bad:
                raise ValueError(f"Unknown models: {sorted(bad)}")
        result = multi_model_svc.run(
            asset_symbol=req.asset,
            window_start=req.window_start,
            window_end=req.window_end,
            models=models,
            persist=req.persist,
        )
        payload = result.to_dict()
        payload["disclaimer"] = "Simulation only — not investment advice."
        return payload
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/volatility/forecast")
def volatility_forecast(req: VolatilityForecastRequest):
    """Probability and timing of next +/-threshold_pct move (simulation only)."""
    try:
        result = volatility_svc.forecast(
            asset_symbol=req.asset,
            threshold_pct=req.threshold_pct,
            as_of_date=req.as_of_date,
        )
        return result.to_dict()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/backtest/scenario")
def backtest_scenario(req: ScenarioBacktestRequest):
    try:
        outcomes = backtest_svc.backtest_from_projection(
            asset_symbol=req.asset,
            horizon_days=req.horizon_days,
            as_of_date=req.as_of_date,
            scenarios=_to_scenarios(req.scenarios),
        )
        return {
            "asset": req.asset,
            "results": [
                {
                    "scenario": o.scenario_name,
                    "return_pct": o.return_pct,
                    "equity_final": o.equity_final,
                    "trades": o.trades,
                }
                for o in outcomes
            ],
            "disclaimer": "Simulation only — not investment advice.",
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/v1/data/refresh")
def refresh_data(req: RefreshRequest):
    results = refresh_all_assets(assets=req.assets, backup=req.backup)
    return {"results": results}


@app.post("/api/v1/data/refresh/{asset}")
def refresh_single_asset(asset: str, backup: bool = True):
    try:
        return refresh_asset_via_api(asset, backup=backup)
    except Exception as exc:
        return {
            "asset": asset,
            "status": "error",
            "error": str(exc),
            "stealth_fallback": stealth_browser_instructions(asset),
        }


@app.get("/api/v1/data/stealth-instructions/{asset}")
def stealth_instructions(asset: str):
    return {"instructions": stealth_browser_instructions(asset)}
