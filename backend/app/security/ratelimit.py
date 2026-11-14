"""Fixed-window rate limiter. Redis when available, in-process fallback otherwise."""

from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass

log = logging.getLogger("fireguard.ratelimit")


@dataclass
class Decision:
    allowed: bool
    remaining: int
    retry_after: int


class RateLimiter:
    def __init__(self, redis_client=None, prefix: str = "fgx:rl") -> None:
        self._redis = redis_client
        self._prefix = prefix
        self._mem: dict[str, tuple[int, int]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str, limit: int, window_s: int = 60) -> Decision:
        now = int(time.time())
        window = now // window_s
        retry_after = window_s - (now % window_s)
        if self._redis is not None:
            try:
                rkey = f"{self._prefix}:{key}:{window}"
                pipe = self._redis.pipeline()
                pipe.incr(rkey)
                pipe.expire(rkey, window_s + 1)
                count = int(pipe.execute()[0])
                return Decision(count <= limit, max(0, limit - count), retry_after)
            except Exception as exc:  # Redis down: fall back to memory rather than fail open silently
                log.warning("rate limiter falling back to memory: %s", exc)
        with self._lock:
            w, count = self._mem.get(key, (window, 0))
            if w != window:
                w, count = window, 0
            count += 1
            self._mem[key] = (w, count)
            if len(self._mem) > 10_000:
                self._mem = {k: v for k, v in self._mem.items() if v[0] == window}
        return Decision(count <= limit, max(0, limit - count), retry_after)
