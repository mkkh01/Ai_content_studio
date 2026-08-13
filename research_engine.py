"""Reproducible crypto forecasting research loop with strict temporal evaluation."""
from __future__ import annotations
import argparse, hashlib, json
from dataclasses import asdict, dataclass
from pathlib import Path
import numpy as np
import pandas as pd

@dataclass
class Config:
    iterations: int = 20
    train_ratio: float = .60
    validation_ratio: float = .20
    train_window: int = 720
    validation_window: int = 168
    fee_bps: float = 6.0
    slippage_bps: float = 4.0
    neutral_vol_fraction: float = .25
    bars_per_year: int = 24 * 365
    min_score_observations: int = 20
    seed: int = 42

class ResearchEngine:
    def __init__(self, config: Config):
        self.cfg = config
        self.rng = np.random.default_rng(config.seed)

    def load(self, path: str) -> pd.DataFrame:
        df = pd.read_csv(path)
        required = {'timestamp', 'open', 'high', 'low', 'close', 'volume'}
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f'Missing columns: {sorted(missing)}')
        df = df.copy()
        raw_timestamp = df['timestamp']
        numeric_timestamp = pd.to_numeric(raw_timestamp, errors='coerce')
        if numeric_timestamp.notna().mean() > 0.95:
            magnitude = float(numeric_timestamp.dropna().abs().median())
            unit = 'us' if magnitude > 1e14 else ('ms' if magnitude > 1e11 else 's')
            df['timestamp'] = pd.to_datetime(numeric_timestamp, unit=unit, utc=True, errors='coerce')
        else:
            df['timestamp'] = pd.to_datetime(raw_timestamp, utc=True, errors='coerce')
        for c in ['open', 'high', 'low', 'close', 'volume']:
            df[c] = pd.to_numeric(df[c], errors='coerce')
        df = df.dropna(subset=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df = df.sort_values('timestamp').drop_duplicates('timestamp').set_index('timestamp')
        return df[(df[['open', 'high', 'low', 'close', 'volume']] > 0).all(axis=1)]

    def features(self, df: pd.DataFrame) -> pd.DataFrame:
        x = pd.DataFrame(index=df.index)
        close, ret = df['close'], df['close'].pct_change()
        for n in [1, 3, 6, 12, 24, 48, 96]:
            x[f'ret_{n}'] = close.pct_change(n)
        for n in [6, 12, 24, 48, 96]:
            x[f'vol_{n}'] = ret.rolling(n, min_periods=n).std()
            rolling_mean, rolling_std = close.rolling(n, min_periods=n).mean(), close.rolling(n, min_periods=n).std()
            x[f'z_{n}'] = (close - rolling_mean) / (rolling_std + 1e-12)
            vm, vs = df['volume'].rolling(n, min_periods=n).mean(), df['volume'].rolling(n, min_periods=n).std()
            x[f'volume_z_{n}'] = (df['volume'] - vm) / (vs + 1e-12)
        x['range'] = ((df['high'] - df['low']) / close).clip(-1, 1)
        x['close_location'] = (close - df['low']) / (df['high'] - df['low'] + 1e-12)
        if 'funding_rate' in df:
            x['funding_rate'] = pd.to_numeric(df['funding_rate'], errors='coerce')
        if 'open_interest' in df:
            x['oi_change'] = pd.to_numeric(df['open_interest'], errors='coerce').pct_change()
        return x.replace([np.inf, -np.inf], np.nan).dropna()

    @staticmethod
    def target(df: pd.DataFrame, horizon: int) -> pd.Series:
        # Keep only realizable future returns; never turn missing targets into zero.
        return df['close'].shift(-horizon) / df['close'] - 1

    def score(self, pred: pd.Series, actual: pd.Series, price: pd.Series, threshold: float, horizon: int = 1) -> dict:
        """Score only independent horizon returns; overlapping labels are excluded.

        For a 24-bar target, observations at t, t+24, t+48 ... are evaluated.
        Sharpe is annualized with bars_per_year / horizon, not bars_per_year.
        """
        horizon = max(1, int(horizon))
        z = pd.concat([pred.rename('pred'), actual.rename('actual'), price.rename('price')], axis=1).dropna()
        z = z.iloc[::horizon]
        if len(z) < 2:
            return {'sharpe': -99, 'net_return': -100, 'max_drawdown': -100, 'trades': 0, 'coverage': 0.0, 'observations': len(z)}
        signal = np.where(z['pred'] > threshold, 1, np.where(z['pred'] < -threshold, -1, 0))
        turnover = np.abs(np.diff(np.r_[0, signal]))
        costs = turnover * (self.cfg.fee_bps + self.cfg.slippage_bps) / 10000
        strategy_returns = signal * z['actual'].to_numpy() - costs
        equity = np.cumprod(1 + strategy_returns)
        peak = np.maximum.accumulate(equity)
        drawdown = equity / peak - 1
        active = signal != 0
        sharpe = np.sqrt(self.cfg.bars_per_year / horizon) * np.mean(strategy_returns) / (np.std(strategy_returns) + 1e-12)
        return {
            'sharpe': round(float(sharpe), 4),
            'net_return': round(float((equity[-1] - 1) * 100), 4),
            'max_drawdown': round(float(drawdown.min() * 100), 4),
            'trades': int(turnover.sum()),
            'coverage': round(float(active.mean()), 4),
            'observations': int(len(z)),
        }

    def fit_predict(self, a: np.ndarray, y: np.ndarray, train_slice: slice, pred_slice: slice, lam: float) -> np.ndarray:
        train_x, train_y = a[train_slice], y[train_slice]
        valid = np.isfinite(train_y) & np.isfinite(train_x).all(axis=1)
        train_x, train_y = train_x[valid], train_y[valid]
        if len(train_x) < 5:
            return np.full(len(a[pred_slice]), np.nan)
        mu, sd = train_x.mean(axis=0), train_x.std(axis=0) + 1e-8
        train_x = (train_x - mu) / sd
        pred_x = (a[pred_slice] - mu) / sd
        w = np.linalg.solve(train_x.T @ train_x + lam * np.eye(train_x.shape[1]), train_x.T @ train_y)
        return pred_x @ w

    def candidate(self, X: pd.DataFrame, y: pd.Series, price: pd.Series, horizon: int, i: int) -> dict:
        n = len(X)
        train_end = int(n * self.cfg.train_ratio)
        val_end = int(n * (self.cfg.train_ratio + self.cfg.validation_ratio))
        test_start = val_end + horizon  # purge overlap with validation labels
        if test_start >= n or train_end < 20:
            return {'name': f'RidgeSearch-{i:03d}', 'accepted': False, 'failure': 'insufficient purged temporal rows'}
        val_start = max(train_end, val_end - self.cfg.validation_window)
        window = min(self.cfg.train_window, train_end)
        cols = list(X.columns)
        k = min(len(cols), int(self.rng.integers(5, min(25, len(cols)) + 1)))
        chosen = list(self.rng.choice(cols, size=k, replace=False))
        a, yy = X[chosen].to_numpy(), y.reindex(X.index).to_numpy()
        train_start = train_end - window
        lambdas = [10 ** p for p in np.linspace(-3, 1, 7)]
        val_scores = []
        for lam in lambdas:
            vp = self.fit_predict(a, yy, slice(train_start, train_end), slice(val_start, val_end), lam)
            val_y, val_p = y.reindex(X.index).iloc[val_start:val_end], price.reindex(X.index).iloc[val_start:val_end]
            threshold = 2 * (self.cfg.fee_bps + self.cfg.slippage_bps) / 10000 + self.cfg.neutral_vol_fraction * float(np.nanstd(yy[train_start:train_end]))
            val_scores.append((self.score(pd.Series(vp, index=val_y.index), val_y, val_p, threshold, horizon)['sharpe'], lam, threshold))
        _, best_lam, threshold = max(val_scores, key=lambda t: t[0])
        test_pred = self.fit_predict(a, yy, slice(train_start, train_end), slice(test_start, n), best_lam)
        test_y, test_p = y.reindex(X.index).iloc[test_start:], price.reindex(X.index).iloc[test_start:]
        metrics = self.score(pd.Series(test_pred, index=test_y.index), test_y, test_p, threshold, horizon)
        validation_sharpe = round(max(val_scores)[0], 4)
        accepted = (validation_sharpe > 0 and metrics['sharpe'] > 0.5 and metrics['max_drawdown'] > -35 and metrics['trades'] >= 5 and metrics.get('observations', 0) >= self.cfg.min_score_observations)
        return {
            'name': f'RidgeSearch-{i:03d}', 'features': k, 'horizon': horizon, 'window': window,
            'feature_names': chosen, 'lambda': best_lam, 'neutral_threshold': round(threshold, 8),
            'validation_sharpe': validation_sharpe, 'metrics': metrics, 'accepted': accepted,
            'failure': None if accepted else 'validation/test robustness or trade-count threshold failed',
        }

    def run(self, df: pd.DataFrame, out: str) -> list[dict]:
        outp = Path(out); outp.mkdir(parents=True, exist_ok=True)
        X = self.features(df); results = []
        data_hash = hashlib.sha256(pd.util.hash_pandas_object(df, index=True).values.tobytes()).hexdigest()[:16]
        for i in range(self.cfg.iterations):
            horizon = int(self.rng.choice([1, 3, 6, 12, 24]))
            y = self.target(df, horizon).reindex(X.index)
            result = self.candidate(X, y, df['close'], horizon, i)
            result.update({'config': asdict(self.cfg), 'data_hash': data_hash, 'data_rows': len(df)})
            results.append(result)
            with (outp / 'experiment_log.jsonl').open('a', encoding='utf8') as f:
                f.write(json.dumps(result, ensure_ascii=False) + '\n')
        results.sort(key=lambda r: r.get('metrics', {}).get('sharpe', -99), reverse=True)
        (outp / 'model_registry.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf8')
        summary = {'best': results[0] if results else None, 'experiments': len(results), 'data_rows': len(df), 'feature_count': X.shape[1], 'failure_count': sum(not r['accepted'] for r in results)}
        (outp / 'decision_history.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf8')
        return results

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--csv', required=True); ap.add_argument('--iterations', type=int, default=20); ap.add_argument('--output', default='runs'); args = ap.parse_args()
    engine = ResearchEngine(Config(iterations=args.iterations)); results = engine.run(engine.load(args.csv), args.output)
    print(json.dumps({'experiments': len(results), 'best': results[0] if results else None}, ensure_ascii=False, indent=2))

if __name__ == '__main__': main()
