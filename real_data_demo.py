"""
Runs the Avellaneda-Stoikov market maker against REAL historical price
data instead of the synthetic Brownian-motion price used in main.py.

Nothing about the strategy math or the order book changes here -- this
script only swaps out where the mid-price series comes from, and
estimates sigma from real data instead of guessing it.
"""
import matplotlib.pyplot as plt
from simulation import MarketSimulation
from data_loader import fetch_binance_klines, estimate_scaled_sigma, build_price_path


def main():
    print("Fetching real historical price data from Binance (public API, no key needed)...")
    df = fetch_binance_klines(symbol="BTCUSDT", interval="1m", limit=1000)
    print(f"Downloaded {len(df)} real 1-minute candles for BTCUSDT.")

    initial_price = 100.0
    dt = 0.005  # match the synthetic mode's internal time scale -- see
                # estimate_scaled_sigma() docstring for why this matters.

    # Estimate sigma directly from real data, rescaled into the same units
    # gamma/k/arrival_base_intensity were tuned against in simulation.py.
    sigma_scaled = estimate_scaled_sigma(df, initial_price, dt)
    print(f"Scaled sigma for the AS model (dt={dt}): {sigma_scaled:.4f}")

    # Rescale the real price series to start at 100 so it's easy to compare
    # against the synthetic simulation's usual starting point -- the real
    # percentage moves are preserved exactly, only the starting level changes.
    price_path = build_price_path(df, initial_price=initial_price)

    sim = MarketSimulation(
        initial_price=initial_price,
        T=1.0,          # overridden internally to match price_path length
        dt=dt,
        sigma=sigma_scaled,
        price_path=price_path,
        seed=42
    )

    result_df = sim.run()
    metrics = sim.calculate_risk_metrics(result_df)

    print("\n--- REAL-DATA REPLAY: PERFORMANCE & RISK METRICS ---")
    print(f"Final PnL: ${result_df['pnl'].iloc[-1]:.2f}")
    print(f"Sharpe Ratio: {metrics['sharpe_ratio']}")
    print(f"Maximum Drawdown: ${metrics['max_drawdown']}")
    print("-----------------------------------------------------\n")

    fig, axs = plt.subplots(3, 1, figsize=(10, 12))

    axs[0].plot(result_df['time'], result_df['mid_price'], label='Real BTC Mid-Price (rescaled)', color='black', linewidth=1)
    axs[0].plot(result_df['time'], result_df['bid_price'], label='MM Bid', color='green', alpha=0.7)
    axs[0].plot(result_df['time'], result_df['ask_price'], label='MM Ask', color='red', alpha=0.7)
    axs[0].set_title('Market Maker Quoting Against Real BTCUSDT 1m Data')
    axs[0].legend()

    axs[1].step(result_df['time'], result_df['inventory'], color='blue')
    axs[1].set_title('Inventory Exposure')
    axs[1].axhline(0, color='black', linestyle='--')

    axs[2].plot(result_df['time'], result_df['pnl'], color='purple')
    axs[2].set_title('Cumulative PnL (Net of Fees) -- Real Data Replay')

    plt.tight_layout()
    plt.savefig('real_data_simulation_plot.png')
    print("Saved chart to real_data_simulation_plot.png")


if __name__ == "__main__":
    main()
