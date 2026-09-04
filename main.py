import matplotlib.pyplot as plt
from simulation import MarketSimulation


def main():
    print("Running Advanced Avellaneda-Stoikov Simulation...")

    sim = MarketSimulation(
        initial_price=100.0,
        T=1.0,
        dt=0.005,
        sigma=2.0
    )

    df = sim.run()

    metrics = sim.calculate_risk_metrics(df)
    print("\n--- PERFORMANCE & RISK METRICS ---")
    print(f"Final PnL: ${df['pnl'].iloc[-1]:.2f}")
    print(f"Sharpe Ratio: {metrics['sharpe_ratio']}")
    print(f"Maximum Drawdown: ${metrics['max_drawdown']}")
    print("------------------------------------\n")

    fig, axs = plt.subplots(3, 1, figsize=(10, 12))

    axs[0].plot(df['time'], df['mid_price'], label='Market Mid-Price', color='black', linewidth=1)
    axs[0].plot(df['time'], df['bid_price'], label='MM Bid', color='green', alpha=0.7)
    axs[0].plot(df['time'], df['ask_price'], label='MM Ask', color='red', alpha=0.7)
    axs[0].set_title('Market Maker Quoting with Shocks & Fees')
    axs[0].legend()

    axs[1].step(df['time'], df['inventory'], color='blue')
    axs[1].set_title('Inventory Exposure')
    axs[1].axhline(0, color='black', linestyle='--')

    axs[2].plot(df['time'], df['pnl'], color='purple')
    axs[2].set_title('Cumulative PnL (Net of Fees)')

    plt.tight_layout()
    plt.savefig('simulation_plot.png')
    print("Saved chart to simulation_plot.png")
    plt.show()


if __name__ == "__main__":
    main()