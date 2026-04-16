import argparse
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import joblib
import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import accuracy_score, f1_score, mean_absolute_error, mean_squared_error, precision_score, recall_score


def load_local_close_series(csv_path: Path) -> pd.Series:
    df = pd.read_csv(csv_path)

    # Normalize schema because repo CSVs are not fully uniform (e.g. Date vs timestamp, optional index column).
    original_columns = list(df.columns)
    normalized_columns = [str(col).strip().lower() for col in original_columns]
    col_map = dict(zip(normalized_columns, original_columns))

    timestamp_col = None
    for candidate in ["timestamp", "date", "datetime", "time"]:
        if candidate in col_map:
            timestamp_col = col_map[candidate]
            break

    close_col = col_map.get("close")
    if timestamp_col is None or close_col is None:
        raise ValueError(
            f"CSV must include a datetime column (timestamp/date/datetime/time) and close column. Found columns: {original_columns}"
        )

    df["_timestamp"] = pd.to_datetime(df[timestamp_col], utc=True, errors="coerce")
    df["_close"] = pd.to_numeric(df[close_col], errors="coerce")
    df = df.dropna(subset=["_timestamp", "_close"]).copy()
    df["date"] = df["_timestamp"].dt.tz_convert(None).dt.floor("D")

    series = (
        df.sort_values("date")
        .groupby("date", as_index=True)["_close"]
        .last()
        .astype(float)
    )
    return series


def sanitize_symbol(asset_symbol: str) -> str:
    return asset_symbol.upper().strip().replace("/", "")


def parse_assets(assets_arg: str) -> list[str]:
    assets = [sanitize_symbol(x) for x in assets_arg.split(",") if x.strip()]
    if not assets:
        raise ValueError("At least one asset must be provided.")
    return assets


def fetch_trending_symbols() -> list[str]:
    try:
        url = "https://api.coingecko.com/api/v3/search/trending"
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        payload = response.json()

        symbols = []
        for item in payload.get("coins", []):
            coin = item.get("item", {})
            sym = str(coin.get("symbol", "")).upper().strip()
            if sym:
                symbols.append(sym)
        if symbols:
            return symbols
    except Exception:
        pass

    # Fallback: top assets by market cap from CoinCap public API.
    url = "https://api.coincap.io/v2/assets"
    response = requests.get(url, params={"limit": 20}, timeout=30)
    response.raise_for_status()
    payload = response.json()
    return [str(item.get("symbol", "")).upper() for item in payload.get("data", []) if item.get("symbol")]


def resolve_coingecko_coin_id(asset_symbol: str) -> str:
    symbol = asset_symbol.replace("USD", "").replace("USDT", "").upper().strip()

    symbol_to_id = {
        "BTC": "bitcoin",
        "XBT": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
        "BNB": "binancecoin",
        "ADA": "cardano",
        "XRP": "ripple",
        "DOGE": "dogecoin",
        "DOT": "polkadot",
        "LTC": "litecoin",
        "TRX": "tron",
        "AVAX": "avalanche-2",
        "LINK": "chainlink",
        "NEAR": "near",
        "APE": "apecoin",
        "CRO": "crypto-com-chain",
        "AXS": "axie-infinity",
        "EOS": "eos",
        "BCH": "bitcoin-cash",
        "PEPE": "pepe",
        "APT": "aptos",
    }

    if symbol in symbol_to_id:
        return symbol_to_id[symbol]

    search_url = "https://api.coingecko.com/api/v3/search"
    response = requests.get(search_url, params={"query": symbol}, timeout=30)
    response.raise_for_status()
    payload = response.json()

    for coin in payload.get("coins", []):
        if str(coin.get("symbol", "")).upper() == symbol:
            return str(coin["id"])

    raise ValueError(f"Unable to resolve CoinGecko id for symbol: {asset_symbol}")


def fetch_api_daily_close(coin_id: str, start_dt: datetime, end_dt: datetime) -> pd.Series:
    from_ts = int(start_dt.replace(tzinfo=timezone.utc).timestamp())
    to_ts = int(end_dt.replace(tzinfo=timezone.utc).timestamp())

    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart/range"
        response = requests.get(
            url,
            params={"vs_currency": "usd", "from": from_ts, "to": to_ts},
            timeout=45,
        )
        response.raise_for_status()
        payload = response.json()

        prices = payload.get("prices", [])
        if prices:
            frame = pd.DataFrame(prices, columns=["ts_ms", "price"])
            frame["date"] = pd.to_datetime(frame["ts_ms"], unit="ms", utc=True).dt.tz_convert(None).dt.floor("D")

            series = (
                frame.sort_values("date")
                .groupby("date", as_index=True)["price"]
                .last()
                .astype(float)
            )
            return series
    except Exception:
        pass

    symbol = coin_id_to_symbol(coin_id)

    # Fallback 1: Yahoo Finance public chart API.
    try:
        yahoo_symbol = f"{symbol}-USD"
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{yahoo_symbol}"
        response = requests.get(
            url,
            params={"period1": from_ts, "period2": to_ts, "interval": "1d"},
            timeout=45,
        )
        response.raise_for_status()
        payload = response.json()

        result = payload.get("chart", {}).get("result", [])
        if result:
            timestamps = result[0].get("timestamp", [])
            closes = result[0].get("indicators", {}).get("quote", [{}])[0].get("close", [])
            frame = pd.DataFrame({"ts": timestamps, "close": closes}).dropna().copy()
            if not frame.empty:
                frame["date"] = pd.to_datetime(frame["ts"], unit="s", utc=True).dt.tz_convert(None).dt.floor("D")
                return frame.set_index("date")["close"].astype(float)
    except Exception:
        pass

    # Fallback 2: CryptoCompare public daily history endpoint.
    url = "https://min-api.cryptocompare.com/data/v2/histoday"
    response = requests.get(
        url,
        params={"fsym": symbol, "tsym": "USD", "limit": 2000, "toTs": to_ts},
        timeout=45,
    )
    response.raise_for_status()
    payload = response.json()

    rows = payload.get("Data", {}).get("Data", [])
    frame = pd.DataFrame(rows)
    if frame.empty or "time" not in frame.columns or "close" not in frame.columns:
        raise ValueError("CryptoCompare returned no usable daily series.")

    frame["date"] = pd.to_datetime(frame["time"], unit="s", utc=True).dt.tz_convert(None).dt.floor("D")
    frame = frame[(frame["time"] >= from_ts) & (frame["time"] <= to_ts)]
    frame = frame.dropna(subset=["close"])
    if frame.empty:
        raise ValueError("CryptoCompare returned empty close series for selected date range.")

    series = frame.set_index("date")["close"].astype(float)
    return series


def coin_id_to_symbol(coin_id: str) -> str:
    id_to_symbol = {
        "bitcoin": "BTC",
        "ethereum": "ETH",
        "solana": "SOL",
        "binancecoin": "BNB",
        "cardano": "ADA",
        "ripple": "XRP",
        "dogecoin": "DOGE",
        "polkadot": "DOT",
        "litecoin": "LTC",
        "tron": "TRX",
        "avalanche-2": "AVAX",
        "chainlink": "LINK",
        "near": "NEAR",
        "apecoin": "APE",
        "crypto-com-chain": "CRO",
        "axie-infinity": "AXS",
        "eos": "EOS",
        "bitcoin-cash": "BCH",
        "pepe": "PEPE",
        "aptos": "APT",
    }
    return id_to_symbol.get(coin_id, "ETH")


def build_supervised(close_series: pd.Series, lags: int = 30) -> pd.DataFrame:
    df = pd.DataFrame({"close": close_series.sort_index()})
    for lag in range(1, lags + 1):
        df[f"lag_{lag}"] = df["close"].shift(lag)

    df = df.dropna().copy()
    df["target"] = df["close"]
    return df


def build_naive_prediction(feature_df: pd.DataFrame) -> np.ndarray:
    # lag_1 is yesterday close; this is deterministic naive persistence baseline.
    return feature_df["lag_1"].values.astype(float)


def directional_scores(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    if len(y_true) < 2:
        return {
            "accuracy_score": float("nan"),
            "precision_score": float("nan"),
            "recall_score": float("nan"),
            "f1_score": float("nan"),
        }

    true_diff = np.diff(y_true)
    pred_diff = np.diff(y_pred)
    y_true_dir = true_diff > 0
    y_pred_dir = pred_diff > 0

    return {
        "accuracy_score": float(accuracy_score(y_true_dir, y_pred_dir)),
        "precision_score": float(precision_score(y_true_dir, y_pred_dir, zero_division=0)),
        "recall_score": float(recall_score(y_true_dir, y_pred_dir, zero_division=0)),
        "f1_score": float(f1_score(y_true_dir, y_pred_dir, zero_division=0)),
    }


def regression_scores(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    epsilon = 1e-9
    mape = np.mean(np.abs((y_true - y_pred) / np.maximum(np.abs(y_true), epsilon))) * 100.0
    smape = np.mean(2.0 * np.abs(y_true - y_pred) / np.maximum(np.abs(y_true) + np.abs(y_pred), epsilon)) * 100.0

    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "MAPE": float(mape),
        "SMAPE": float(smape),
    }


def all_scores(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, float]:
    scores = {}
    scores.update(regression_scores(y_true, y_pred))
    scores.update(directional_scores(y_true, y_pred))
    return scores


def compute_time_accuracy_curve(pred_df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    tmp = pred_df.copy()
    tmp["actual_diff"] = tmp["actual_close"].diff()
    tmp["pred_diff"] = tmp["predicted_close"].diff()
    tmp["is_correct_direction"] = (tmp["actual_diff"] > 0) == (tmp["pred_diff"] > 0)
    tmp = tmp.dropna().copy()
    tmp["rolling_accuracy"] = tmp["is_correct_direction"].rolling(window=window, min_periods=2).mean()
    tmp = tmp.dropna(subset=["rolling_accuracy"])
    return tmp[["date", "rolling_accuracy"]]


def save_accuracy_time_plot(curve_df: pd.DataFrame, out_path: Path, asset_symbol: str):
    plt.figure(figsize=(8, 10), dpi=140)
    plt.plot(curve_df["rolling_accuracy"], curve_df["date"], color="#0B7285", linewidth=2)
    plt.scatter(curve_df["rolling_accuracy"], curve_df["date"], color="#74C0FC", s=8, alpha=0.55)
    plt.xlabel("Accuracy (rolling directional)")
    plt.ylabel("Time")
    plt.title(f"{asset_symbol} - Time/Accuracy Trend (X=Accuracy, Y=Time)")
    plt.xlim(0.0, 1.0)
    plt.grid(alpha=0.25)
    plt.tight_layout()
    plt.savefig(out_path)
    plt.close()


def save_price_prediction_plot(pred_df: pd.DataFrame, out_path: Path, asset_symbol: str):
    """
    Two-subplot price comparison chart (simulation only — not investment advice).
    Top   : Daily close — predicted (blue dashed) vs actual (orange), X=time on monthly scale.
    Bottom: Weekly price fluctuation bars — actual vs predicted Δ per week.
    """
    df = pred_df.copy()
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")

    # Weekly resample — last close of each Friday.
    df_weekly = (
        df.set_index("date")
        .resample("W-FRI")
        .last()
        .dropna(subset=["actual_close", "predicted_close"])
        .reset_index()
    )
    df_weekly["actual_wk_change"] = df_weekly["actual_close"].diff()
    df_weekly["pred_wk_change"] = df_weekly["predicted_close"].diff()
    df_weekly = df_weekly.dropna(subset=["actual_wk_change", "pred_wk_change"])
    df_weekly["abs_divergence"] = (df_weekly["actual_wk_change"] - df_weekly["pred_wk_change"]).abs()
    max_div_idx = df_weekly["abs_divergence"].idxmax() if not df_weekly.empty else None

    eval_year = df["date"].dt.year.iloc[0] if not df.empty else "?"
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 9), dpi=140)
    fig.suptitle(
        f"{asset_symbol} — Predicted vs Actual Price\n"
        f"(Trained on past local data; evaluated on {eval_year} prices — simulation only)",
        fontsize=11,
        y=0.995,
    )

    # --- Top subplot: daily prices with monthly X ticks ---
    ax1.plot(df["date"], df["actual_close"], color="#E67700", linewidth=1.8, label="Actual close")
    ax1.plot(
        df["date"],
        df["predicted_close"],
        color="#1971C2",
        linewidth=1.5,
        linestyle="--",
        alpha=0.85,
        label="Predicted close",
    )
    ax1.xaxis.set_major_locator(mdates.MonthLocator())
    ax1.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax1.tick_params(axis="x", rotation=35)
    ax1.set_ylabel("Price (USD)")
    ax1.set_title("Daily close price — monthly scale")
    ax1.legend(loc="upper left", fontsize=9)
    ax1.grid(alpha=0.25)

    # --- Bottom subplot: weekly price fluctuation bars ---
    bar_width = pd.Timedelta(days=2)
    date_index = list(df_weekly.index)

    # Colour per bar: red on the week of maximum predicted-vs-actual divergence.
    for i, row in df_weekly.iterrows():
        is_max = max_div_idx is not None and i == max_div_idx
        c_act = "#C92A2A" if is_max else "#E67700"
        c_pred = "#C92A2A" if is_max else "#1971C2"
        ax2.bar(row["date"] - pd.Timedelta(days=1.8), row["actual_wk_change"],
                width=bar_width, color=c_act, alpha=0.80)
        ax2.bar(row["date"] + pd.Timedelta(days=1.8), row["pred_wk_change"],
                width=bar_width, color=c_pred, alpha=0.80)

    # Annotate the max-divergence week
    if max_div_idx is not None:
        row_max = df_weekly.loc[max_div_idx]
        div_val = row_max["abs_divergence"]
        y_top = max(abs(row_max["actual_wk_change"]), abs(row_max["pred_wk_change"]))
        ax2.annotate(
            f"Max \u0394 {div_val:,.0f}\n{row_max['date'].strftime('%d %b')}",
            xy=(row_max["date"], y_top),
            xytext=(row_max["date"], y_top + abs(y_top) * 0.45 + 1),
            arrowprops=dict(arrowstyle="->", color="#C92A2A", lw=1.4),
            fontsize=8, color="#C92A2A", ha="center",
        )

    # Legend proxies
    from matplotlib.patches import Patch
    ax2.legend(handles=[
        Patch(facecolor="#E67700", alpha=0.80, label="Actual weekly \u0394"),
        Patch(facecolor="#1971C2", alpha=0.80, label="Predicted weekly \u0394"),
        Patch(facecolor="#C92A2A", alpha=0.90, label="Max pred/actual divergence"),
    ], loc="upper left", fontsize=9)

    ax2.axhline(0, color="gray", linewidth=0.8, linestyle="-")
    ax2.xaxis.set_major_locator(mdates.MonthLocator())
    ax2.xaxis.set_major_formatter(mdates.DateFormatter("%b %Y"))
    ax2.tick_params(axis="x", rotation=35)
    ax2.set_ylabel("Weekly price change (USD)")
    ax2.set_title("Weekly price fluctuation \u2014 actual vs predicted  (red = max divergence)")
    ax2.grid(alpha=0.25)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(out_path)
    plt.close()


def walk_forward_scores(
    supervised: pd.DataFrame,
    train_end: pd.Timestamp,
    feature_cols: list[str],
    n_estimators: int,
    horizon: int,
    step: int,
) -> dict:
    wf_rows = []
    evaluation = supervised[supervised.index > train_end].copy()
    if len(evaluation) <= horizon + 1:
        return {"intervals": [], "mean_directional_accuracy": float("nan"), "mean_mape": float("nan")}

    anchor_positions = list(range(0, max(1, len(evaluation) - horizon), step))
    for pos in anchor_positions:
        start_date = evaluation.index[pos]
        end_pos = min(pos + horizon, len(evaluation))
        eval_slice = evaluation.iloc[pos:end_pos]
        train_slice = supervised[supervised.index < start_date]
        if len(train_slice) < 30 or eval_slice.empty:
            continue

        model = RandomForestRegressor(n_estimators=n_estimators, random_state=42, n_jobs=-1)
        model.fit(train_slice[feature_cols].values, train_slice["target"].values)
        pred = model.predict(eval_slice[feature_cols].values)
        s = all_scores(eval_slice["target"].values, pred)
        wf_rows.append(
            {
                "start_date": str(eval_slice.index.min().date()),
                "end_date": str(eval_slice.index.max().date()),
                "samples": int(len(eval_slice)),
                "MAPE": s["MAPE"],
                "accuracy_score": s["accuracy_score"],
            }
        )

    if not wf_rows:
        return {"intervals": [], "mean_directional_accuracy": float("nan"), "mean_mape": float("nan")}

    wf_df = pd.DataFrame(wf_rows)
    return {
        "intervals": wf_rows,
        "mean_directional_accuracy": float(wf_df["accuracy_score"].mean()),
        "mean_mape": float(wf_df["MAPE"].mean()),
    }


def run_meta_historical_test(
    asset_symbol: str,
    lags: int,
    n_estimators: int,
    accuracy_window: int,
    walk_forward_horizon: int,
    walk_forward_step: int,
    out_dir: Path,
) -> dict:
    root = Path(__file__).resolve().parent
    local_csv = root / "data" / f"{asset_symbol}-1d-data.csv"
    if not local_csv.exists():
        raise FileNotFoundError(f"Local dataset not found: {local_csv}")

    local_series = load_local_close_series(local_csv)
    train_end = local_series.index.max()

    trending_symbols = fetch_trending_symbols()
    coin_id = resolve_coingecko_coin_id(asset_symbol)

    api_start = train_end + timedelta(days=1)
    api_end = datetime.now(timezone.utc)
    api_series = fetch_api_daily_close(coin_id, api_start, api_end)

    combined_series = pd.concat([local_series, api_series])
    combined_series = combined_series[~combined_series.index.duplicated(keep="last")].sort_index()

    supervised = build_supervised(combined_series, lags=lags)
    feature_cols = [f"lag_{i}" for i in range(1, lags + 1)]

    train_mask = supervised.index <= train_end
    current_year = datetime.now().year
    eval_mask = supervised.index.year == current_year

    train_df = supervised.loc[train_mask]
    eval_df = supervised.loc[eval_mask]

    if train_df.empty:
        raise ValueError("No training rows available from past local dataset.")
    if eval_df.empty:
        raise ValueError("No current-year rows available for deterministic comparison.")

    model_past = RandomForestRegressor(
        n_estimators=n_estimators,
        random_state=42,
        n_jobs=-1,
    )
    model_past.fit(train_df[feature_cols].values, train_df["target"].values)

    y_true_eval = eval_df["target"].values
    y_pred_eval = model_past.predict(eval_df[feature_cols].values)

    model_scores = all_scores(y_true_eval, y_pred_eval)
    naive_pred_eval = build_naive_prediction(eval_df)
    naive_scores = all_scores(y_true_eval, naive_pred_eval)

    model_today = RandomForestRegressor(
        n_estimators=n_estimators,
        random_state=42,
        n_jobs=-1,
    )
    model_today.fit(supervised[feature_cols].values, supervised["target"].values)

    asset_dir = out_dir / asset_symbol
    asset_dir.mkdir(parents=True, exist_ok=True)

    pred_df = pd.DataFrame(
        {
            "date": eval_df.index,
            "actual_close": y_true_eval,
            "predicted_close": y_pred_eval,
            "abs_error": np.abs(y_true_eval - y_pred_eval),
            "signed_error": y_pred_eval - y_true_eval,
        }
    )
    pred_df.to_csv(asset_dir / "current_year_predictions.csv", index=False)
    save_price_prediction_plot(pred_df, asset_dir / "price_prediction_chart.png", asset_symbol)

    accuracy_curve = compute_time_accuracy_curve(pred_df, window=accuracy_window)
    accuracy_curve.to_csv(asset_dir / "accuracy_time_curve.csv", index=False)
    save_accuracy_time_plot(accuracy_curve, asset_dir / "accuracy_time_trend.png", asset_symbol)

    wf = walk_forward_scores(
        supervised=supervised,
        train_end=train_end,
        feature_cols=feature_cols,
        n_estimators=n_estimators,
        horizon=walk_forward_horizon,
        step=walk_forward_step,
    )

    joblib.dump(model_today, asset_dir / f"{asset_symbol}_model_retrained.joblib")

    report = {
        "asset_symbol": asset_symbol,
        "coin_id": coin_id,
        "train_end_date": str(train_end.date()),
        "evaluation_year": int(current_year),
        "evaluation_samples": int(len(eval_df)),
        "lags": int(lags),
        "n_estimators": int(n_estimators),
        "trending_symbols_snapshot": trending_symbols,
        "asset_in_trending_now": asset_symbol.replace("USD", "").replace("USDT", "").upper() in trending_symbols,
        "metrics_model": model_scores,
        "metrics_naive": naive_scores,
        "walk_forward": wf,
        "notes": [
            "Model trained only on past local data for evaluation phase.",
            "Evaluation uses deterministic lagged actual values with current-year targets.",
            "Backtesting/trading interpretation remains simulation-only.",
            "Model retrained afterward on all available data including current period.",
        ],
    }

    with open(asset_dir / "meta_historical_report.json", "w", encoding="utf-8") as fp:
        json.dump(report, fp, indent=2)

    return {
        "asset": asset_symbol,
        "asset_dir": str(asset_dir),
        "evaluation_samples": int(len(eval_df)),
        "model_accuracy": float(model_scores["accuracy_score"]),
        "model_mape": float(model_scores["MAPE"]),
        "naive_accuracy": float(naive_scores["accuracy_score"]),
        "naive_mape": float(naive_scores["MAPE"]),
    }


def run_cli():
    parser = argparse.ArgumentParser(
        prog="meta-historical",
        description="Deterministic meta-historical crypto validation CLI (past-only train, current-year compare, retrain).",
    )
    parser.add_argument("--assets", default="ETHUSD", help="Comma-separated assets (example: ETHUSD,XBTUSD,SOLUSD)")
    parser.add_argument("--lags", type=int, default=30, help="Lag features used by the model")
    parser.add_argument("--n-estimators", type=int, default=300, help="Random Forest estimators")
    parser.add_argument("--accuracy-window", type=int, default=14, help="Window for rolling directional accuracy")
    parser.add_argument("--wf-horizon", type=int, default=14, help="Walk-forward horizon in days")
    parser.add_argument("--wf-step", type=int, default=7, help="Walk-forward anchor step in days")
    parser.add_argument("--min-samples", type=int, default=100, help="Gate threshold: minimum eval samples per asset")
    parser.add_argument("--max-mape", type=float, default=4.0, help="Gate threshold: maximum acceptable MAPE")
    args = parser.parse_args()

    assets = parse_assets(args.assets)
    root = Path(__file__).resolve().parent
    now = datetime.now()
    out_dir = root / "outputs" / "meta_historical" / now.strftime("%Y-%m-%d") / now.strftime("%H-%M-%S")
    out_dir.mkdir(parents=True, exist_ok=True)

    summary_rows = []
    for asset in assets:
        result = run_meta_historical_test(
            asset_symbol=asset,
            lags=args.lags,
            n_estimators=args.n_estimators,
            accuracy_window=args.accuracy_window,
            walk_forward_horizon=args.wf_horizon,
            walk_forward_step=args.wf_step,
            out_dir=out_dir,
        )
        summary_rows.append(result)

    summary_df = pd.DataFrame(summary_rows)
    summary_df["passes_gate"] = (
        (summary_df["evaluation_samples"] >= args.min_samples) & (summary_df["model_mape"] <= args.max_mape)
    )
    summary_df.to_csv(out_dir / "summary.csv", index=False)

    with open(out_dir / "next_best_decision.txt", "w", encoding="utf-8") as fp:
        if bool(summary_df["passes_gate"].all()):
            fp.write(
                "Gate passed for all assets. Next Best Decision: execute weekly automated run with unchanged parameters "
                "to confirm metric stability across time."
            )
        else:
            failed_assets = ",".join(summary_df.loc[~summary_df["passes_gate"], "asset"].tolist())
            fp.write(
                "Gate failed for: "
                f"{failed_assets}. Next Best Decision: keep fixed assets and lags, increase n_estimators to 500, "
                "and rerun only failed assets to test if MAPE falls below threshold."
            )

    print("Meta-historical CLI completed.")
    print(f"Output: {out_dir}")
    print(summary_df.to_string(index=False))


if __name__ == "__main__":
    run_cli()
