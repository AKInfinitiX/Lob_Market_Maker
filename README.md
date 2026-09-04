# Avellaneda-Stoikov Market Making Simulator

A simulation and Monte Carlo risk-analysis framework for testing the
Avellaneda-Stoikov (2008) optimal market-making strategy against a
stochastic single-asset price process, using a custom price-time-priority
order book matching engine.

This is a research/learning project, not a production trading system.

## What this project does

- Implements the closed-form Avellaneda-Stoikov reservation price and
  optimal spread formulas.
- Runs a simplified limit order book (price-time priority, heap-based)
  that matches the market maker's bid/ask against synthetically generated
  counterparty order flow each timestep.
- Models a stochastic public mid-price via Brownian motion with occasional
  jump shocks, plus a randomly-triggered "informed trader" regime that
  temporarily skews order flow and adds price impact.
- Tracks inventory, cash, and PnL net of a flat per-trade fee, with a
  forced-liquidation rule if inventory is held too long.
- Runs a 300-trial Monte Carlo sweep (varying only the random seed) to
  report the distribution of final PnL, Sharpe ratio, and max drawdown
  rather than a single simulation run.

## Real market data mode

`real_data_demo.py` fetches real historical BTCUSDT 1-minute candles from
Binance's public REST API (no key required), estimates volatility (sigma)
directly from real log returns, and replays the real price path through
the *same* Avellaneda-Stoikov market maker and order book -- nothing
about the strategy or matching engine changes.

```bash
python3 real_data_demo.py
```

This does **not** require new math: the AS reservation-price/spread
formulas are identical, and the extra data-side work is just standard
deviation of log returns. It's mostly plumbing (fetch → clean → feed into
the existing simulation loop), isolated in `data_loader.py` so the core
`market_maker.py` / `orderbook.py` logic stays untouched.

**Caveat that matters:** `gamma` and `k` in `main.py` / `monte_carlo.py`
were chosen for the synthetic toy time-scale (`dt=0.005`), not fit to real
1-minute bar data. `real_data_demo.py` re-estimates `sigma` from real data
but reuses the same `gamma`/`k` defaults, so treat its output as "the same
strategy logic plugged into real prices," not a fully recalibrated
production model. Proper recalibration of `gamma`/`k` against real spread
and order-flow data is the natural next step (see below).

## What this project does NOT do (important limitations)

- **Order flow is still synthetic even in real-data mode.** Real-data mode
  replaces the *price* path with real data, but fills are still generated
  by the same probabilistic arrival model as the synthetic mode, since
  Binance's public klines endpoint gives OHLCV candles, not individual
  order-level data.
- **No real order book depth.** The book is cleared every timestep and
  only ever holds the market maker's own bid/ask plus at most one
  counterparty order per side — there are no other participants, no
  multiple price levels, and no queue position.
- **Fixed order size.** Every order is exactly 1 unit; there are no
  partial fills or variable trade sizes from other participants.
- **No latency modeling.** Real market-making PnL is heavily driven by
  latency and quote staleness, which is not simulated here.
- **Uncalibrated constants.** Parameters such as the informed-trader
  probability/duration/intensity, price impact per fill, and jump size
  were chosen to be directionally reasonable, not fit to real data.
- **Sharpe ratio is a relative comparison metric only.** The
  "annualization" (`periods_per_year = 1/dt`) is internally consistent
  across runs of this simulator but does not correspond to real calendar
  time, so it should not be compared to real-world annualized Sharpe
  ratios.

In short: the strategy math is correct and the simulation is genuinely
stochastic (verified by reproducible, seeded Monte Carlo runs), but the
market mechanics are a simplified single-counterparty approximation of a
real limit order book, not a faithful replica of one.

## Project structure

```
.
├── orderbook.py        # Price-time-priority matching engine (heap-based)
├── market_maker.py      # Avellaneda-Stoikov reservation price & spread
├── simulation.py         # Price process, order flow, PnL/risk tracking
├── main.py                 # Single simulation run (synthetic price) + plot
├── monte_carlo.py          # 300-trial Monte Carlo sweep + plots + CSV
├── data_loader.py           # Fetches real price data (Binance API) & estimates volatility
├── real_data_demo.py        # Runs the market maker against real historical price data
├── requirements.txt
└── README.md
```

## Installation

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Requires Python 3.9+ (uses standard type hints and `heapq`).

## Usage

**Single run** (prints PnL/Sharpe/drawdown, saves `simulation_plot.png`):

```bash
python3 main.py
```

**Monte Carlo sweep** (300 seeded trials, saves
`monte_carlo_results.png` and `monte_carlo_results.csv`):

```bash
python3 monte_carlo.py
```

Both scripts write output plots to the current working directory.

## Key parameters (`simulation.py` / `market_maker.py`)

| Parameter | Meaning | Default |
|---|---|---|
| `gamma` | Risk aversion coefficient | 0.01 |
| `sigma` | Price volatility | 2.0 |
| `k` | Order arrival decay rate | 45.0 |
| `T` | Simulation horizon | 1.0 |
| `dt` | Timestep size | 0.005 |
| `max_held_steps` | Force-liquidate inventory after N steps | 40 |
| `informed_regime_prob` | Chance of entering an informed-flow regime per step | 0.03 |

## Sample results

Pre-generated example output is checked into [`results/`](./results) so
you can see what the simulator produces without running it yourself:

| File | Description |
|---|---|
| [`results/simulation_plot.png`](./results/simulation_plot.png) | Single run: mid-price with MM bid/ask overlay, inventory over time, and cumulative PnL |
| [`results/monte_carlo_results.png`](./results/monte_carlo_results.png) | 300-trial distributions of final PnL, max drawdown, Sharpe ratio, and PnL vs. max inventory held |
| [`results/monte_carlo_results.csv`](./results/monte_carlo_results.csv) | Raw per-trial data (seed, final PnL, Sharpe, drawdown, max inventory) behind the plot above |

These confirm the strategy is a small-edge, fat-tailed one rather than
"free money" — roughly 40% of the 300 runs end with negative final PnL
in the default configuration. Everything in `results/` is regenerable;
run `main.py` or `monte_carlo.py` to produce fresh ones with a different
seed or parameter set.

## Suggested next steps

- Recalibrate `gamma` and `k` specifically against real spread/volume
  data for the chosen symbol and bar frequency (currently only `sigma`
  is estimated from real data; `gamma`/`k` still use the synthetic-mode
  defaults).
- Run `real_data_demo.py` across multiple symbols/time windows and
  compare PnL/Sharpe distributions the way `monte_carlo.py` does for the
  synthetic mode.
- Add real order book depth with multiple simulated participants instead
  of clearing the book every tick.
- Fit the informed-flow parameters to real order-flow data instead of
  using fixed constants.

## References

- Avellaneda, M., & Stoikov, S. (2008). *High-frequency trading in a
  limit order book.* Quantitative Finance, 8(3), 217-224.
