import collections
import time
from asyncio.locks import Lock
from enum import Enum


class StatisticsBucket:
    def __init__(self):
        self.passed = 0
        self.failed = 0


class StatisticsBucketContainer:
    def __init__(self, size):
        # TODO: value sanity check
        self._queue = collections.deque(maxlen=size)

    def reset_from_left(self, count):
        real_count = min(count, len(self._queue))
        for _ in range(real_count):
            self._queue.popleft()
            self._queue.append(StatisticsBucket())

    def update_current(self, passed, failed):
        current_bucket = self._queue[0]
        current_bucket.passed += passed
        current_bucket.failed += failed

    def evaluate(self):
        passed = 0
        failed = 0

        for bucket in self._queue:
            passed += bucket.passed
            failed += bucket.failed

        return passed, failed


class CircuitBreakerState(Enum):
    closed = 1
    open = 2
    half_open = 3


class CircuitBreaker:
    def __init__(self, func, buckets_count, bucket_interval, min_evaluation):
        self._bucket_container = StatisticsBucketContainer(buckets_count)
        self._bucket_interval = bucket_interval
        self._interval = self._bucket_interval * buckets_count
        self._next_time = time.monotonic() + self._bucket_interval
        self._lock = Lock()
        self._func = func
        self._min_evaluation = min_evaluation
        self._current_state = CircuitBreakerState.closed

    def _handle_closed(self):
        pass

    def _handle_open(self):
        pass

    def _handle_half_open(self):
        pass

    async def call(self, *args, **kwargs):

        with await self._lock:
            current_time = time.monotonic()

            if current_time > self._next_time:
                quotient, remainder = divmod(current_time - self._next_time, self._bucket_interval)
                if remainder > 0:
                    quotient += 1

                self._next_time = quotient * self._bucket_interval
                self._bucket_container.reset_from_left(quotient)

                passed, failed = self._bucket_container.evaluate()

                count = passed + failed

                if count > self._min_evaluation:
                    if passed
        try:
            return await self._func(*args, **kwargs)
        finally:
            pass
