from collections import defaultdict
from datetime import datetime

from cachetools import TTLCache

from app.config import config


class RateLimiter:
    def __init__(self):
        self.minute_cache = TTLCache(maxsize=100000, ttl=60)
        self.daily_cost = defaultdict(float)
        self.last_reset = datetime.now().date()

    def check_user_limit(self, company_id: int, user_id: str, limit: int | None = None) -> bool:
        key = f"{company_id}:{user_id}"
        current = self.minute_cache.get(key, 0)
        max_requests = limit if limit is not None else config.RATE_LIMIT_PER_USER_PER_MINUTE
        if current >= max_requests:
            return False
        self.minute_cache[key] = current + 1
        return True

    def check_company_cost(self, company_id: int, cost_usd: float) -> bool:
        today = datetime.now().date()
        if today != self.last_reset:
            self.daily_cost.clear()
            self.last_reset = today

        return self.daily_cost[company_id] + cost_usd <= config.DAILY_COST_LIMIT_PER_COMPANY

    def add_cost(self, company_id: int, cost_usd: float):
        self.daily_cost[company_id] += cost_usd


rate_limiter = RateLimiter()
