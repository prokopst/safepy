"""
:license: Apache2, see LICENSE for more details.
"""
import asyncio
import functools
import math
import random
import logging
from typing import Callable

from safepy.retry_mechanism.retry_common import default_exception_evaluator, JitterBackoffStrategy, \
    ExponentialBackoffStrategy

logger = logging.getLogger(__name__)


def retry_async_generic(attempts: int, on_exception: Callable[[Exception], bool]=default_exception_evaluator,
                        backoff_strategy: Callable[[int], float]=lambda x: 1.0):
    if attempts < 1:
        raise ValueError("attempts lower than 1")

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_attempt = attempts - 1

            # PyCharm coverage thinks range(0, 0) is not covered, by it's not even possible,
            # the check is above. Outrageous!
            for attempt in range(0, attempts):
                try:
                    logger.info("Attempt #%d", attempt)
                    result = await func(*args, **kwargs)
                    return result

                except Exception as e:
                    logger.exception("Attempt #%d failed", attempt)
                    if attempt == last_attempt:
                        raise

                    if not on_exception(e):
                        raise

                current_delay = backoff_strategy(attempt)
                await asyncio.sleep(current_delay)

        return wrapper
    return decorator


def retry_async_with_jitter_backoff(
    attempts: int, base_delay: float, on_exception: Callable[[Exception], bool]=default_exception_evaluator,
    maximum_delay: float=math.inf
):
    """
    Retry with so called "jitter backoff" algorithm. It's basically random between 0 and exponential backoff
    for current attempt capped by maximum_delay.

    :param attempts: number of attempts
    :param base_delay: base_delay for the jitter backoff
    :param on_exception: function to evaluate exceptions
    :param maximum_delay: the cap of the individual delay
    """
    random_generator = random.Random()
    jitter_backoff_strategy = JitterBackoffStrategy(random_generator, base_delay, maximum_delay)

    return retry_async_generic(attempts, on_exception, jitter_backoff_strategy)


def retry_async_with_exponential_backoff(
    attempts: int, base_delay: float, on_exception: Callable[[Exception], bool]=default_exception_evaluator,
    maximum_delay: float=math.inf
):
    """
    Retry with classical exponential backoff algorithm.

    :param attempts: number of attempts
    :param base_delay: base_delay for the jitter backoff
    :param on_exception: function to evaluate exceptions
    :param maximum_delay: the cap of the individual delay
    """
    exponential_backoff_strategy = ExponentialBackoffStrategy(base_delay, maximum_delay)

    return retry_async_generic(attempts, on_exception, exponential_backoff_strategy)


# default retry is the one with jitter backoff
retry_async = retry_async_with_jitter_backoff
