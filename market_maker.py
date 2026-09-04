import math
from typing import Tuple


class AvellanedaStoikovMarketMaker:
    def __init__(self, gamma: float, sigma: float, k: float, T: float):
        if gamma <= 0:
            raise ValueError("gamma must be > 0")
        if k <= 0:
            raise ValueError("k must be > 0")
        if sigma < 0:
            raise ValueError("sigma must be >= 0")
        if T <= 0:
            raise ValueError("T must be > 0")

        self.gamma = gamma
        self.sigma = sigma
        self.k = k
        self.T = T

    def calculate_reservation_price(self, mid_price: float, inventory: int, t: float) -> float:
        time_left = max(0.0, self.T - t)
        inventory_penalty = inventory * self.gamma * (self.sigma ** 2) * time_left
        return mid_price - inventory_penalty

    def calculate_optimal_spread(self, t: float) -> float:
        time_left = max(0.0, self.T - t)
        spread = (self.gamma * (self.sigma ** 2) * time_left) + \
                 ((2.0 / self.gamma) * math.log(1.0 + (self.gamma / self.k)))
        return spread

    def get_quotes(self, mid_price: float, inventory: int, t: float) -> Tuple[float, float]:
        r = self.calculate_reservation_price(mid_price, inventory, t)
        spread = self.calculate_optimal_spread(t)
        bid_price = round(r - (spread / 2.0), 2)
        ask_price = round(r + (spread / 2.0), 2)
        return bid_price, ask_price