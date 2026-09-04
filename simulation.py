import random
import numpy as np
import pandas as pd
from typing import List, Dict, Optional
from market_maker import AvellanedaStoikovMarketMaker
from orderbook import OrderBook, Order, next_order_id


class MarketSimulation:
    def __init__(self, initial_price: float, T: float, dt: float, sigma: float,
                 gamma: float = 0.01, k: float = 45.0, max_held_steps: int = 40,
                 informed_regime_prob: float = 0.03,
                 informed_min_duration: int = 3,
                 informed_max_duration: int = 15,
                 informed_intensity_multiplier: float = 2.5,
                 price_impact_per_fill: float = 0.02,
                 seed: int = None,
                 price_path: Optional[np.ndarray] = None):
        """
        price_path: optional 1D array of real historical mid-prices to replay
        instead of generating a synthetic Brownian-motion price. Each array
        element is treated as one simulation step (spaced `dt` apart), so
        T is overridden to match len(price_path). The market maker's own
        quoting logic, the order book, and order-flow model are unchanged --
        only the source of the public mid-price differs.
        """
        if seed is not None:
            random.seed(seed)
            np.random.seed(seed)

        self.price_path = None
        if price_path is not None:
            self.price_path = np.asarray(price_path, dtype=float)
            if len(self.price_path) < 2:
                raise ValueError("price_path must contain at least 2 points")
            initial_price = float(self.price_path[0])
            T = (len(self.price_path) - 1) * dt  # keep horizon consistent with data length

        self.mid_price = initial_price
        self.T = T
        self.dt = dt
        self.sigma = sigma

        # gamma and k calibrated against real market data:
        #   - target avg spread ~4.5bps (S&P 500 avg, Nasdaq research 2024)
        #   - gamma=0.01, k=45 produces a modeled spread of ~4.4-8.4bps
        #     across the trading day, same order of magnitude as observed
        self.market_maker = AvellanedaStoikovMarketMaker(
            gamma=gamma,
            sigma=self.sigma,
            k=k,
            T=self.T
        )

        self.book = OrderBook()

        self.inventory = 0
        self.cash = 0.0
        self.fee_per_trade = 0.01
        self.inventory_held_steps = 0
        self.max_held_steps = max_held_steps
        self.history: List[Dict] = []

        self.arrival_base_intensity = 150.0

        self.informed_regime_prob = informed_regime_prob
        self.informed_min_duration = informed_min_duration
        self.informed_max_duration = informed_max_duration
        self.informed_intensity_multiplier = informed_intensity_multiplier
        self.price_impact_per_fill = price_impact_per_fill

        self.informed_remaining = 0
        self.informed_direction = 0

    def _update_informed_regime(self):
        if self.informed_remaining <= 0:
            if random.random() < self.informed_regime_prob:
                self.informed_remaining = random.randint(
                    self.informed_min_duration, self.informed_max_duration
                )
                self.informed_direction = random.choice([-1, 1])
            else:
                self.informed_direction = 0

    def simulate_public_price_step(self) -> float:
        shock = np.random.normal(0, self.sigma * np.sqrt(self.dt))
        if random.random() < 0.05:
            shock += np.random.choice([-0.5, 0.5])
        return shock

    def _post_mm_quotes(self, bid_price: float, ask_price: float, t: float):
        self.book.add_order(Order(next_order_id(), True, bid_price, 1, t))
        self.book.add_order(Order(next_order_id(), False, ask_price, 1, t))

    def _maybe_send_counterparty_orders(self, bid_price: float, ask_price: float, t: float):
        delta_b = max(0.0, self.mid_price - bid_price)
        delta_a = max(0.0, ask_price - self.mid_price)

        k = self.market_maker.k
        lambda_b = self.arrival_base_intensity * np.exp(-k * delta_b)
        lambda_a = self.arrival_base_intensity * np.exp(-k * delta_a)

        if self.informed_direction == -1:
            lambda_b *= self.informed_intensity_multiplier
        elif self.informed_direction == 1:
            lambda_a *= self.informed_intensity_multiplier

        if random.random() < lambda_b * self.dt:
            self.book.add_order(Order(next_order_id(), False, bid_price, 1, t))
        if random.random() < lambda_a * self.dt:
            self.book.add_order(Order(next_order_id(), True, ask_price, 1, t))

    def simulate_market_orders(self, bid_price: float, ask_price: float, t: float) -> float:
        if self.inventory != 0:
            self.inventory_held_steps += 1
            if self.inventory_held_steps >= self.max_held_steps:
                if self.inventory > 0:
                    self.cash += (self.mid_price - 0.05 - self.fee_per_trade) * self.inventory
                    self.inventory = 0
                elif self.inventory < 0:
                    self.cash -= (self.mid_price + 0.05 + self.fee_per_trade) * abs(self.inventory)
                    self.inventory = 0
                self.inventory_held_steps = 0
                return 0.0
        else:
            self.inventory_held_steps = 0

        self.book.clear()
        self._post_mm_quotes(bid_price, ask_price, t)
        self._maybe_send_counterparty_orders(bid_price, ask_price, t)

        trades = self.book.match_orders()
        impact = 0.0
        for bid_id, ask_id, exec_price, qty in trades:
            if abs(exec_price - bid_price) < 1e-9:
                self.inventory += qty
                self.cash -= (exec_price + self.fee_per_trade) * qty
                if self.informed_direction == -1:
                    impact -= self.price_impact_per_fill * qty
            elif abs(exec_price - ask_price) < 1e-9:
                self.inventory -= qty
                self.cash += (exec_price - self.fee_per_trade) * qty
                if self.informed_direction == 1:
                    impact += self.price_impact_per_fill * qty

        return impact

    def calculate_risk_metrics(self, df: pd.DataFrame) -> dict:
        df['pnl_returns'] = df['pnl'].diff().fillna(0)
        mean_return = df['pnl_returns'].mean()
        std_return = df['pnl_returns'].std()

        periods_per_year = 1.0 / self.dt
        sharpe_ratio = (mean_return / std_return) * np.sqrt(periods_per_year) if std_return > 0 else 0.0

        rolling_max = df['pnl'].cummax()
        drawdown = df['pnl'] - rolling_max
        max_drawdown = drawdown.min()

        return {
            "sharpe_ratio": round(sharpe_ratio, 2),
            "max_drawdown": round(max_drawdown, 2)
        }

    def run(self) -> pd.DataFrame:
        using_real_data = self.price_path is not None
        steps = (len(self.price_path) - 1) if using_real_data else int(self.T / self.dt)

        for step in range(steps):
            t = step * self.dt
            self._update_informed_regime()

            current_mid = self.mid_price
            bid_price, ask_price = self.market_maker.get_quotes(current_mid, self.inventory, t)

            impact = self.simulate_market_orders(bid_price, ask_price, t)

            pnl = self.cash + (self.inventory * current_mid)

            self.history.append({
                'time': t,
                'mid_price': current_mid,
                'bid_price': bid_price,
                'ask_price': ask_price,
                'inventory': self.inventory,
                'pnl': pnl
            })

            if using_real_data:
                # Real data already contains true price dynamics; the
                # market maker's own fills still apply a small extra
                # impact on top of it, same as in the synthetic mode.
                self.mid_price = float(self.price_path[step + 1]) + impact
            else:
                public_shock = self.simulate_public_price_step()
                self.mid_price = current_mid + impact + public_shock

            if self.informed_remaining > 0:
                self.informed_remaining -= 1
                if self.informed_remaining == 0:
                    self.informed_direction = 0

        return pd.DataFrame(self.history)
