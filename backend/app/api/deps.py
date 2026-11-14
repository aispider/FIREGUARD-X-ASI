from __future__ import annotations

import logging
from functools import lru_cache

import redis

from app.config import get_settings
from app.security.ratelimit import RateLimiter

log = logging.getLogger("fireguard.deps")


@lru_cache
def redis_client() -> redis.Redis | None:
    url = get_settings().redis_url
    if not url:
        return None
    try:
        c = redis.Redis.from_url(url, socket_connect_timeout=1, socket_timeout=1)
        c.ping()
        return c
    except Exception as e:  # noqa: BLE001
        log.warning("redis unavailable, using in-memory rate limiting: %s", e)
        return None


@lru_cache
def limiter() -> RateLimiter:
    return RateLimiter(redis_client())


def redis_ok() -> bool:
    c = redis_client()
    try:
        return bool(c and c.ping())
    except Exception:  # noqa: BLE001
        return False


# Names used by the test fixtures.
get_redis = redis_client
get_limiter = limiter
