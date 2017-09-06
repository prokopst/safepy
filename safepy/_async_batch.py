from asyncio.locks import Lock, Event
from enum import Enum

"""
https://azure.microsoft.com/en-us/blog/new-article-best-practices-for-performance-improvements-using-service-bus-brokered-messaging/
"""


class AcceptResult(Enum):
    not_accepted = 0
    accepted = 1
    last_accepted = 2


class BatchOperation(object):
    def __init__(self, batch_contraint_factory):
        self._batch = []
        self._batch_contraint = batch_contraint_factory(self._batch)
        self._event = Event()

    def can_accept(self, item):
        return self._batch_contraint(item)

    def add(self, item):
        key = len(self._batch)
        self._batch.append(item)
        return key

    def close(self):
        self._event.set()


class LimitSizeBatchConstrain(object):
    pass


class BatchMechanism(object):
    def __init__(self, batch_constraint_factory):
        self._batch_constraint_factory = batch_constraint_factory
        self._batch_operation = None
        self._batch_operation_lock = None
        self._result_distribution_strategy = None

    def _create_batch_operation(self):
        return BatchOperation(self._batch_constraint_factory)

    def _register_ready(self):
        ...

    async def process(self, item):
        process_this_context = False

        with await self._batch_operation_lock:
            batch_operation = self._batch_operation

            if not batch_operation:
                self._batch_operation = self._create_batch_operation()
                batch_operation = self._batch_operation
                process_this_context = True

            constrain_result = batch_operation.can_accept(item)

            if constrain_result == AcceptResult.accepted:
                key = batch_operation.add(item)

            elif constrain_result == AcceptResult.last_accepted:
                key = batch_operation.add(item)
                batch_operation.signal_ready()

            elif constrain_result == AcceptResult.not_accepted:
                batch_operation.signal_ready()
                batch_operation = self._create_batch_operation()
                key = batch_operation.add(item)

        if process_this_context:
            self._register_ready()
            await batch_operation.process_batch()

        result = await batch_operation.get_result()
        return self._result_distribution_strategy(result.value, result.exception, key)
