import math


def default_exception_evaluator(e):
    return True


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

    def __call__(self, attempt: int) -> float:
        return min(self._cap, self._base_delay * self._random_generator.uniform(0, 2 ** attempt))


class ExponentialBackoffStrategy(object):
    """
    Implementation of the exponential backoff, more precisely binary exponential backoff.
    """
    def __init__(self, base_delay: float, cap: float=math.inf):
        _values_sanity_check(base_delay, cap)

        self._base_delay = base_delay
        self._cap = cap

    def __call__(self, attempt: int) -> float:
        return min(self._cap, self._base_delay * (2 ** attempt))