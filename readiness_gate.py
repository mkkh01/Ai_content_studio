#!/usr/bin/env python3
"""Independent readiness gate for a crypto research strategy.

This script is deliberately not an optimizer. It cannot change thresholds,
select a favorable period, or improve a result. It reads already-produced
walk-forward, cost-sensitivity, and external-holdout files and returns a
non-zero exit code unless every pre-declared production criterion passes.

The gate is an evidence checker, not a profitability guarantee. A passing
result still requires operational controls and a staged paper-trading period.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULTS = {
    "min_windows": 8,
    "min_median_relative_sharpe": 0.50,
    "min_mean_net_return": 0.0,
    "min_positive_window_fraction": 0.625,
    "min_independent_trades_per_window": 20,
    "min_external_months": 3,
    "min_external_relative_sharpe": 0.25,
    "min_external_net_return": 0.0,
    "min_external_positive_fraction": 2 / 3,
    "required_cost_multiples": [1.0, 2.0],
}


def _require_columns(df: pd.DataFrame, columns: list[str], label: str) -> None:
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise ValueError(f"{label} is missing required columns: {missing}")


def evaluate_walk_forward(df: pd.DataFrame, cfg: dict) -> dict:
    _require_columns(df, ["model", "windows", "median_relative_sharpe", "mean_net_return", "mean_trades"], "walk-forward summary")
    rows = []
    for _, r in df.iterrows():
        checks = {
            "windows": float(r["windows"]) >= cfg["min_windows"],
            "median_relative_sharpe": float(r["median_relative_sharpe"]) >= cfg["min_median_relative_sharpe"],
            "mean_net_return": float(r["mean_net_return"]) > cfg["min_mean_net_return"],
            "mean_trades": float(r["mean_trades"]) >= cfg["min_independent_trades_per_window"],
        }
        rows.append({"model": r["model"], "feature_mode": r.get("feature_mode", "unknown"), "scope": "walk_forward", "pass": all(checks.values()), **checks})
    return rows


def evaluate_costs(df: pd.DataFrame, cfg: dict) -> list[dict]:
    if df.empty:
        return [{"scope": "cost_sensitivity", "pass": False, "reason": "missing cost-sensitivity data"}]
    _require_columns(df, ["cost_multiple", "feature_mode", "model", "mean_relative_sharpe", "mean_net_return"], "cost summary")
    rows = []
    for (mode, model), group in df.groupby(["feature_mode", "model"]):
        checks = {}
        for multiple in cfg["required_cost_multiples"]:
            g = group[np.isclose(group["cost_multiple"].astype(float), multiple)]
            checks[f"cost_{multiple:g}x_present"] = len(g) == 1
            if len(g) == 1:
                checks[f"cost_{multiple:g}x_relative_sharpe"] = float(g.iloc[0]["mean_relative_sharpe"]) > 0
                checks[f"cost_{multiple:g}x_return"] = float(g.iloc[0]["mean_net_return"]) > 0
        rows.append({"model": model, "feature_mode": mode, "scope": "cost_sensitivity", "pass": all(checks.values()), **checks})
    return rows


def evaluate_external(df: pd.DataFrame, cfg: dict) -> list[dict]:
    if df.empty:
        return [{"scope": "external_holdout", "pass": False, "reason": "missing external holdout data"}]
    _require_columns(df, ["feature_mode", "test_relative_sharpe", "test_net_return", "test_trades"], "external summary")
    # The current external file may contain one row per mode. A future file can
    # include a month column; then each mode must pass across separate months.
    month_col = "month" if "month" in df.columns else None
    rows = []
    for mode, group in df.groupby("feature_mode"):
        months = group[month_col].nunique() if month_col else len(group)
        positive_fraction = float((group["test_net_return"] > 0).mean())
        checks = {
            "external_months": months >= cfg["min_external_months"],
            "external_relative_sharpe": float(group["test_relative_sharpe"].median()) >= cfg["min_external_relative_sharpe"],
            "external_return": float(group["test_net_return"].mean()) > cfg["min_external_net_return"],
            "external_positive_fraction": positive_fraction >= cfg["min_external_positive_fraction"],
            "external_trade_count": int(group["test_trades"].min()) >= cfg["min_independent_trades_per_window"],
        }
        rows.append({"feature_mode": mode, "model": "external", "scope": "external_holdout", "pass": all(checks.values()), **checks})
    return rows


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--walk-forward", type=Path, required=True)
    p.add_argument("--cost-summary", type=Path, required=True)
    p.add_argument("--external", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--config", type=Path, help="Optional JSON file overriding pre-declared gates")
    args = p.parse_args()

    cfg = DEFAULTS.copy()
    if args.config:
        cfg.update(json.loads(args.config.read_text(encoding="utf-8")))

    wf = pd.read_csv(args.walk_forward)
    costs = pd.read_csv(args.cost_summary)
    external = pd.read_csv(args.external)
    checks = evaluate_walk_forward(wf, cfg) + evaluate_costs(costs, cfg) + evaluate_external(external, cfg)
    passed = bool(checks) and all(bool(row.get("pass", False)) for row in checks)
    report = {
        "decision": "PASS_PRODUCTION_GATE" if passed else "FAIL_REMAIN_PAPER_TRADING",
        "passed": passed,
        "criteria": cfg,
        "checks": checks,
        "interpretation": "A pass is evidence of robustness, not a promise of profit; a fail prohibits production deployment.",
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    raise SystemExit(0 if passed else 2)


if __name__ == "__main__":
    main()
