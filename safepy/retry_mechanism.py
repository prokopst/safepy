"""
:license: Apache2, see LICENSE for more details.
"""
import asyncio
import functools
import math
import random


def _values_sanity_check(base_delay, maximum):
    if base_delay < 0:
        raise ValueError("base_delay < 0")

    if maximum < 0:
        raise ValueError("maximum < 0")

    if base_delay > maximum:
        raise ValueError(base_delay > maximum)


class JitterBackoffStrategy(object):
    """
    Exponential backoff with randomness called "jitter backoff" (full jitter variant) based on:

        https://www.awsarchitectureblog.com/2015/03/backoff.html

    Or the link above does not work, see:

        https://web.archive.org/web/20150323040719/http://www.awsarchitectureblog.com/2015/03/backoff.html

    And if the one above does not work too than you're doomed.
    """
    def __init__(self, random_generator, base_delay, cap=math.inf):
        _values_sanity_check(base_delay, cap)

        self._base_delay = base_delay
        self._cap = cap
        self._random_generator = random_generator

    def __call__(self, attempt):
        return min(self._cap, self._base_delay * self._random_generator.uniform(0, 2 ** attempt))


class ExponentialBackoffStrategy(object):
    """
    Implementation of the exponential backoff, more precisely binary exponential backoff.
    """
    def __init__(self, base_delay: float, cap: float=math.inf):
        _values_sanity_check(base_delay, cap)

        self._base_delay = base_delay
        self._cap = cap

    def __call__(self, attempt):
        return min(self._cap, self._base_delay * (2 ** attempt))


def retry_generic(attempts, exceptions=(Exception,), backoff_strategy=lambda x: 1, on_cancel_raise_last=True):
    if attempts < 1:
        raise ValueError("attempts lower than 1")

    def decorator(function):
        @functools.wraps(function)
        async def wrapper(*args, **kwargs):
            last_attempt = attempts - 1
            last_exception = None

            # PyCharm coverage thinks range(0, 0) is not covered, by it's not even possible,
            # the check is above. Outrageous!
            for attempt in range(0, attempts):
                if attempt != 0:
                    current_delay = backoff_strategy(attempt)
                    asyncio.sleep(current_delay)
                try:
                    return await function(*args, **kwargs)

                except exceptions as e:
                    if attempt == last_attempt:
                        raise
                    last_exception = e

                except asyncio.CancelledError:
                    if on_cancel_raise_last and last_exception is not None:
                        raise last_exception.with_traceback(last_exception.__traceback__)
                    raise

        return wrapper
    return decorator


def retry_with_jitter_backoff(
    attempts: int, base_delay: float, exceptions=(Exception,),
    maximum_delay: float=math.inf, on_cancel_raise_last: bool=True
):
    """
    Retry with so called "jitter backoff" algorithm. It's basically random between 0 and exponential backoff
    for current attempt capped by maximum_delay.

    :param attempts: number of attempts
    :param base_delay: base_delay for the jitter backoff
    :param exceptions: a tuple/list of exceptions or a specific exception type
    :param maximum_delay: the cap of the individual delay
    :param on_cancel_raise_last: on CancelError raise last exception (if any)
    """
    random_generator = random.Random()
    jitter_backoff_strategy = JitterBackoffStrategy(random_generator, base_delay, maximum_delay)

    return retry_generic(attempts, exceptions, jitter_backoff_strategy, on_cancel_raise_last)


def retry_with_exponential_backoff(
    attempts: int, base_delay: float, exceptions=(Exception,),
    maximum_delay: float=math.inf, on_cancel_raise_last: bool=True
):
    """
    Retry with exponential backoff algorithm. It's basically random between 0 and exponential backoff
    for current attempt capped by maximum_delay.

    :param attempts: number of attempts
    :param base_delay: base_delay for the jitter backoff
    :param exceptions: a tuple/list of exceptions or a specific exception type
    :param maximum_delay: the cap of the individual delay
    :param on_cancel_raise_last: on CancelError raise last exception (if any)
    """
    exponential_backoff_strategy = ExponentialBackoffStrategy(base_delay, maximum_delay)

    return retry_generic(attempts, exceptions, exponential_backoff_strategy, on_cancel_raise_last)


# default retry is the one with jitter backoff
retry = retry_with_jitter_backoff
