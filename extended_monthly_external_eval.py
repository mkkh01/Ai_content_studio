#!/usr/bin/env python3
"""Rolling monthly external holdouts for the BTCUSDT derivatives dataset."""
from __future__ import annotations
import argparse
from pathlib import Path
import numpy as np
import pandas as pd
from research_engine import Config, ResearchEngine
from ml_walk_forward import MLConfig, executable_target, model_candidates, score_predictions


def evaluate(csv: str, output: str, mode: str = 'derivatives') -> pd.DataFrame:
    cfg = MLConfig(horizon=6, execution_delay=1, train_bars=1440, validation_bars=240, fee_bps=6, slippage_bps=4, feature_mode=mode, target_cost_adjusted=True, uncertainty_multiple=.5)
    engine = ResearchEngine(Config(feature_mode=mode))
    raw = engine.load(csv)
    X = engine.features(raw)
    gross = executable_target(raw, cfg.horizon, cfg.execution_delay)
    cost = (cfg.fee_bps + cfg.slippage_bps) / 10000.0
    train_y = (gross - np.sign(gross) * cost).rename('target_train')
    aligned = X.join(train_y).join(gross).dropna()
    X = aligned.drop(columns=['target_train', 'target_gross'])
    train_y, gross = aligned['target_train'], aligned['target_gross']
    months = pd.date_range('2025-06-01', '2026-07-01', freq='MS', tz='UTC')
    rows = []
    for cutoff in months:
        next_month = cutoff + pd.offsets.MonthBegin(1)
        pre = np.where(X.index < cutoff)[0]
        test = np.where((X.index >= cutoff) & (X.index < next_month))[0]
        if len(pre) < cfg.train_bars + cfg.validation_bars + cfg.horizon or len(test) <= cfg.horizon:
            continue
        train_end = pre[-1] + 1 - cfg.horizon
        val_start = train_end - cfg.validation_bars
        train_start = val_start - cfg.train_bars
        test_start = test[0] + cfg.horizon
        if train_start < 0 or test_start >= len(X):
            continue
        best = None
        for candidate in model_candidates('hist_gradient_boosting', cfg.seed):
            candidate.fit(X.iloc[train_start:train_end], train_y.iloc[train_start:train_end])
            pred_val = candidate.predict(X.iloc[val_start:train_end])
            residual = float(np.std(np.asarray(train_y.iloc[val_start:train_end]) - pred_val, ddof=1))
            threshold = max(cost * cfg.neutral_cost_multiple, cfg.uncertainty_multiple * residual)
            val = score_predictions(pred_val, gross.iloc[val_start:train_end], cfg.horizon, cfg.fee_bps, cfg.slippage_bps, threshold)
            if best is None or val['relative_sharpe'] > best[0]:
                best = (val['relative_sharpe'], candidate, threshold)
        model = best[1]
        model.fit(X.iloc[train_start:train_end], train_y.iloc[train_start:train_end])
        pred = model.predict(X.iloc[test_start:test[-1] + 1])
        result = score_predictions(pred, gross.iloc[test_start:test[-1] + 1], cfg.horizon, cfg.fee_bps, cfg.slippage_bps, best[2])
        rows.append({'month': cutoff.strftime('%Y-%m'), 'feature_mode': mode, 'validation_relative_sharpe': best[0], **{f'test_{k}': v for k, v in result.items()}})
    out = pd.DataFrame(rows)
    Path(output).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(output, index=False)
    print(out.round(6).to_string(index=False))
    return out

if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--csv', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--feature-mode', default='derivatives')
    a = p.parse_args()
    evaluate(a.csv, a.output, a.feature_mode)
