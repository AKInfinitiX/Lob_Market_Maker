import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from simulation import MarketSimulation

N_RUNS = 300


def run_trial(seed: int) -> dict:
    sim = MarketSimulation(
        initial_price=100.0,
        T=1.0,
        dt=0.005,
        sigma=2.0,
        seed=seed
    )
    df = sim.run()
    metrics = sim.calculate_risk_metrics(df)
    return {
        'seed': seed,
        'final_pnl': df['pnl'].iloc[-1],
        'sharpe_ratio': metrics['sharpe_ratio'],
        'max_drawdown': metrics['max_drawdown'],
        'max_abs_inventory': df['inventory'].abs().max(),
    }


def main():
    print(f"Running Monte Carlo sweep: {N_RUNS} independent trials...")
    results = [run_trial(seed) for seed in range(N_RUNS)]
    results_df = pd.DataFrame(results)

    n_losing = (results_df['final_pnl'] < 0).sum()
    pct_losing = 100 * n_losing / N_RUNS

    print("\n--- MONTE CARLO SUMMARY ---")
    print(f"Runs: {N_RUNS}")
    print(f"Mean final PnL: ${results_df['final_pnl'].mean():.2f}")
    print(f"Std dev final PnL: ${results_df['final_pnl'].std():.2f}")
    print(f"Best run: ${results_df['final_pnl'].max():.2f}")
    print(f"Worst run: ${results_df['final_pnl'].min():.2f}")
    print(f"Runs with negative final PnL: {n_losing} ({pct_losing:.1f}%)")
    print(f"Mean Sharpe ratio: {results_df['sharpe_ratio'].mean():.2f}")
    print(f"Mean max drawdown: ${results_df['max_drawdown'].mean():.2f}")
    print(f"Worst max drawdown across all runs: ${results_df['max_drawdown'].min():.2f}")
    print("----------------------------\n")

    fig, axs = plt.subplots(2, 2, figsize=(12, 9))

    axs[0, 0].hist(results_df['final_pnl'], bins=30, color='purple', edgecolor='black')
    axs[0, 0].axvline(0, color='red', linestyle='--', label='Break-even')
    axs[0, 0].set_title(f'Final PnL Distribution ({N_RUNS} runs)')
    axs[0, 0].set_xlabel('Final PnL ($)')
    axs[0, 0].legend()

    axs[0, 1].hist(results_df['max_drawdown'], bins=30, color='orange', edgecolor='black')
    axs[0, 1].set_title('Max Drawdown Distribution')
    axs[0, 1].set_xlabel('Max Drawdown ($)')

    axs[1, 0].hist(results_df['sharpe_ratio'], bins=30, color='green', edgecolor='black')
    axs[1, 0].set_title('Sharpe Ratio Distribution')
    axs[1, 0].set_xlabel('Sharpe Ratio')

    axs[1, 1].scatter(results_df['max_abs_inventory'], results_df['final_pnl'], alpha=0.5, color='blue')
    axs[1, 1].set_title('Final PnL vs Max Inventory Held')
    axs[1, 1].set_xlabel('Max |Inventory|')
    axs[1, 1].set_ylabel('Final PnL ($)')

    plt.tight_layout()
    plt.savefig('monte_carlo_results.png')
    print("Saved chart to monte_carlo_results.png")

    results_df.to_csv('monte_carlo_results.csv', index=False)
    print("Saved raw results to monte_carlo_results.csv")


if __name__ == "__main__":
    main()