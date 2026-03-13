import asyncio
import random
import time
from functools import wraps

from sp_api.base import SellingApiRequestThrottledException


def rate_limit(
    max_rate: float, burst_rate: int, time_period: float = 1, max_retries: int = 5
):
    """
    Token bucket rate limiter decorator for Amazon SP API.

    Args:
        max_rate(int):    Steady-state requests allowed per time_period.
        burst_rate(int):  Max bucket size — how many requests can fire immediately.
        time_period(float): Window in seconds (default: 1).
        max_retries(int): Number of attempts after which the exception is raised.

    Usage:
        @amazon_throttled(max_rate=5, burst_rate=15)
        async def create_report(...): ...
    """
    refill_rate = max_rate / time_period  # tokens per second

    def decorator(func):
        tokens = float(burst_rate)
        last_refill = time.monotonic()
        lock = asyncio.Lock()

        @wraps(func)
        async def wrapper(*args, **kwargs):
            nonlocal tokens, last_refill

            while True:
                async with lock:
                    now = time.monotonic()
                    tokens = min(burst_rate, tokens + (now - last_refill) * refill_rate)
                    last_refill = now

                    if tokens >= 1:
                        tokens -= 1
                        break

                    wait = (1 - tokens) / refill_rate

                await asyncio.sleep(wait)

            last_exc: Exception = RuntimeError(
                f"{func.__name__} throttled after {max_retries} retries"
            )
            retries = 0
            while retries < max_retries:
                try:
                    return await func(*args, **kwargs)
                except SellingApiRequestThrottledException as e:
                    last_exc = e
                    retries += 1
                    wait = (2**retries) + random.uniform(0, 1)
                    print(
                        f"!!! Amazon Throttled Exception on {func.__name__}. Backing off {wait:.2f}s (attempt {retries})"
                    )
                    await asyncio.sleep(wait)
                except Exception:
                    raise

            raise last_exc

        return wrapper

    return decorator
