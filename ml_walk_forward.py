from __future__ import annotations
import argparse, json
from dataclasses import asdict, dataclass
from pathlib import Path
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.linear_model import ElasticNet
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from research_engine import Config, ResearchEngine

@dataclass
class MLConfig:
    horizon: int = 6
    windows: int = 4
    train_bars: int = 1200
    validation_bars: int = 300
    test_bars: int = 300
    fee_bps: float = 6.0
    slippage_bps: float = 4.0
    bars_per_year: int = 24 * 365
    neutral_cost_multiple: float = 1.5
    feature_mode: str = 'liquidity'
    seed: int = 42


def net_sharpe(returns: np.ndarray, annual_factor: float) -> float:
    returns = np.asarray(returns, dtype=float)
    returns = returns[np.isfinite(returns)]
    if len(returns) < 2 or np.std(returns, ddof=1) <= 1e-12:
        return 0.0
    return float(np.mean(returns) / np.std(returns, ddof=1) * np.sqrt(annual_factor))


def score_predictions(pred, actual, horizon, fee_bps, slippage_bps, threshold):
    pred = np.asarray(pred, dtype=float)
    actual = np.asarray(actual, dtype=float)
    idx = np.arange(0, len(actual), max(1, horizon))
    pred, actual = pred[idx], actual[idx]
    cost = (fee_bps + slippage_bps) / 10000.0
    signals = np.where(np.abs(pred) > threshold, np.sign(pred), 0.0)
    net = signals * actual - (signals != 0) * cost
    benchmark = actual - cost
    annual_factor = 24 * 365 / max(1, horizon)
    sharpe = net_sharpe(net, annual_factor)
    benchmark_sharpe = net_sharpe(benchmark, annual_factor)
    active = net[signals != 0]
    return {
        'sharpe_net': sharpe,
        'benchmark_sharpe_net': benchmark_sharpe,
        'relative_sharpe': sharpe - benchmark_sharpe,
        'net_return': float(np.prod(1 + net) - 1),
        'benchmark_net_return': float(np.prod(1 + benchmark) - 1),
        'mean_net_return': float(np.mean(net)),
        'trades': int(np.sum(signals != 0)),
        'observations': int(len(net)),
        'coverage': float(np.mean(signals != 0)),
        'threshold': float(threshold),
        'active_mean_return': float(np.mean(active)) if len(active) else 0.0,
    }


def model_candidates(kind, seed):
    if kind == 'elastic_net':
        return [
            make_pipeline(StandardScaler(), ElasticNet(alpha=a, l1_ratio=l, max_iter=20000, tol=1e-5, random_state=seed))
            for a, l in [(0.0001, 0.1), (0.001, 0.5), (0.01, 0.8)]
        ]
    return [
        HistGradientBoostingRegressor(max_iter=it, learning_rate=lr, max_leaf_nodes=leaf,
                                      l2_regularization=1.0, random_state=seed)
        for it, lr, leaf in [(100, 0.03, 7), (150, 0.05, 7), (200, 0.03, 15)]
    ]


def run(path, out_dir, cfg: MLConfig):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    engine = ResearchEngine(Config(seed=cfg.seed, feature_mode=cfg.feature_mode,
                                   fee_bps=cfg.fee_bps, slippage_bps=cfg.slippage_bps))
    raw = engine.load(path)
    X = engine.features(raw)
    y = engine.target(raw, cfg.horizon).rename('target')
    aligned = X.join(y).join(raw['close'].rename('close')).dropna()
    X, y, close = aligned.drop(columns=['target','close']), aligned['target'], aligned['close']
    rows=[]
    for kind in ['elastic_net', 'hist_gradient_boosting']:
        for w in range(cfg.windows):
            start = w * cfg.test_bars
            train_end = start + cfg.train_bars
            val_end = train_end + cfg.validation_bars
            test_end = val_end + cfg.test_bars
            if test_end > len(X): break
            Xtr, ytr = X.iloc[start:train_end], y.iloc[start:train_end]
            Xv, yv = X.iloc[train_end:val_end], y.iloc[train_end:val_end]
            Xt, yt = X.iloc[val_end:test_end], y.iloc[val_end:test_end]
            train_std = float(ytr.std())
            threshold = max((cfg.fee_bps + cfg.slippage_bps) / 10000 * cfg.neutral_cost_multiple,
                            0.25 * train_std)
            best_model, best_val = None, -np.inf
            for candidate in model_candidates(kind, cfg.seed + w):
                candidate.fit(Xtr, ytr)
                val_pred = candidate.predict(Xv)
                val_score = score_predictions(val_pred, yv, cfg.horizon, cfg.fee_bps, cfg.slippage_bps, threshold)
                if val_score['relative_sharpe'] > best_val:
                    best_model, best_val = candidate, val_score['relative_sharpe']
            test_pred = best_model.predict(Xt)
            test_score = score_predictions(test_pred, yt, cfg.horizon, cfg.fee_bps, cfg.slippage_bps, threshold)
            rows.append({'model':kind,'window':w+1,'validation_relative_sharpe':best_val,
                         **{f'test_{k}':v for k,v in test_score.items()}})
    result = pd.DataFrame(rows)
    result.to_csv(out/'ml_walk_forward_results.csv', index=False)
    summary = result.groupby('model').agg(windows=('window','size'),
        mean_sharpe_net=('test_sharpe_net','mean'), median_sharpe_net=('test_sharpe_net','median'),
        mean_relative_sharpe=('test_relative_sharpe','mean'), median_relative_sharpe=('test_relative_sharpe','median'),
        mean_net_return=('test_net_return','mean'), mean_benchmark_return=('test_benchmark_net_return','mean'),
        mean_trades=('test_trades','mean'), mean_coverage=('test_coverage','mean')).reset_index()
    summary.to_csv(out/'ml_walk_forward_summary.csv', index=False)
    (out/'ml_walk_forward_config.json').write_text(json.dumps(asdict(cfg), indent=2), encoding='utf-8')
    print(summary.round(6).to_string(index=False))
    return result, summary

if __name__ == '__main__':
    p=argparse.ArgumentParser()
    p.add_argument('--csv', required=True); p.add_argument('--output', default='ml_runs')
    p.add_argument('--horizon', type=int, default=6); p.add_argument('--windows', type=int, default=4)
    p.add_argument('--feature-mode', default='liquidity')
    args=p.parse_args()
    run(args.csv, args.output, MLConfig(horizon=args.horizon, windows=args.windows, feature_mode=args.feature_mode))
