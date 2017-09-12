import collections
import time
from asyncio.locks import Lock


class StatisticsBucket:
    def __init__(self):
        self.passed = 0
        self.failed = 0


class CicruitBreakerStatistics:
    def __init__(self, buckets_count, bucket_interval):
        self._deque = collections.deque(maxlen=buckets_count)
        self._bucket_interval = bucket_interval
        self._interval = self._bucket_interval * buckets_count
        self._start_time = time.monotonic()
        self._lock = Lock()

    async def add_stats(self, passed, failed):
        with await self._lock:
            current_time = time.monotonic()

            if current_time > (self._start_time + self._interval):
                self._deque.popleft()
                # TODO: change the start time
                bucket = StatisticsBucket()
                self._deque.append(bucket)

            elif self._deque:
                bucket = self._deque[-1]

            else:
                bucket = StatisticsBucket()
                self._deque.append(bucket)

            bucket.passed += passed
            bucket.failed += failed

    async def evaluate(self):
        with await self._lock:
            passed, failed = 0, 0

            for bucket in self._deque:
                passed += bucket.passed
                failed += bucket.failed

            return passed, failed
