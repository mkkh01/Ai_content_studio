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
    execution_delay: int = 1
    windows: int = 4
    train_bars: int = 1200
    validation_bars: int = 300
    test_bars: int = 300
    fee_bps: float = 6.0
    slippage_bps: float = 4.0
    bars_per_year: int = 24 * 365
    neutral_cost_multiple: float = 1.5
    uncertainty_multiple: float = 0.5
    target_cost_adjusted: bool = True
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
    benchmark = actual.copy()
    if len(benchmark): benchmark[0] -= cost
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


def executable_target(raw, horizon, execution_delay):
    entry = raw['open'].shift(-execution_delay)
    exit_ = raw['close'].shift(-(execution_delay + horizon))
    return (exit_ / entry - 1).rename('target_gross')


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
    y_gross = executable_target(raw, cfg.horizon, cfg.execution_delay)
    y_train = y_gross.copy()
    if cfg.target_cost_adjusted:
        cost = (cfg.fee_bps + cfg.slippage_bps) / 10000.0
        y_train = (y_gross - np.sign(y_gross) * cost).rename('target_train')
    else:
        y_train = y_train.rename('target_train')
    aligned = X.join(y_train).join(y_gross).join(raw['close'].rename('close')).dropna()
    X = aligned.drop(columns=['target_train','target_gross','close'])
    y_train, y_gross, close = aligned['target_train'], aligned['target_gross'], aligned['close']
    rows=[]
    for kind in ['elastic_net', 'hist_gradient_boosting']:
        for w in range(cfg.windows):
            start = w * cfg.test_bars
            raw_train_end = start + cfg.train_bars
            train_end = raw_train_end - cfg.horizon
            val_start = raw_train_end
            val_end = val_start + cfg.validation_bars
            test_start = val_end + cfg.horizon
            test_end = test_start + cfg.test_bars
            if test_end > len(X): break
            Xtr, ytr = X.iloc[start:train_end], y_train.iloc[start:train_end]
            Xv, yv = X.iloc[val_start:val_end], y_train.iloc[val_start:val_end]
            Xt, yt = X.iloc[test_start:test_end], y_gross.iloc[test_start:test_end]
            best_model, best_val, best_threshold = None, -np.inf, None
            for candidate in model_candidates(kind, cfg.seed + w):
                candidate.fit(Xtr, ytr)
                val_pred = candidate.predict(Xv)
                residual_std = float(np.std(np.asarray(yv) - np.asarray(val_pred), ddof=1)) if len(yv) > 1 else float(ytr.std())
                threshold = max((cfg.fee_bps + cfg.slippage_bps) / 10000 * cfg.neutral_cost_multiple,
                                cfg.uncertainty_multiple * residual_std)
                val_score = score_predictions(val_pred, yv, cfg.horizon, cfg.fee_bps, cfg.slippage_bps, threshold)
                if val_score['relative_sharpe'] > best_val:
                    best_model, best_val, best_threshold = candidate, val_score['relative_sharpe'], threshold
            test_pred = best_model.predict(Xt)
            test_score = score_predictions(test_pred, yt, cfg.horizon, cfg.fee_bps, cfg.slippage_bps, best_threshold)
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
    p.add_argument('--horizon', type=int, default=6); p.add_argument('--execution-delay', type=int, default=1); p.add_argument('--windows', type=int, default=4)
    p.add_argument('--train-bars', type=int, default=1200); p.add_argument('--validation-bars', type=int, default=300); p.add_argument('--test-bars', type=int, default=300)
    p.add_argument('--fee-bps', type=float, default=6.0); p.add_argument('--slippage-bps', type=float, default=4.0)
    p.add_argument('--uncertainty-multiple', type=float, default=0.5)
    p.add_argument('--feature-mode', default='liquidity')
    args=p.parse_args()
    run(args.csv, args.output, MLConfig(horizon=args.horizon, execution_delay=args.execution_delay, windows=args.windows, train_bars=args.train_bars, validation_bars=args.validation_bars, test_bars=args.test_bars, fee_bps=args.fee_bps, slippage_bps=args.slippage_bps, uncertainty_multiple=args.uncertainty_multiple, feature_mode=args.feature_mode))
