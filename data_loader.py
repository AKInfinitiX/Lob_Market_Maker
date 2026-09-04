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
    This is the real-data estimate that plugs into the AS model's sigma
    when dt is set to represent one bar (see build_price_path docstring).
    """
    log_returns = np.log(df["close"] / df["close"].shift(1)).dropna()
    return float(log_returns.std())


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
