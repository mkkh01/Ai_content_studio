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
    risk_per_trade: float = 0.0025
    max_position_size: float = 1.0
    time_stop_fraction: float = 0.5
    breakeven_trigger_atr: float = 1.0
    breakeven_offset_bps: float = 0.0
    walk_forward_windows: int = 4
    composite_min_score: float = 0.25
    min_window_sharpe: float = -0.5
    feature_mode: str = 'liquidity'
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

        # Alternative feature families outside regime classification.
        for n in [4, 12, 24, 48]:
            rv = ret.rolling(n, min_periods=n).std()
            x[f'alt_norm_ret_{n}'] = close.pct_change(n) / (rv * np.sqrt(n) + 1e-12)
            x[f'alt_return_consistency_{n}'] = ret.rolling(n, min_periods=n).mean() / (ret.abs().rolling(n, min_periods=n).mean() + 1e-12)
            x[f'alt_positive_fraction_{n}'] = (ret > 0).rolling(n, min_periods=n).mean()
            x[f'alt_downside_semivar_{n}'] = ret.where(ret < 0, 0).pow(2).rolling(n, min_periods=n).mean().pow(0.5)
            x[f'alt_upside_semivar_{n}'] = ret.where(ret > 0, 0).pow(2).rolling(n, min_periods=n).mean().pow(0.5)
            roll_high, roll_low = close.rolling(n, min_periods=n).max(), close.rolling(n, min_periods=n).min()
            x[f'alt_range_position_{n}'] = (close - roll_low) / (roll_high - roll_low + 1e-12)
            typical = (df['high'] + df['low'] + close) / 3
            vwap = (typical * df['volume']).rolling(n, min_periods=n).sum() / (df['volume'].rolling(n, min_periods=n).sum() + 1e-12)
            x[f'alt_vwap_distance_{n}'] = close / (vwap + 1e-12) - 1
        dollar_volume = close * df['volume']
        x['alt_dollar_volume_percentile'] = dollar_volume.rolling(48, min_periods=48).rank(pct=True)
        x['alt_illiquidity'] = ret.abs() / (dollar_volume + 1e-12)
        x['alt_volume_concentration'] = df['volume'].rolling(24, min_periods=24).max() / (df['volume'].rolling(24, min_periods=24).sum() + 1e-12)

        # Advanced volatility features. All rolling statistics use only past/current bars.
        log_hl = np.log((df['high'] + 1e-12) / (df['low'] + 1e-12))
        log_co = np.log((close + 1e-12) / (df['open'] + 1e-12))
        true_range = pd.concat([
            df['high'] - df['low'],
            (df['high'] - close.shift(1)).abs(),
            (df['low'] - close.shift(1)).abs(),
        ], axis=1).max(axis=1)
        x['alt_cost_to_range'] = ((self.cfg.fee_bps + self.cfg.slippage_bps) / 10000) / (true_range / (close + 1e-12) + 1e-12)

        # Classical technical features, calculated from current and past bars only.
        for n in [7, 14, 28]:
            delta = close.diff()
            gain = delta.clip(lower=0).rolling(n, min_periods=n).mean()
            loss = (-delta.clip(upper=0)).rolling(n, min_periods=n).mean()
            rs = gain / (loss + 1e-12)
            x[f'ta_rsi_{n}'] = (100 - (100 / (1 + rs))) / 100.0
            x[f'ta_atr_pct_{n}'] = true_range.rolling(n, min_periods=n).mean() / (close + 1e-12)
            x[f'ta_atr_ratio_{n}'] = x[f'ta_atr_pct_{n}'] / (x[f'vol_adv_atr_{min(n, 96)}'] + 1e-12) if f'vol_adv_atr_{min(n, 96)}' in x else x[f'ta_atr_pct_{n}']
        ema12 = close.ewm(span=12, adjust=False, min_periods=12).mean()
        ema26 = close.ewm(span=26, adjust=False, min_periods=26).mean()
        macd = ema12 - ema26
        macd_signal = macd.ewm(span=9, adjust=False, min_periods=9).mean()
        x['ta_macd_pct'] = macd / (close + 1e-12)
        x['ta_macd_signal_pct'] = macd_signal / (close + 1e-12)
        x['ta_macd_hist_pct'] = (macd - macd_signal) / (close + 1e-12)
        x['ta_rsi_centered'] = x['ta_rsi_14'] - 0.5

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
        # Trend, regime and multi-timeframe features; all use data available up to t.
        for fast, slow in [(6, 24), (12, 48), (24, 96)]:
            ema_fast = close.ewm(span=fast, adjust=False, min_periods=fast).mean()
            ema_slow = close.ewm(span=slow, adjust=False, min_periods=slow).mean()
            x[f'trend_ema_gap_{fast}_{slow}'] = ema_fast / (ema_slow + 1e-12) - 1
            x[f'trend_ema_slope_{fast}'] = ema_fast.pct_change(fast)
        directional = (close.diff().rolling(14, min_periods=14).mean() / (ret.abs().rolling(14, min_periods=14).mean() + 1e-12)).clip(-5, 5)
        x['trend_directional_efficiency'] = directional
        x['trend_adx_proxy'] = (df['high'].diff().clip(lower=0).rolling(14, min_periods=14).mean() + (-df['low'].diff()).clip(lower=0).rolling(14, min_periods=14).mean()) / (true_range.rolling(14, min_periods=14).mean() + 1e-12)
        for n in [24, 96, 288]:
            x[f'mtf_ret_{n}'] = close.pct_change(n)
            x[f'mtf_vol_{n}'] = ret.rolling(n, min_periods=n).std()
        regime_score = x['trend_ema_gap_12_48'].fillna(0) / (x['vol_24'].fillna(0) + 1e-12)
        x['regime_trend_score'] = regime_score.clip(-10, 10)
        x['regime_high_vol'] = (x['vol_24'] > x['vol_24'].rolling(96, min_periods=24).median()).astype(float)
        x['regime_sideways'] = (x['trend_directional_efficiency'].abs() < 0.35).astype(float)
        # Regime-conditioned interactions let the linear model use different
        # responses for trend continuation versus mean-reversion conditions.
        x['regime_up_mask'] = (x['regime_trend_score'] > 0.5).astype(float)
        x['regime_down_mask'] = (x['regime_trend_score'] < -0.5).astype(float)
        x['regime_trend_momentum'] = x['regime_trend_score'] * x['ret_24']
        x['regime_sideways_reversion'] = x['regime_sideways'] * x['z_24']
        x['regime_highvol_return'] = x['regime_high_vol'] * x['ret_6']
        if 'funding_rate' in df:
            x['funding_rate'] = pd.to_numeric(df['funding_rate'], errors='coerce')
        if 'open_interest' in df:
            x['oi_change'] = pd.to_numeric(df['open_interest'], errors='coerce').pct_change()
        x = x.replace([np.inf, -np.inf], np.nan).dropna()
        base = [c for c in x.columns if not (c.startswith('trend_') or c.startswith('mtf_') or c.startswith('regime_') or c.startswith('alt_') or c.startswith('ta_'))]
        core = [c for c in x.columns if c in {'trend_ema_gap_12_48','trend_ema_slope_12','trend_directional_efficiency','trend_adx_proxy','mtf_ret_96','mtf_vol_96','regime_trend_score','regime_high_vol','regime_sideways'}]
        alt_return = [c for c in x.columns if any(c.startswith(f'alt_{p}') for p in ['norm_ret_','return_consistency_','positive_fraction_','downside_semivar_','upside_semivar_'])]
        alt_reversion = [c for c in x.columns if c.startswith('alt_range_position_') or c.startswith('alt_vwap_distance_')]
        alt_liquidity = [c for c in x.columns if c in {'alt_dollar_volume_percentile','alt_illiquidity','alt_volume_concentration','alt_cost_to_range'}]
        if self.cfg.feature_mode == 'core_regime': keep = base + core
        elif self.cfg.feature_mode == 'return_path': keep = base + alt_return
        elif self.cfg.feature_mode == 'reversion': keep = base + alt_reversion
        elif self.cfg.feature_mode == 'liquidity': keep = base + alt_liquidity
        elif self.cfg.feature_mode == 'technical': keep = base + [c for c in x.columns if c.startswith('ta_')]
        elif self.cfg.feature_mode == 'minimal_technical': keep = base + ['ta_rsi_14', 'ta_macd_hist_pct']
        elif self.cfg.feature_mode == 'return_reversion': keep = base + alt_return + alt_reversion
        elif self.cfg.feature_mode == 'return_liquidity': keep = base + alt_return + alt_liquidity
        elif self.cfg.feature_mode == 'alternative_full': keep = base + alt_return + alt_reversion + alt_liquidity
        elif self.cfg.feature_mode == 'baseline': keep = base
        elif self.cfg.feature_mode == 'full': keep = list(x.columns)
        else: keep = base + core
        return x[sorted(set(keep))]

    @staticmethod
    def target(df: pd.DataFrame, horizon: int) -> pd.Series:
        # Keep only realizable future returns; never turn missing targets into zero.
        return df['close'].shift(-horizon) / df['close'] - 1

    def score(self, pred: pd.Series, actual: pd.Series, price: pd.Series, threshold: float, horizon: int = 1, high: pd.Series | None = None, low: pd.Series | None = None) -> dict:
        """Score independent trades with ATR sizing, trailing/breakeven/time stops."""
        horizon = max(1, int(horizon))
        parts = [pred.rename('pred'), actual.rename('actual'), price.rename('price')]
        if high is not None and low is not None: parts += [high.rename('high'), low.rename('low')]
        z = pd.concat(parts, axis=1).dropna()
        if len(z) < 2:
            return {'sharpe': -99, 'net_return': -100, 'max_drawdown': -100, 'trades': 0, 'coverage': 0.0, 'observations': len(z), 'stop_exits': 0, 'time_exits': 0, 'breakeven_exits': 0, 'avg_hold_bars': 0.0, 'avg_position_size': 0.0}
        entries = z.iloc[::horizon]
        gross_returns, trade_costs, signals, stop_exits, time_exits, breakeven_exits, holds, sizes = [], [], [], 0, 0, 0, [], []
        tr = (z['high'] - z['low']).combine((z['high'] - z['price'].shift(1)).abs(), max).combine((z['low'] - z['price'].shift(1)).abs(), max) if {'high','low'}.issubset(z.columns) else None
        atr_series = tr.rolling(24, min_periods=2).mean() if tr is not None else None
        for label, row in entries.iterrows():
            signal = 1 if row['pred'] > threshold else (-1 if row['pred'] < -threshold else 0); signals.append(signal)
            if signal == 0:
                gross_returns.append(0.0); trade_costs.append(0.0); holds.append(0); sizes.append(0.0); continue
            entry_pos = z.index.get_loc(label); entry = float(row['price']); max_hold = max(1, int(round(horizon * self.cfg.time_stop_fraction)))
            end_pos = min(entry_pos + max_hold, len(z) - 1)
            atr = float(atr_series.iloc[entry_pos]) if atr_series is not None and np.isfinite(atr_series.iloc[entry_pos]) else entry * self.cfg.min_stop_pct
            stop_dist = max(atr * self.cfg.atr_stop_mult, entry * self.cfg.min_stop_pct); trail_dist = max(atr * self.cfg.atr_trail_mult, entry * self.cfg.min_stop_pct)
            size = min(self.cfg.max_position_size, self.cfg.risk_per_trade / max(stop_dist / entry, 1e-9)); sizes.append(size)
            exit_price = float(z['price'].iloc[end_pos]); held = end_pos - entry_pos; stopped = timed = breakeven = False; peak = entry; trough = entry; stop = entry - signal * stop_dist
            if self.cfg.risk_enabled and {'high','low'}.issubset(z.columns):
                for pos in range(entry_pos + 1, end_pos + 1):
                    bar_high, bar_low = float(z['high'].iloc[pos]), float(z['low'].iloc[pos])
                    if signal == 1:
                        peak = max(peak, bar_high); stop = max(entry - stop_dist, peak - trail_dist)
                        if peak >= entry + self.cfg.breakeven_trigger_atr * atr: stop = max(stop, entry * (1 + self.cfg.breakeven_offset_bps / 10000)); breakeven = True
                        if bar_low <= stop: exit_price, held, stopped = stop, pos - entry_pos, True; break
                    else:
                        trough = min(trough, bar_low); stop = min(entry + stop_dist, trough + trail_dist)
                        if trough <= entry - self.cfg.breakeven_trigger_atr * atr: stop = min(stop, entry * (1 - self.cfg.breakeven_offset_bps / 10000)); breakeven = True
                        if bar_high >= stop: exit_price, held, stopped = stop, pos - entry_pos, True; break
                if not stopped and end_pos == min(entry_pos + max_hold, len(z) - 1): timed = True
            gross_returns.append(size * signal * (exit_price / entry - 1)); trade_costs.append(size * (self.cfg.fee_bps + self.cfg.slippage_bps) / 10000); holds.append(held); stop_exits += int(stopped); time_exits += int(timed and not stopped); breakeven_exits += int(breakeven and stopped)
        strategy_returns = np.asarray(gross_returns) - np.asarray(trade_costs); equity = np.cumprod(1 + strategy_returns); peak_eq = np.maximum.accumulate(equity); drawdown = equity / peak_eq - 1
        active = np.asarray(signals) != 0; sharpe = np.sqrt(self.cfg.bars_per_year / horizon) * np.mean(strategy_returns) / (np.std(strategy_returns) + 1e-12)
        return {'sharpe': round(float(sharpe), 4), 'net_return': round(float((equity[-1] - 1) * 100), 4), 'max_drawdown': round(float(drawdown.min() * 100), 4), 'trades': int(active.sum()), 'coverage': round(float(active.mean()), 4), 'observations': int(len(entries)), 'stop_exits': int(stop_exits), 'time_exits': int(time_exits), 'breakeven_exits': int(breakeven_exits), 'avg_hold_bars': round(float(np.mean([h for h, s in zip(holds, active) if s]) if active.any() else 0), 4), 'avg_position_size': round(float(np.mean([s for s, a in zip(sizes, active) if a]) if active.any() else 0), 4)}

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
        return {
            'name': f'RidgeSearch-{i:03d}', 'features': k, 'horizon': horizon, 'window': window,
            'feature_names': chosen, 'lambda': best_lam, 'neutral_threshold': round(threshold, 8),
            'validation_sharpe': validation_sharpe, 'metrics': metrics,
            'failure': 'single-window metrics retained for diagnostics',
        }

    def walk_forward_metrics(self, X: pd.DataFrame, y: pd.Series, price: pd.Series, high: pd.Series, low: pd.Series, horizon: int, chosen: list[str], lam: float, threshold: float) -> dict:
        """Evaluate fixed features/parameters over independent forward windows."""
        n = len(X); fold = max(48, int(n * 0.12)); a = X[chosen].to_numpy(); yy = y.reindex(X.index).to_numpy()
        train_window = min(self.cfg.train_window, max(24, int(n * .45))); windows = []
        for w in range(self.cfg.walk_forward_windows):
            test_start = int(n * (.48 + w * .12)) + horizon; test_end = min(test_start + fold, n)
            train_end = test_start - horizon; train_start = max(0, train_end - train_window)
            if test_end - test_start < max(3, horizon): continue
            pred = self.fit_predict(a, yy, slice(train_start, train_end), slice(test_start, test_end), lam)
            sy = y.reindex(X.index).iloc[test_start:test_end]; sp = price.reindex(X.index).iloc[test_start:test_end]
            sh = high.reindex(X.index).iloc[test_start:test_end]; sl = low.reindex(X.index).iloc[test_start:test_end]
            metric = self.score(pd.Series(pred, index=sy.index), sy, sp, threshold, horizon, sh, sl)
            windows.append({'window': w + 1, 'test_start': str(X.index[test_start]), 'test_end': str(X.index[test_end - 1]), **metric})
        if not windows: return {'windows': [], 'composite_score': -99, 'median_sharpe': -99, 'std_sharpe': 99, 'positive_windows': 0, 'mean_return': -100, 'mean_trades': 0}
        wd = pd.DataFrame(windows); median_sharpe = float(wd.sharpe.median()); std_sharpe = float(wd.sharpe.std(ddof=0)); mean_return = float(wd.net_return.mean()); composite = median_sharpe - .5 * std_sharpe + .25 * mean_return - (0.25 if wd.trades.mean() < 5 else 0)
        return {'windows': windows, 'composite_score': round(composite, 4), 'median_sharpe': round(median_sharpe, 4), 'std_sharpe': round(std_sharpe, 4), 'min_sharpe': round(float(wd.sharpe.min()), 4), 'positive_windows': int((wd.sharpe > 0).sum()), 'mean_return': round(mean_return, 4), 'mean_trades': round(float(wd.trades.mean()), 4), 'mean_drawdown': round(float(wd.max_drawdown.mean()), 4)}

    def run(self, df: pd.DataFrame, out: str) -> list[dict]:
        outp = Path(out); outp.mkdir(parents=True, exist_ok=True); X = self.features(df); results = []
        data_hash = hashlib.sha256(pd.util.hash_pandas_object(df, index=True).values.tobytes()).hexdigest()[:16]
        for i in range(self.cfg.iterations):
            horizon = int(self.rng.choice([1, 3, 6, 12, 24])); y = self.target(df, horizon).reindex(X.index)
            result = self.candidate(X, y, df['close'], horizon, i, df['high'], df['low'])
            if 'feature_names' in result:
                wf = self.walk_forward_metrics(X, y, df['close'], df['high'], df['low'], horizon, result['feature_names'], result['lambda'], result['neutral_threshold'])
                result['walk_forward'] = wf; result['composite_score'] = wf['composite_score']
                result['accepted'] = (len(wf['windows']) >= 3 and wf['composite_score'] > self.cfg.composite_min_score and wf['min_sharpe'] > self.cfg.min_window_sharpe and wf['positive_windows'] >= 3 and wf['mean_trades'] >= 5)
                result['failure'] = None if result['accepted'] else 'composite walk-forward criteria failed'
            result.update({'config': asdict(self.cfg), 'data_hash': data_hash, 'data_rows': len(df)}); results.append(result)
            with (outp / 'experiment_log.jsonl').open('a', encoding='utf8') as f: f.write(json.dumps(result, ensure_ascii=False) + '\n')
        results.sort(key=lambda r: r.get('composite_score', -99), reverse=True)
        (outp / 'model_registry.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf8')
        summary = {'best': results[0] if results else None, 'experiments': len(results), 'data_rows': len(df), 'feature_count': X.shape[1], 'failure_count': sum(not r['accepted'] for r in results), 'acceptance_rule': 'composite_score > threshold, >=3 positive windows, min window Sharpe, mean trades'}
        (outp / 'decision_history.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf8')
        return results

def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--csv', required=True); ap.add_argument('--iterations', type=int, default=20); ap.add_argument('--output', default='runs'); args = ap.parse_args()
    engine = ResearchEngine(Config(iterations=args.iterations)); results = engine.run(engine.load(args.csv), args.output)
    print(json.dumps({'experiments': len(results), 'best': results[0] if results else None}, ensure_ascii=False, indent=2))

if __name__ == '__main__': main()
