"""
CryptoPredictions — Projection & What-If Scenario Explorer

Run: streamlit run app_projection.py

Simulation only — not investment advice.
"""

from __future__ import annotations

import json
from datetime import datetime

import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st

from services.projection import ProjectionService, ScenarioSpec
from services.long_horizon import LongHorizonService
from services.scenario_backtest import ScenarioBacktestService
from services.data_refresh import refresh_asset_via_api, stealth_browser_instructions

st.set_page_config(
    page_title="CryptoPredictions — Projection Lab",
    page_icon="📈",
    layout="wide",
)

DISCLAIMER = (
    "**Simulation only — not investment advice.** "
    "Projections are experimental model outputs for research and software validation."
)


@st.cache_resource
def get_service() -> ProjectionService:
    return ProjectionService()


@st.cache_resource
def get_long_service() -> LongHorizonService:
    return LongHorizonService()


@st.cache_resource
def get_backtest_service() -> ScenarioBacktestService:
    return ScenarioBacktestService()


def render_disclaimer():
    st.warning(DISCLAIMER)


def plot_projection(result, show_scenarios: bool = True):
    fig, ax = plt.subplots(figsize=(12, 5), dpi=120)
    base = result.base_path
    ax.fill_between(
        base["date"],
        base["interval_low"],
        base["interval_high"],
        alpha=0.2,
        color="#1971C2",
        label="Base 10–90% interval",
    )
    ax.plot(base["date"], base["forecast_close"], color="#1971C2", linewidth=2, label="Base forecast")

    colors = ["#E67700", "#2F9E44", "#C92A2A", "#7048E8"]
    if show_scenarios:
        for idx, (name, frame) in enumerate(result.scenario_paths.items()):
            color = colors[idx % len(colors)]
            ax.plot(
                frame["date"],
                frame["forecast_close"],
                linewidth=1.8,
                linestyle="--",
                color=color,
                label=f"Scenario: {name}",
            )

    ax.set_title(
        f"{result.asset_symbol} — Forward projection from {result.as_of_date} "
        f"({result.horizon_days} days)"
    )
    ax.set_xlabel("Date")
    ax.set_ylabel("Price (USD)")
    ax.legend(loc="upper left", fontsize=9)
    ax.grid(alpha=0.25)
    plt.xticks(rotation=30)
    plt.tight_layout()
    st.pyplot(fig)
    plt.close(fig)


def main():
    st.title("Projection Lab")
    st.caption("Forward projections and what-if scenarios for crypto price research")
    render_disclaimer()

    service = get_service()
    assets = service.list_assets()
    if not assets:
        st.error("No daily datasets found in data/.")
        return

    with st.sidebar:
        st.header("Configuration")
        asset = st.selectbox("Asset", assets, index=assets.index("ETHUSD") if "ETHUSD" in assets else 0)
        profile = service.get_profile(asset)
        st.info(
            f"Profile: lags={profile['lags']}, features={profile['features']}, "
            f"n_estimators={profile['n_estimators']}"
        )
        if profile.get("description"):
            st.caption(profile["description"])

        horizon_days = st.slider("Horizon (days)", min_value=7, max_value=180, value=30, step=1)
        use_custom_cutoff = st.checkbox("Custom as-of date", value=False)
        as_of_date = None
        if use_custom_cutoff:
            as_of_date = st.date_input("As-of date", value=datetime(2023, 2, 17)).isoformat()

        advanced = st.expander("Advanced model overrides")
        with advanced:
            lags = st.number_input("Lags", min_value=7, max_value=90, value=profile["lags"])
            feature_mode = st.selectbox(
                "Feature mode",
                ["close", "focused", "enhanced"],
                index=["close", "focused", "enhanced"].index(profile["features"]),
            )
            n_estimators = st.number_input(
                "n_estimators", min_value=100, max_value=1000, value=profile["n_estimators"], step=50
            )

        st.header("What-If Scenarios")
        enable_bear = st.checkbox("Bear shock (-20%)", value=False)
        bear_day = st.number_input("Bear shock day", min_value=1, max_value=horizon_days, value=1)
        enable_bull = st.checkbox("Bull shock (+15%)", value=False)
        bull_day = st.number_input("Bull shock day", min_value=1, max_value=horizon_days, value=7)
        vol_mult = st.slider("Volatility multiplier", min_value=0.5, max_value=2.0, value=1.0, step=0.1)
        run_btn = st.button("Run projection", type="primary", use_container_width=True)

    tab_proj, tab_compare, tab_long, tab_backtest, tab_data, tab_artifacts = st.tabs(
        ["Projection", "Scenario compare", "Long horizon", "Scenario backtest", "Data refresh", "Artifacts"]
    )

    if run_btn:
        scenarios: list[ScenarioSpec] = []
        if enable_bear:
            scenarios.append(
                ScenarioSpec(name="Bear -20%", price_shock_pct=-20.0, shock_day=int(bear_day))
            )
        if enable_bull:
            scenarios.append(
                ScenarioSpec(name="Bull +15%", price_shock_pct=15.0, shock_day=int(bull_day))
            )
        if vol_mult != 1.0:
            scenarios.append(
                ScenarioSpec(name=f"Volatility x{vol_mult}", volatility_multiplier=vol_mult)
            )

        with st.spinner(f"Projecting {asset} for {horizon_days} days..."):
            try:
                result = service.project_forward(
                    asset_symbol=asset,
                    horizon_days=horizon_days,
                    as_of_date=as_of_date,
                    lags=int(lags),
                    feature_mode=feature_mode,
                    n_estimators=int(n_estimators),
                    scenarios=scenarios,
                )
                st.session_state["last_result"] = result
            except Exception as exc:
                st.error(f"Projection failed: {exc}")
                return

    result = st.session_state.get("last_result")
    if result is None:
        with tab_proj:
            st.info("Configure parameters in the sidebar and click **Run projection**.")
        return

    with tab_proj:
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Last observed close", f"${result.metadata['last_observed_close']:,.2f}")
        col2.metric("Horizon", f"{result.horizon_days} days")
        col3.metric(
            "End forecast",
            f"${result.base_path['forecast_close'].iloc[-1]:,.2f}",
        )
        end_change = (
            (result.base_path["forecast_close"].iloc[-1] / result.metadata["last_observed_close"]) - 1
        ) * 100
        col4.metric("Base % change", f"{end_change:+.1f}%")

        plot_projection(result, show_scenarios=bool(result.scenario_paths))
        st.dataframe(result.base_path, use_container_width=True)

    with tab_compare:
        if not result.scenario_paths:
            st.info("Enable at least one what-if scenario in the sidebar to compare paths.")
        else:
            compare_rows = []
            for name, frame in result.scenario_paths.items():
                end_price = float(frame["forecast_close"].iloc[-1])
                base_end = float(result.base_path["forecast_close"].iloc[-1])
                compare_rows.append(
                    {
                        "scenario": name,
                        "end_price": end_price,
                        "vs_base_pct": ((end_price / base_end) - 1) * 100,
                        "vs_last_obs_pct": (
                            (end_price / result.metadata["last_observed_close"]) - 1
                        )
                        * 100,
                    }
                )
            st.dataframe(pd.DataFrame(compare_rows), use_container_width=True)
            plot_projection(result, show_scenarios=True)

    with tab_artifacts:
        artifact_dir = result.metadata.get("artifact_dir")
        if artifact_dir:
            st.code(artifact_dir)
            report_path = f"{artifact_dir}/projection_report.json"
            try:
                with open(report_path, encoding="utf-8") as fp:
                    st.json(json.load(fp))
            except OSError:
                st.caption("Report file not found.")
        else:
            st.caption("Artifacts are saved under outputs/projections/ when projection runs.")

    with tab_long:
        st.subheader("Long horizon (90–365 days)")
        st.caption("Prophet fan chart — native uncertainty bands for extended horizons.")
        lh_horizon = st.slider("Long horizon days", 90, 365, 180, key="lh_horizon")
        lh_model = st.selectbox("Model", ["prophet", "orbit"], key="lh_model")
        if st.button("Run long projection", key="run_long"):
            with st.spinner("Fitting Prophet/Orbit..."):
                try:
                    lh_result = get_long_service().project(
                        asset_symbol=asset,
                        horizon_days=lh_horizon,
                        as_of_date=as_of_date,
                        model=lh_model,
                    )
                    st.session_state["long_result"] = lh_result
                except Exception as exc:
                    st.error(str(exc))
        lh_result = st.session_state.get("long_result")
        if lh_result:
            fig, ax = plt.subplots(figsize=(12, 5), dpi=120)
            fc = lh_result.forecast
            ax.fill_between(fc["date"], fc["interval_low"], fc["interval_high"], alpha=0.25, color="#7048E8")
            ax.plot(fc["date"], fc["forecast_close"], color="#7048E8", linewidth=2)
            ax.set_title(f"{lh_result.asset_symbol} — {lh_result.model} {lh_result.horizon_days}d fan chart")
            ax.grid(alpha=0.25)
            plt.xticks(rotation=30)
            plt.tight_layout()
            st.pyplot(fig)
            plt.close(fig)
            st.dataframe(fc, use_container_width=True)

    with tab_backtest:
        st.subheader("Scenario backtest (signal1 on projected path)")
        if st.button("Run scenario backtest", key="run_bt"):
            with st.spinner("Backtesting projected paths..."):
                try:
                    bt_outcomes = get_backtest_service().backtest_projection_result(result)
                    st.session_state["bt_outcomes"] = bt_outcomes
                except Exception as exc:
                    st.error(str(exc))
        bt_outcomes = st.session_state.get("bt_outcomes")
        if bt_outcomes:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "scenario": o.scenario_name,
                            "return_pct": f"{o.return_pct:.2f}%",
                            "equity_final": f"${o.equity_final:,.0f}",
                            "trades": o.trades,
                        }
                        for o in bt_outcomes
                    ]
                ),
                use_container_width=True,
            )
        else:
            st.info("Run a projection first, then click **Run scenario backtest**.")

    with tab_data:
        st.subheader("Data refresh")
        st.caption("Extend local CSV via public APIs. On failure, use stealth-browser fallback.")
        if st.button("Refresh asset via API", key="refresh_api"):
            with st.spinner(f"Refreshing {asset}..."):
                try:
                    refresh_result = refresh_asset_via_api(asset)
                    st.session_state["refresh_result"] = refresh_result
                except Exception as exc:
                    st.session_state["refresh_result"] = {"status": "error", "error": str(exc)}
        if st.session_state.get("refresh_result"):
            st.json(st.session_state["refresh_result"])
        with st.expander("Stealth-browser fallback instructions"):
            st.code(stealth_browser_instructions(asset))


if __name__ == "__main__":
    main()
