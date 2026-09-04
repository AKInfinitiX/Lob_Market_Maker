# Avellaneda-Stoikov Market Making Simulator

A simulation and risk-analysis framework for the Avellaneda-Stoikov
(2008) optimal market-making strategy, built on a custom price-time-
priority order book, tested against both a synthetic stochastic price
process and real historical market data.

This is a research/learning project, not a production trading system.

---

## What it does

- **Strategy**: implements the closed-form Avellaneda-Stoikov
  reservation price and optimal spread formulas.
- **Order book**: a real price-time-priority matching engine (heap-based),
  with partial fills and correct trade attribution.
- **Synthetic simulation** (`main.py`, `monte_carlo.py`): a stochastic
  public mid-price via Brownian motion with occasional jump shocks, plus a
  randomly-triggered "informed trader" regime that temporarily skews order
  flow and adds price impact.
- **Real-data simulation** (`real_data_demo.py`): replays real historical
  BTCUSDT price data through the exact same strategy and order book,
  fetched live from Binance's public API.
- **Risk analysis**: tracks inventory, cash, and PnL net of fees, with a
  forced-liquidation rule if inventory is held too long, and a 300-trial
  Monte Carlo sweep reporting the distribution of final PnL, Sharpe ratio,
  and max drawdown (not just one lucky run).

## Project structure

```
.
├── orderbook.py          # Price-time-priority matching engine (heap-based)
├── market_maker.py       # Avellaneda-Stoikov reservation price & spread
├── simulation.py         # Price process, order flow, PnL/risk tracking
├── main.py                # Single synthetic simulation run + plot
├── monte_carlo.py         # 300-trial Monte Carlo sweep + plots + CSV
├── data_loader.py          # Fetches real price data (Binance API), volatility estimation
├── real_data_demo.py       # Runs the market maker against real historical price data
├── results/                # Checked-in sample output (see below)
├── requirements.txt
├── .gitignore
└── README.md
```

## Installation

```bash
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Requires Python 3.9+.

## Usage

| Command | What it does | Output |
|---|---|---|
| `python3 main.py` | Single synthetic run | Prints PnL/Sharpe/drawdown, saves `simulation_plot.png` |
| `python3 monte_carlo.py` | 300 seeded synthetic trials | Saves `monte_carlo_results.png` and `.csv` |
| `python3 real_data_demo.py` | Replays real BTCUSDT data (needs internet) | Prints metrics, saves `real_data_simulation_plot.png` |

## Key parameters

| Parameter | Meaning | Default |
|---|---|---|
| `gamma` | Risk aversion coefficient | 0.01 |
| `sigma` | Price volatility (auto-estimated from data in real-data mode) | 2.0 |
| `k` | Order arrival decay rate | 45.0 |
| `T` | Simulation horizon | 1.0 (auto-set from data length in real-data mode) |
| `dt` | Internal timestep size | 0.005 |
| `max_held_steps` | Force-liquidate inventory after N steps | 40 |
| `informed_regime_prob` | Chance of entering an informed-flow regime per step | 0.03 |

---

## Sample results

Pre-generated example output lives in [`results/`](./results):

| File | Description |
|---|---|
| [`results/simulation_plot.png`](./results/simulation_plot.png) | Single synthetic run: mid-price with MM bid/ask overlay, inventory, cumulative PnL |
| [`results/monte_carlo_results.png`](./results/monte_carlo_results.png) | 300-trial distributions: final PnL, max drawdown, Sharpe ratio, PnL vs. max inventory |
| [`results/monte_carlo_results.csv`](./results/monte_carlo_results.csv) | Raw per-trial data behind the plot above |
| [`results/real_data_simulation_plot.png`](./results/real_data_simulation_plot.png) | Same strategy replayed against real BTCUSDT 1-minute data |

Everything in `results/` is regenerable — run any of the three scripts
above to produce fresh ones with a different seed, symbol, or parameters.

### Synthetic Monte Carlo (300 trials)

Roughly 40% of runs end with negative final PnL — this is a small-edge,
fat-tailed strategy, not "free money," which is the expected and honest
outcome of a correctly-implemented spread-capture strategy under
adverse selection.

### Real-data run (BTCUSDT, 1-minute candles, 1000 bars)

| Metric | Value |
|---|---|
| Symbol / interval | BTCUSDT, 1m |
| Final PnL | $1.78 |
| Sharpe ratio | 0.37 |
| Max drawdown | -$1.99 |

These are in the same range as the synthetic Monte Carlo distribution
(mean Sharpe ~0.3, drawdowns typically -$2 to -$3), meaning the strategy
behaves consistently whether tested on synthetic or real prices — a
useful sanity check that the synthetic simulation isn't wildly
unrepresentative of real market behavior, even though it remains a
simplified model (see limitations below).

Exact numbers will differ each time you run `real_data_demo.py`, since it
always pulls whatever the most recent 1000 candles happen to be.

---

## A real bug found and fixed while adding real-data mode

Worth documenting because it's a genuine example of validating a
simulation against real data exposing a hidden assumption:

An early version of real-data mode used `dt=1.0` to represent "one real
bar." This broke the fill-probability model: `lambda * dt` came out
around 60, when it needs to be a probability in `[0, 1]` — making
counterparty order arrivals *deterministic* every tick on both sides
instead of random. Combined with a second, independent bug in the
matching engine — fills were attributed to the market maker whenever the
execution price *happened* to match its quote, rather than checking
whether the market maker's own order was actually part of the trade —
this produced a deterministic sawtooth inventory pattern that repeatedly
grew to the `max_held_steps` forced-liquidation cap and lost money on
every single cycle.

**Fix:** fill probabilities are now clipped to `[0, 1]`; trade attribution
checks actual order IDs instead of price coincidence; and real-data mode
keeps `dt` at the same internal scale as the synthetic mode, rescaling the
real volatility estimate to match (`estimate_scaled_sigma()` in
`data_loader.py`) rather than changing `dt` itself. This also slightly
changed synthetic-mode PnL for a given seed, since the price-coincidence
bug could rarely fire there too — that's a correctness fix, not new
randomness.

---

## What this project does NOT do (limitations)

- **No real order book depth.** The book is cleared every timestep and
  only ever holds the market maker's own bid/ask plus at most one
  counterparty order per side — no other participants, no multiple price
  levels, no queue position.
- **Order flow is still synthetic, even in real-data mode.** Real-data
  mode replaces the *price* path with real data, but fills are still
  generated by the same probabilistic arrival model, since Binance's
  public klines endpoint gives OHLCV candles, not order-level data.
- **Fixed order size.** Every order is exactly 1 unit — no partial fills
  or variable trade sizes from other participants.
- **No latency modeling.** Real market-making PnL is heavily driven by
  latency and quote staleness, which isn't simulated here.
- **Uncalibrated constants.** The informed-trader probability/duration/
  intensity, price impact per fill, and jump size were chosen to be
  directionally reasonable, not fit to real data. `gamma`/`k` are also
  not re-fit for real data — only `sigma` is estimated from it.
- **Sharpe ratio is a relative comparison metric only.** The
  "annualization" (`periods_per_year = 1/dt`) is internally consistent
  across runs of this simulator but doesn't correspond to real calendar
  time, so it shouldn't be compared to real-world annualized Sharpe
  ratios.

**In short:** the strategy math is correct, the simulation is genuinely
stochastic (verified via reproducible seeded runs), and it now behaves
consistently on both synthetic and real data — but the market mechanics
are a simplified single-counterparty approximation of a real limit order
book, not a faithful replica of one.

## Suggested next steps

- Recalibrate `gamma` and `k` against real spread/volume data, not just
  `sigma`.
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
