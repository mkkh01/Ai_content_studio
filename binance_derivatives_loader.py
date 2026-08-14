#!/usr/bin/env python3
"""Download and safely merge Binance USDⓈ-M derivatives data.

The module is intentionally conservative:

* Vision archive files are preferred over live REST endpoints for reproducibility.
* Every source is normalized to a UTC timestamp and deduplicated.
* Features are merged with ``pandas.merge_asof(..., direction='backward')``.
* No source observation after a market bar is allowed into that bar.
* Derived changes and rolling statistics use only current and past observations.

The resulting CSV is suitable as an input to the repository's research engine.
It does not make a model tradable; downstream walk-forward and cost tests remain
mandatory.
"""

from __future__ import annotations

import argparse
import io
import logging
import re
import zipfile
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Optional

import numpy as np
import pandas as pd
import requests

LOG = logging.getLogger("binance_derivatives_loader")
VISION = "https://data.binance.vision/data/futures/um"


@dataclass(frozen=True)
class DownloadConfig:
    symbol: str = "BTCUSDT"
    start: str = "2026-01-01"
    end: str = "2026-07-31"
    interval: str = "1h"
    cache_dir: Path = Path("data/binance_cache")
    timeout_seconds: int = 30

    @property
    def start_date(self) -> date:
        return date.fromisoformat(self.start)

    @property
    def end_date(self) -> date:
        return date.fromisoformat(self.end)


def _days(start: date, end: date) -> Iterable[date]:
    cur = start
    while cur <= end:
        yield cur
        cur += timedelta(days=1)


def _request_zip(url: str, destination: Path, timeout: int) -> Optional[Path]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and destination.stat().st_size > 0:
        return destination
    LOG.info("GET %s", url)
    response = requests.get(url, timeout=timeout, headers={"User-Agent": "research-lab/1.0"})
    if response.status_code == 404:
        return None
    response.raise_for_status()
    destination.write_bytes(response.content)
    return destination


def _archive_candidates(kind: str, cfg: DownloadConfig, day: date) -> list[tuple[str, Path]]:
    symbol = cfg.symbol.upper()
    stamp = day.isoformat()
    # Binance Vision publishes daily files; monthly files are used as a fallback.
    daily_name = f"{symbol}-{kind}-{stamp}.zip"
    monthly_name = f"{symbol}-{kind}-{day:%Y-%m}.zip"
    return [
        (f"{VISION}/daily/{kind}/{symbol}/{daily_name}", cfg.cache_dir / kind / daily_name),
        (f"{VISION}/monthly/{kind}/{symbol}/{monthly_name}", cfg.cache_dir / kind / monthly_name),
    ]


def download_archive_series(kind: str, cfg: DownloadConfig) -> list[Path]:
    """Download daily/monthly Vision archives for ``kind`` and return local paths."""
    found: list[Path] = []
    seen: set[Path] = set()
    for day in _days(cfg.start_date, cfg.end_date):
        for url, path in _archive_candidates(kind, cfg, day):
            if path in seen:
                continue
            seen.add(path)
            try:
                result = _request_zip(url, path, cfg.timeout_seconds)
            except requests.RequestException as exc:
                LOG.warning("Could not download %s: %s", url, exc)
                continue
            if result:
                found.append(result)
                break
    if not found:
        raise FileNotFoundError(
            f"No Binance Vision {kind} archives found for {cfg.symbol} "
            f"between {cfg.start} and {cfg.end}."
        )
    return found


def _read_archives(paths: Iterable[Path]) -> pd.DataFrame:
    frames: list[pd.DataFrame] = []
    for path in paths:
        with zipfile.ZipFile(path) as archive:
            members = [m for m in archive.namelist() if m.lower().endswith(('.csv', '.csv.gz'))]
            if not members:
                LOG.warning("No CSV member in %s", path)
                continue
            for member in members:
                with archive.open(member) as handle:
                    frames.append(pd.read_csv(handle))
    if not frames:
        raise ValueError("Archives contained no CSV data")
    return pd.concat(frames, ignore_index=True)


def _timestamp_column(df: pd.DataFrame) -> str:
    candidates = ["timestamp", "time", "create_time", "calc_time", "fundingTime", "funding_time"]
    for col in candidates:
        if col in df.columns:
            return col
    raise KeyError(f"No timestamp column found; available columns: {list(df.columns)}")


def normalize_timestamp(df: pd.DataFrame, source: str) -> pd.DataFrame:
    out = df.copy()
    col = _timestamp_column(out)
    raw = out[col]
    if pd.api.types.is_numeric_dtype(raw):
        unit = "us" if raw.dropna().abs().median() > 10**14 else "ms"
        out["timestamp"] = pd.to_datetime(raw, unit=unit, utc=True, errors="coerce").astype("datetime64[ns, UTC]")
    else:
        out["timestamp"] = pd.to_datetime(raw, utc=True, errors="coerce").astype("datetime64[ns, UTC]")
    out = out.dropna(subset=["timestamp"]).sort_values("timestamp")
    out = out.drop_duplicates("timestamp", keep="last").reset_index(drop=True)
    out["source"] = source
    return out


def _numeric(df: pd.DataFrame, *names: str) -> Optional[pd.Series]:
    lowered = {str(c).lower().replace(" ", "_"): c for c in df.columns}
    for name in names:
        c = lowered.get(name.lower().replace(" ", "_"))
        if c is not None:
            return pd.to_numeric(df[c], errors="coerce")
    return None


def normalize_funding(raw: pd.DataFrame) -> pd.DataFrame:
    df = normalize_timestamp(raw, "binance_vision_funding")
    rate = _numeric(df, "funding_rate", "fundingrate", "last_funding_rate")
    if rate is None:
        raise KeyError("Funding archive has no funding rate column")
    out = pd.DataFrame({"timestamp": df.timestamp, "funding_rate": rate})
    return out.dropna(subset=["funding_rate"]).drop_duplicates("timestamp").sort_values("timestamp")


def normalize_metrics(raw: pd.DataFrame) -> pd.DataFrame:
    """Normalize Vision metrics, including OI and available taker ratio fields."""
    df = normalize_timestamp(raw, "binance_vision_metrics")
    oi = _numeric(df, "sum_open_interest", "open_interest", "openinterest")
    oi_value = _numeric(df, "sum_open_interest_value", "open_interest_value")
    # Metrics archives commonly expose a taker long/short volume ratio rather
    # than raw buy/sell volumes. Keep it under an explicit proxy name.
    taker_ratio = _numeric(
        df,
        "sum_taker_long_short_vol_ratio",
        "taker_buy_sell_ratio",
        "buy_sell_ratio",
    )
    out = pd.DataFrame({"timestamp": df.timestamp})
    if oi is not None:
        out["oi_contracts"] = oi
    if oi_value is not None:
        out["oi_value"] = oi_value
    if taker_ratio is not None:
        out["taker_buy_sell_ratio"] = taker_ratio
    if len(out.columns) == 1:
        raise KeyError(f"Metrics archive has no recognized OI/order-flow columns: {list(df.columns)}")
    return out.drop_duplicates("timestamp").sort_values("timestamp")


def normalize_order_flow(raw: pd.DataFrame) -> pd.DataFrame:
    """Normalize a raw takerBuySellVol file or REST response.

    Accepted columns include ``buyVol``, ``sellVol``, ``buy_volume`` and
    ``sell_volume``. A ratio-only source is accepted as a proxy and is clearly
    named ``taker_buy_sell_ratio``.
    """
    df = normalize_timestamp(raw, "binance_taker_buy_sell")
    buy = _numeric(df, "buyVol", "buy_volume", "taker_buy_volume", "taker_buy_vol")
    sell = _numeric(df, "sellVol", "sell_volume", "taker_sell_volume", "taker_sell_vol")
    ratio = _numeric(df, "buySellRatio", "buy_sell_ratio", "taker_buy_sell_ratio")
    out = pd.DataFrame({"timestamp": df.timestamp})
    if buy is not None:
        out["taker_buy_volume"] = buy
    if sell is not None:
        out["taker_sell_volume"] = sell
    if ratio is not None:
        out["taker_buy_sell_ratio"] = ratio
    if "taker_buy_volume" in out and "taker_sell_volume" in out:
        denom = out["taker_sell_volume"].replace(0, np.nan)
        out["taker_buy_sell_ratio"] = out["taker_buy_volume"] / denom
    if len(out.columns) == 1:
        raise KeyError(f"Order-flow source has no recognized columns: {list(df.columns)}")
    return out.drop_duplicates("timestamp").sort_values("timestamp")


def _load_source(path: Path) -> pd.DataFrame:
    if path.suffix == ".zip":
        return _read_archives([path])
    if path.suffix == ".gz":
        return pd.read_csv(path, compression="gzip")
    return pd.read_csv(path)


def derive_features(df: pd.DataFrame) -> pd.DataFrame:
    out = df.sort_values("timestamp").copy()
    for col in ["funding_rate", "oi_contracts", "oi_value", "taker_buy_volume", "taker_sell_volume", "taker_buy_sell_ratio"]:
        if col in out:
            out[col] = pd.to_numeric(out[col], errors="coerce")
    for col in ["oi_contracts", "oi_value", "taker_buy_volume", "taker_sell_volume", "taker_buy_sell_ratio"]:
        if col in out:
            safe = out[col].replace(0, np.nan)
            out[f"{col}_change"] = out[col].pct_change(fill_method=None).replace([np.inf, -np.inf], np.nan)
            out[f"{col}_z20"] = (out[col] - out[col].rolling(20, min_periods=20).mean()) / out[col].rolling(20, min_periods=20).std(ddof=0)
    if "funding_rate" in out:
        out["funding_change"] = out["funding_rate"].diff()
        out["funding_8h_sum"] = out["funding_rate"].rolling(8, min_periods=1).sum()
    if {"taker_buy_volume", "taker_sell_volume"}.issubset(out.columns):
        total = (out["taker_buy_volume"] + out["taker_sell_volume"]).replace(0, np.nan)
        out["taker_imbalance"] = (out["taker_buy_volume"] - out["taker_sell_volume"]) / total
    elif "taker_buy_sell_ratio" in out:
        out["taker_imbalance"] = (out["taker_buy_sell_ratio"] - 1.0) / (out["taker_buy_sell_ratio"] + 1.0)
    return out


def safe_asof_merge(bars: pd.DataFrame, sources: list[pd.DataFrame], tolerance: str = "8h") -> pd.DataFrame:
    """Backward merge source observations into bars without look-ahead."""
    if "timestamp" not in bars.columns:
        raise KeyError("Bars must contain timestamp")
    result = bars.copy()
    result["timestamp"] = pd.to_datetime(result["timestamp"], utc=True).astype("datetime64[ns, UTC]")
    result = result.sort_values("timestamp").drop_duplicates("timestamp")
    for i, source in enumerate(sources, start=1):
        right = source.copy()
        right["timestamp"] = pd.to_datetime(right["timestamp"], utc=True).astype("datetime64[ns, UTC]")
        right = right.sort_values("timestamp").drop_duplicates("timestamp")
        audit_col = f"source_timestamp_{i}"
        right = right.rename(columns={"timestamp": audit_col})
        result = pd.merge_asof(result, right, left_on="timestamp", right_on=audit_col, direction="backward", tolerance=pd.Timedelta(tolerance), suffixes=("", "_source"))
    return derive_features(result)


def assert_no_lookahead(merged: pd.DataFrame, source_timestamps: list[pd.Series]) -> None:
    """Fail loudly if retained provenance timestamps are after their market bar."""
    bar_time = pd.to_datetime(merged["timestamp"], utc=True)
    audit_cols = [c for c in merged.columns if c.startswith("source_timestamp_")]
    if len(audit_cols) != len(source_timestamps):
        raise AssertionError("Expected one retained source timestamp column per source")
    for col in audit_cols:
        source_time = pd.to_datetime(merged[col], utc=True)
        bad = source_time.notna() & (source_time > bar_time)
        if bad.any():
            raise AssertionError(f"Look-ahead detected in {col}: source timestamp is after bar timestamp")


def load_and_merge(bars_path: Path, funding_path: Optional[Path], metrics_path: Optional[Path], order_flow_path: Optional[Path], tolerance: str) -> pd.DataFrame:
    bars = pd.read_csv(bars_path)
    sources: list[pd.DataFrame] = []
    source_ts: list[pd.Series] = []
    if funding_path:
        funding = normalize_funding(_load_source(funding_path)); sources.append(funding); source_ts.append(funding.timestamp)
    if metrics_path:
        metrics = normalize_metrics(_load_source(metrics_path)); sources.append(metrics); source_ts.append(metrics.timestamp)
    if order_flow_path:
        flow = normalize_order_flow(_load_source(order_flow_path)); sources.append(flow); source_ts.append(flow.timestamp)
    merged = safe_asof_merge(bars, sources, tolerance=tolerance)
    assert_no_lookahead(merged, source_ts)
    return merged


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bars", required=True, type=Path, help="OHLCV CSV with timestamp column")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--funding", type=Path, help="Local funding CSV/ZIP; if omitted download Vision")
    parser.add_argument("--metrics", type=Path, help="Local metrics CSV/ZIP with OI; if omitted download Vision")
    parser.add_argument("--order-flow", type=Path, help="Local taker buy/sell CSV/ZIP")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--start", default="2026-01-01")
    parser.add_argument("--end", default="2026-07-31")
    parser.add_argument("--cache-dir", type=Path, default=Path("data/binance_cache"))
    parser.add_argument("--tolerance", default="8h", help="Maximum age of a source observation")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    cfg = DownloadConfig(args.symbol, args.start, args.end, cache_dir=args.cache_dir)
    funding = args.funding
    metrics = args.metrics
    if funding is None:
        funding_paths = download_archive_series("fundingRate", cfg)
        funding = funding_paths[0] if len(funding_paths) == 1 else None
        if funding is None:
            raw = normalize_funding(_read_archives(funding_paths))
        else:
            raw = normalize_funding(_load_source(funding))
    else:
        raw = normalize_funding(_load_source(funding))
    funding_frame = raw
    metrics_frame = None
    if metrics is None:
        metrics_paths = download_archive_series("metrics", cfg)
        metrics_frame = normalize_metrics(_read_archives(metrics_paths))
    else:
        metrics_frame = normalize_metrics(_load_source(metrics))
    bars = pd.read_csv(args.bars)
    sources = [funding_frame, metrics_frame]
    if args.order_flow:
        sources.append(normalize_order_flow(_load_source(args.order_flow)))
    merged = safe_asof_merge(bars, sources, args.tolerance)
    assert_no_lookahead(merged, [s.timestamp for s in sources])
    args.output.parent.mkdir(parents=True, exist_ok=True)
    merged.to_csv(args.output, index=False)
    print(f"wrote {len(merged):,} rows x {len(merged.columns):,} columns to {args.output}")
    print("features:", ", ".join(c for c in merged.columns if c.startswith(("funding_", "oi_", "taker_"))))


if __name__ == "__main__":
    main()
