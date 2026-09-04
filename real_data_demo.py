"""
Runs the Avellaneda-Stoikov market maker against REAL historical price
data instead of the synthetic Brownian-motion price used in main.py.

Nothing about the strategy math or the order book changes here -- this
script only swaps out where the mid-price series comes from, and
estimates sigma from real data instead of guessing it.
"""
import matplotlib.pyplot as plt
from simulation import MarketSimulation
from data_loader import fetch_binance_klines, estimate_bar_volatility, build_price_path


def main():
    print("Fetching real historical price data from Binance (public API, no key needed)...")
    df = fetch_binance_klines(symbol="BTCUSDT", interval="1m", limit=1000)
    print(f"Downloaded {len(df)} real 1-minute candles for BTCUSDT.")

    # Estimate sigma directly from real data instead of guessing it.
    sigma_est = estimate_bar_volatility(df)
    print(f"Estimated bar-to-bar volatility from real data: {sigma_est:.6f}")

    # Rescale the real price series to start at 100 so it's easy to compare
    # against the synthetic simulation's usual starting point -- the real
    # percentage moves are preserved exactly, only the starting level changes.
    price_path = build_price_path(df, initial_price=100.0)

    # dt=1.0 here represents "one real bar" (one minute), not the toy
    # dt=0.005 used in main.py's synthetic simulation. gamma/k were tuned
    # for the synthetic scale in main.py and have NOT been re-fit for real
    # 1-minute BTC data -- see README for why that recalibration matters.
    sim = MarketSimulation(
        initial_price=100.0,
        T=1.0,          # overridden internally to match price_path length
        dt=1.0,
        sigma=sigma_est,
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
