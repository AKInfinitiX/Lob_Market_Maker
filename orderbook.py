import heapq
import itertools
from typing import List, Tuple, Optional

_id_counter = itertools.count(1)


def next_order_id() -> int:
    return next(_id_counter)


class Order:
    def __init__(self, order_id: int, is_buy: bool, price: float, quantity: int, timestamp: float):
        self.order_id = order_id
        self.is_buy = is_buy
        self.price = price
        self.quantity = quantity
        self.timestamp = timestamp

    def __lt__(self, other: 'Order') -> bool:
        if self.price == other.price:
            return self.timestamp < other.timestamp
        if self.is_buy:
            return self.price > other.price
        return self.price < other.price

    @property
    def real_price(self) -> float:
        return self.price


class OrderBook:
    def __init__(self):
        self.bids: List[Order] = []
        self.asks: List[Order] = []
        self.order_map = {}

    def add_order(self, order: Order):
        self.order_map[order.order_id] = order
        if order.is_buy:
            heapq.heappush(self.bids, order)
        else:
            heapq.heappush(self.asks, order)

    def get_mid_price(self) -> Optional[float]:
        if self.bids and self.asks:
            return (self.bids[0].real_price + self.asks[0].real_price) / 2.0
        return None

    def match_orders(self) -> List[Tuple[int, int, float, int]]:
        trades = []
        while self.bids and self.asks:
            best_bid = self.bids[0]
            best_ask = self.asks[0]
            if best_bid.real_price >= best_ask.real_price:
                matched_qty = min(best_bid.quantity, best_ask.quantity)
                execution_price = best_ask.real_price
                trades.append((best_bid.order_id, best_ask.order_id, execution_price, matched_qty))
                best_bid.quantity -= matched_qty
                best_ask.quantity -= matched_qty
                if best_bid.quantity == 0:
                    heapq.heappop(self.bids)
                    self.order_map.pop(best_bid.order_id, None)
                if best_ask.quantity == 0:
                    heapq.heappop(self.asks)
                    self.order_map.pop(best_ask.order_id, None)
            else:
                break
        return trades

    def clear(self):
        self.bids.clear()
        self.asks.clear()
        self.order_map.clear()