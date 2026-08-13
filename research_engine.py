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
    risk_enabled: bool = True
    atr_stop_mult: float = 2.0
    atr_trail_mult: float = 2.5
    min_stop_pct: float = 0.001
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

        # Advanced volatility features. All rolling statistics use only past/current bars.
        log_hl = np.log((df['high'] + 1e-12) / (df['low'] + 1e-12))
        log_co = np.log((close + 1e-12) / (df['open'] + 1e-12))
        true_range = pd.concat([
            df['high'] - df['low'],
            (df['high'] - close.shift(1)).abs(),
            (df['low'] - close.shift(1)).abs(),
        ], axis=1).max(axis=1)
        for n in [6, 12, 24, 48, 96]:
            atr = true_range.rolling(n, min_periods=n).mean() / (close + 1e-12)
            parkinson = np.sqrt((log_hl.pow(2).rolling(n, min_periods=n).mean()) / (4 * np.log(2)))
            gk_term = (0.5 * log_hl.pow(2) - (2 * np.log(2) - 1) * log_co.pow(2)).clip(lower=0)
            garman_klass = np.sqrt(gk_term.rolling(n, min_periods=n).mean())
            realized = ret.pow(2).rolling(n, min_periods=n).sum().pow(0.5)
            x[f'vol_adv_atr_{n}'] = atr
            x[f'vol_adv_parkinson_{n}'] = parkinson
            x[f'vol_adv_gk_{n}'] = garman_klass
            x[f'vol_adv_realized_{n}'] = realized
            x[f'vol_adv_ratio_{n}'] = realized / (realized.rolling(max(2, n * 4), min_periods=max(2, n * 4)).mean() + 1e-12)
        if 'funding_rate' in df:
            x['funding_rate'] = pd.to_numeric(df['funding_rate'], errors='coerce')
        if 'open_interest' in df:
            x['oi_change'] = pd.to_numeric(df['open_interest'], errors='coerce').pct_change()
        return x.replace([np.inf, -np.inf], np.nan).dropna()

    @staticmethod
    def target(df: pd.DataFrame, horizon: int) -> pd.Series:
        # Keep only realizable future returns; never turn missing targets into zero.
        return df['close'].shift(-horizon) / df['close'] - 1

    def score(self, pred: pd.Series, actual: pd.Series, price: pd.Series, threshold: float, horizon: int = 1, high: pd.Series | None = None, low: pd.Series | None = None) -> dict:
        """Score independent trades with an optional ATR initial/trailing stop.

        Entries are sampled every ``horizon`` bars, so labels do not overlap. When
        OHLC is supplied, each trade is walked bar by bar using only information
        available at entry and subsequent bars; no future close is used to set a stop.
        """
        horizon = max(1, int(horizon))
        parts = [pred.rename('pred'), actual.rename('actual'), price.rename('price')]
        if high is not None and low is not None:
            parts += [high.rename('high'), low.rename('low')]
        z = pd.concat(parts, axis=1).dropna()
        if len(z) < 2:
            return {'sharpe': -99, 'net_return': -100, 'max_drawdown': -100, 'trades': 0, 'coverage': 0.0, 'observations': len(z), 'stop_exits': 0, 'avg_hold_bars': 0.0}
        entries = z.iloc[::horizon]
        gross_returns, trade_costs, signals, stop_exits, holds = [], [], [], 0, []
        tr = (z['high'] - z['low']).combine((z['high'] - z['price'].shift(1)).abs(), max).combine((z['low'] - z['price'].shift(1)).abs(), max) if {'high','low'}.issubset(z.columns) else None
        atr_series = tr.rolling(24, min_periods=2).mean() if tr is not None else None
        for label, row in entries.iterrows():
            signal = 1 if row['pred'] > threshold else (-1 if row['pred'] < -threshold else 0)
            signals.append(signal)
            if signal == 0:
                gross_returns.append(0.0); trade_costs.append(0.0); holds.append(0); continue
            entry_pos = z.index.get_loc(label); entry = float(row['price']); end_pos = min(entry_pos + horizon, len(z) - 1)
            atr = float(atr_series.iloc[entry_pos]) if atr_series is not None and np.isfinite(atr_series.iloc[entry_pos]) else entry * self.cfg.min_stop_pct
            stop_dist = max(atr * self.cfg.atr_stop_mult, entry * self.cfg.min_stop_pct)
            trail_dist = max(atr * self.cfg.atr_trail_mult, entry * self.cfg.min_stop_pct)
            exit_price = float(z['price'].iloc[end_pos]); held = end_pos - entry_pos; stopped = False
            if self.cfg.risk_enabled and {'high','low'}.issubset(z.columns):
                peak = entry; trough = entry
                for pos in range(entry_pos + 1, end_pos + 1):
                    bar_high, bar_low = float(z['high'].iloc[pos]), float(z['low'].iloc[pos])
                    if signal == 1:
                        peak = max(peak, bar_high); stop = max(entry - stop_dist, peak - trail_dist)
                        if bar_low <= stop: exit_price, held, stopped = stop, pos - entry_pos, True; break
                    else:
                        trough = min(trough, bar_low); stop = min(entry + stop_dist, trough + trail_dist)
                        if bar_high >= stop: exit_price, held, stopped = stop, pos - entry_pos, True; break
            gross_returns.append(signal * (exit_price / entry - 1)); trade_costs.append((self.cfg.fee_bps + self.cfg.slippage_bps) / 10000); holds.append(held); stop_exits += int(stopped)
        strategy_returns = np.asarray(gross_returns) - np.asarray(trade_costs)
        equity = np.cumprod(1 + strategy_returns); peak_eq = np.maximum.accumulate(equity); drawdown = equity / peak_eq - 1
        active = np.asarray(signals) != 0; sharpe = np.sqrt(self.cfg.bars_per_year / horizon) * np.mean(strategy_returns) / (np.std(strategy_returns) + 1e-12)
        return {'sharpe': round(float(sharpe), 4), 'net_return': round(float((equity[-1] - 1) * 100), 4), 'max_drawdown': round(float(drawdown.min() * 100), 4), 'trades': int(active.sum()), 'coverage': round(float(active.mean()), 4), 'observations': int(len(entries)), 'stop_exits': int(stop_exits), 'avg_hold_bars': round(float(np.mean([h for h, s in zip(holds, active) if s]) if active.any() else 0), 4)}

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

    def candidate(self, X: pd.DataFrame, y: pd.Series, price: pd.Series, horizon: int, i: int, high: pd.Series | None = None, low: pd.Series | None = None) -> dict:
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
            val_scores.append((self.score(pd.Series(vp, index=val_y.index), val_y, val_p, threshold, horizon, high.reindex(X.index).iloc[val_start:val_end] if high is not None else None, low.reindex(X.index).iloc[val_start:val_end] if low is not None else None)['sharpe'], lam, threshold))
        _, best_lam, threshold = max(val_scores, key=lambda t: t[0])
        test_pred = self.fit_predict(a, yy, slice(train_start, train_end), slice(test_start, n), best_lam)
        test_y, test_p = y.reindex(X.index).iloc[test_start:], price.reindex(X.index).iloc[test_start:]
        metrics = self.score(pd.Series(test_pred, index=test_y.index), test_y, test_p, threshold, horizon, high.reindex(X.index).iloc[test_start:] if high is not None else None, low.reindex(X.index).iloc[test_start:] if low is not None else None)
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
            result = self.candidate(X, y, df['close'], horizon, i, df['high'], df['low'])
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
