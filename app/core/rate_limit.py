import math
import threading
import time
from collections import defaultdict, deque


class FailedLoginLimiter:
    def __init__(self, max_failures: int, window_seconds: int) -> None:
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._failures: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, ip: str, now: float) -> deque[float]:
        attempts = self._failures[ip]
        cutoff = now - self.window_seconds
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()
        return attempts

    def is_limited(self, ip: str) -> tuple[bool, int]:
        with self._lock:
            now = time.monotonic()
            attempts = self._prune(ip, now)
            if len(attempts) < self.max_failures:
                return False, 0
            retry = max(1, math.ceil(self.window_seconds - (now - attempts[0])))
            return True, retry

    def record_failure(self, ip: str) -> tuple[bool, int]:
        with self._lock:
            now = time.monotonic()
            attempts = self._prune(ip, now)
            attempts.append(now)
            if len(attempts) <= self.max_failures:
                return False, 0
            retry = max(1, math.ceil(self.window_seconds - (now - attempts[0])))
            return True, retry

    def clear(self, ip: str) -> None:
        with self._lock:
            self._failures.pop(ip, None)

    def reset(self) -> None:
        with self._lock:
            self._failures.clear()
