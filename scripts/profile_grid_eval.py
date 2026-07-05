"""Quick local grid eval: lags x features per asset on holdout after cutoff."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import pandas as pd
from sklearn.ensemble import RandomForestRegressor

from meta_historical_test import all_scores, build_supervised, build_supervised_focused, load_local_close_series
from services.assets import resolve_data_path

ASSETS = ["XBTUSD", "LTCUSD", "ETHUSD", "ADAUSD", "BCHUSD", "SOLUSD", "BNBUSD", "DOGEUSD", "AVAXUSD"]
LAGS_OPTS = [14, 30]
FEAT_OPTS = ["close", "focused"]
CUTOFF = "2025-12-31"
N_EST = 300


def main():
    results = []
    for asset in ASSETS:
        csv = resolve_data_path(asset)
        close = load_local_close_series(csv)
        cutoff = pd.Timestamp(CUTOFF)
        for lags in LAGS_OPTS:
            for feat in FEAT_OPTS:
                try:
                    if feat == "focused":
                        sup, cols = build_supervised_focused(close, lags=lags)
                    else:
                        sup = build_supervised(close, lags=lags)
                        cols = [f"lag_{i}" for i in range(1, lags + 1)]
                    train = sup[sup.index <= cutoff]
                    test = sup[sup.index > cutoff]
                    if len(train) < 50 or len(test) < 20:
                        continue
                    model = RandomForestRegressor(n_estimators=N_EST, random_state=42, n_jobs=-1)
                    model.fit(train[cols].values, train["target"].values)
                    pred = model.predict(test[cols].values)
                    scores = all_scores(test["target"].values, pred)
                    results.append(
                        {
                            "asset": asset,
                            "lags": lags,
                            "features": feat,
                            "mape": round(scores["MAPE"], 3),
                            "dir_acc": round(scores["accuracy_score"], 3),
                            "test_n": len(test),
                        }
                    )
                except Exception as exc:
                    results.append({"asset": asset, "lags": lags, "features": feat, "error": str(exc)})

    by_asset = {}
    for row in results:
        if "error" in row:
            continue
        asset = row["asset"]
        key = (-row["mape"], row["dir_acc"])
        if asset not in by_asset or key > (-by_asset[asset]["mape"], by_asset[asset]["dir_acc"]):
            by_asset[asset] = row

    profiles = json.loads((ROOT / "config/asset_profiles.json").read_text(encoding="utf-8"))
    comparison = []
    for asset in ASSETS:
        cur = profiles.get(asset, profiles["default"])
        best = by_asset.get(asset)
        if not best:
            comparison.append({"asset": asset, "status": "no_data"})
            continue
        comparison.append(
            {
                "asset": asset,
                "current": {"lags": cur["lags"], "features": cur["features"]},
                "best_mape": {"lags": best["lags"], "features": best["features"], "mape": best["mape"], "dir_acc": best["dir_acc"]},
                "profile_match": cur["lags"] == best["lags"] and cur["features"] == best["features"],
            }
        )

    out = {"cutoff": CUTOFF, "results": results, "best_per_asset": by_asset, "comparison": comparison}
    print(json.dumps(out, indent=2))


if __name__ == "__main__":
    main()
