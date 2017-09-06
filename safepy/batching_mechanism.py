import asyncio
from asyncio.futures import CancelledError
from asyncio.locks import Lock, Event
from asyncio import get_event_loop, sleep
from collections import Sequence
from enum import Enum
from functools import wraps, partial
from copy import copy

from safepy.copy_exception import copy_exception_with_traceback


class BatchedError(Exception):
    pass


class AcceptResult(Enum):
    not_accepted = 0
    accepted = 1
    last_accepted = 2


def unpack_result_strategy(result, index):
    return result[index]


def return_result_strategy(result, index):
    return result


class Batch(object):
    def __init__(self):
        self._items = []

    def accept(self, item) -> AcceptResult:
        self._items.append(item)
        return AcceptResult.accepted

    @property
    def items(self):
        return self._items

    def __len__(self):
        return len(self._items)


class LimitedBatch(Batch):
    def __init__(self, max_batch_size):
        super().__init__()

        self._max_batch_size = max_batch_size

    def accept(self, item):
        if len(self._items) < self._max_batch_size:
            self._items.append(item)

            if len(self._items) == self._max_batch_size:
                return AcceptResult.last_accepted

            return AcceptResult.accepted

        # though it's not supposed to happen
        return AcceptResult.not_accepted


class BatchOperation(object):
    def __init__(self, function):
        self._function = function
        self._event = Event()
        self._event_others = Event()
        self._result = None
        self._exception = None

    async def wait_for_result_async(self, index):
        await self._event_others.wait()

        if self._exception:
            raise copy_exception_with_traceback(self._exception)

        if isinstance(self._result, Sequence):
            return self._result[index]

        # the best effort, we return the result as it is
        return self._result

    async def process_batch(self, batch):
        await self._event.wait()

        result, exception = None, None
        try:
            result = await self._function(*batch.items)
        except Exception as e:
            exception = e

        self._result = result
        self._exception = exception
        self._event_others.set()

    def signal_ready(self):
        self._event.set()


class BatchingMechanism(object):
    def __init__(self, function, timeout, batch_factory, result_distribution_strategy):
        self._function = function
        self._timeout = timeout
        self._batch_factory = batch_factory
        self._result_split_strategy = result_distribution_strategy

        self._lock = Lock()
        self._batch, self._batch_operation = self._reset()

    async def call(self, item):
        # just to silence PyCharm warning, it's set in the with block
        current_index = 0

        with await self._lock:
            batch = self._batch
            batch_operation = self._batch_operation

            accept_result = batch.accept(item)
            if accept_result == AcceptResult.not_accepted:
                # we have to reset the current batch if a new item is not accepted
                # and signal to the result handler
                batch_operation.signal_ready()
                batch, batch_operation = self._reset()

                # intentionally overwritten to handle last_accepted as well
                accept_result = batch.accept(item)
                # avoid not accepting single item
                if accept_result == AcceptResult.not_accepted:
                    # now the batch is locked, so no need
                    raise BatchedError("an item rejected from an empty batch")

            if accept_result == AcceptResult.last_accepted:
                batch_operation.signal_ready()
                self._reset()

            current_index = len(batch) - 1

        if current_index == 0:
            loop = get_event_loop()

            async def lock_protected_signal_ready():
                try:
                    await sleep(self._timeout)
                    # lock to avoid potential race condition related to reset and signal
                    with await self._lock:
                        self._reset()
                        batch_operation.signal_ready()
                except CancelledError:
                    pass

            task = loop.create_task(lock_protected_signal_ready())

            try:
                await batch_operation.process_batch(batch)

            finally:
                # cancel is ignored if the task was executed
                task.cancel()

        return await batch_operation.wait_for_result_async(current_index)

    def _reset(self):
        self._batch = self._batch_factory()
        self._batch_operation = BatchOperation(self._function)
        return self._batch, self._batch_operation


def batched_generic(timeout: float, batch_factory: callable, result_distribution_strategy: callable):
    def decorator(function):
        batching_mechanism = BatchingMechanism(function, timeout, batch_factory, result_distribution_strategy)

        @wraps(function)
        async def wrapper(item):
            return await batching_mechanism.call(item)

        return wrapper

    return decorator


def batched(timeout: float, max_batch_size: int):
    batch_factory = partial(LimitedBatch, max_batch_size=max_batch_size)
    result_distribution_strategy = return_result_strategy

    return batched_generic(timeout, batch_factory, result_distribution_strategy)


if __name__ == '__main__':
    @batched(5, 4)
    async def blah(*args):
        print(','.join(str(arg) for arg in args))
        #raise ValueError("ouch!")
        return [i + 10 for i in args]

    loop = get_event_loop()
    results = loop.run_until_complete(
        asyncio.gather(
            blah(1), blah(2), blah(3), blah(4), blah(5),
            blah(6), blah(7), blah(8), blah(9), blah(10),
            blah(11), return_exceptions=True
        )
    )
    print(results)
