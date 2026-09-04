"""
Fetches real historical price data (Binance public REST API, no API key
required) and prepares it for replay inside MarketSimulation.

This module only touches data acquisition and basic statistics -- it does
not change the Avellaneda-Stoikov math or the order book at all.
"""
import requests
import numpy as np
import pandas as pd

BINANCE_KLINES_URL = "https://api.binance.com/api/v3/klines"


def fetch_binance_klines(symbol: str = "BTCUSDT", interval: str = "1m",
                          limit: int = 1000) -> pd.DataFrame:
    """
    Fetch recent historical candles from Binance's public market-data API.
    No authentication needed -- this is public market data.

    Returns a DataFrame with columns: open_time, open, high, low, close, volume
    """
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    resp = requests.get(BINANCE_KLINES_URL, params=params, timeout=10)
    resp.raise_for_status()
    raw = resp.json()

    df = pd.DataFrame(raw, columns=[
        "open_time", "open", "high", "low", "close", "volume",
        "close_time", "quote_asset_volume", "num_trades",
        "taker_buy_base", "taker_buy_quote", "ignore"
    ])
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms")
    for col in ("open", "high", "low", "close", "volume"):
        df[col] = df[col].astype(float)

    return df[["open_time", "open", "high", "low", "close", "volume"]]


def estimate_bar_volatility(df: pd.DataFrame) -> float:
    """
    Standard deviation of log returns, bar-to-bar (not annualized).
    """
    log_returns = np.log(df["close"] / df["close"].shift(1)).dropna()
    return float(log_returns.std())


def estimate_scaled_sigma(df: pd.DataFrame, initial_price: float, dt: float) -> float:
    """
    Convert a real bar-to-bar log-return volatility into the sigma units
    the Avellaneda-Stoikov model expects, GIVEN a specific internal dt.

    This matters because arrival_base_intensity and k in simulation.py
    were tuned together with sigma=2.0 at dt=0.005 (the synthetic-mode
    defaults) -- naively reusing those same constants at a very different
    dt (e.g. dt=1.0 for "one real bar") makes the fill-probability model
    produce nonsensical results (arrivals become certain every tick).

    Keeping dt at the same small scale as the synthetic mode and instead
    rescaling sigma to match keeps gamma/k/arrival_base_intensity valid
    without needing to re-tune them from scratch.

    sigma_AS such that sigma_AS * sqrt(dt) ~= observed price step std,
    after rescaling the real series to start at `initial_price`.
    """
    bar_sigma = estimate_bar_volatility(df)          # std of log returns, per bar
    price_step_std = initial_price * bar_sigma        # approx price-unit std at target scale
    return price_step_std / np.sqrt(dt)


def build_price_path(df: pd.DataFrame, initial_price: float = 100.0) -> np.ndarray:
    """
    Convert a real close-price series into a mid-price path that
    MarketSimulation can replay tick-by-tick.

    Rescales the whole path so it starts at `initial_price`, preserving the
    real percentage moves -- this keeps the series compatible with the AS
    formulas without changing the *shape* of real market behavior at all.
    """
    prices = df["close"].to_numpy(dtype=float)
    return prices * (initial_price / prices[0])
