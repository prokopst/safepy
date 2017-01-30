from asyncio import get_event_loop, CancelledError
from unittest import TestCase
from unittest.mock import Mock, call
from deasync import deasync
from safepy.retry_mechanism import ExponentialBackoffStrategy, JitterBackoffStrategy, retry_generic, \
    retry_with_jitter_backoff, retry_with_exponential_backoff

loop = get_event_loop()


def async_mock_call(mock):
    async def wrapper():
        return mock()

    return wrapper


class DummyError(Exception):
    pass


class TestRetry(TestCase):
    def test_retry_fails_on_invalid_attempts(self):
        for attempts in [-1, 0]:
            with self.subTest(value=attempts):
                with self.assertRaises(ValueError):
                    @retry_generic(attempts=attempts)
                    async def dummy():
                        pass

    @deasync
    async def test_retry_succeeds(self):
        @retry_generic(attempts=1)
        async def function():
            return 42

        result = await function()
        self.assertEqual(42, result)

    @deasync
    async def test_retry_fails(self):
        @retry_generic(attempts=1)
        async def function():
            raise DummyError()

        with self.assertRaises(DummyError):
            await function()

    @deasync
    async def test_retry_succeeds_after_retries(self):
        mock = Mock(side_effect=[DummyError(), DummyError(), 42])

        @retry_generic(3, DummyError)
        async def function(*args):
            return mock(*args)

        result = await function(21)

        self.assertEqual(42, result)

        mock.assert_has_calls([call(21), call(21), call(21)])

    @deasync
    async def test_retry_fails_after_retries(self):
        mock = Mock(side_effect=[DummyError(), DummyError(), DummyError()])

        @retry_generic(3, DummyError)
        async def function(*args):
            return mock(*args)

        with self.assertRaises(DummyError):
            await function(21)

        mock.assert_has_calls([call(21), call(21), call(21)])

    @deasync
    async def test_retry_fails_on_unexpected_exception(self):
        class TotallyUnexpectedError(Exception):
            pass

        mock = Mock(side_effect=[DummyError(), TotallyUnexpectedError(), 42])

        @retry_generic(3, DummyError)
        async def function(*args):
            return mock(*args)

        with self.assertRaises(TotallyUnexpectedError):
            await function(21)

        mock.assert_has_calls([call(21), call(21)])

    @deasync
    async def test_retry_returns_last_exception_on_cancel(self):
        mock = Mock(side_effect=[DummyError(), CancelledError()])

        @retry_generic(3, DummyError, on_cancel_raise_last=False)
        async def function(*args):
            return mock(*args)

        with self.assertRaises(CancelledError):
            await function(21)

        mock.assert_has_calls([call(21), call(21)])

    @deasync
    async def test_retry_returns_last_exception_on_cancel(self):
        mock = Mock(side_effect=[DummyError(), CancelledError()])

        @retry_generic(3, DummyError)
        async def function(*args):
            return mock(*args)

        with self.assertRaises(DummyError):
            await function(21)

        mock.assert_has_calls([call(21), call(21)])

    @deasync
    async def test_retry_returns_cancel_on_cancel_if_no_exception_available(self):
        mock = Mock(side_effect=[CancelledError(), 42])

        @retry_generic(3, DummyError)
        async def function(*args):
            return mock(*args)

        with self.assertRaises(CancelledError):
            await function(21)

        mock.assert_has_calls([call(21)])


class TestPublicRetryDecorators(TestCase):
    """
    More like a sanity test for all public retry mechanisms.
    """
    @deasync
    async def test_public_retry_decorators_do_retry(self):
        for retry in (retry_with_jitter_backoff, retry_with_exponential_backoff):
            with self.subTest(retry=retry):
                mock = Mock(side_effect=[DummyError, 42])

                async def function(arg):
                    return mock(arg)

                result = await retry(2, 0, DummyError)(function)(21)

                self.assertEqual(result, 42)
                mock.assert_has_calls([call(21), call(21)])


class TestExponentialBackoffStrategy(TestCase):
    TEST_SANITY_DATA = [(-1, 0), (0, -1), (1, 0)]
    TEST_DATA = [(0, 3), (1, 6), (2, 12), (3, 24), (4, 48)]
    BASE_DELAY = 3

    def test_exponential_backoff_strategy_gets_expected_values(self):
        backoff_strategy = ExponentialBackoffStrategy(self.BASE_DELAY)

        for attempt, expected_value in self.TEST_DATA:
            value = backoff_strategy(attempt)
            self.assertEqual(value, expected_value)

    def test_exponential_backoff_strategy_is_capped(self):
        maximum = 10.5
        backoff_strategy = ExponentialBackoffStrategy(self.BASE_DELAY, maximum)

        for attempt, expected_value in self.TEST_DATA:
            expected_value = min(maximum, expected_value)
            value = backoff_strategy(attempt)
            self.assertEqual(value, expected_value)

    def test_jitter_backoff_raises_on_invalid_params(self):
        for base_delay, maximum in self.TEST_SANITY_DATA:
            with self.subTest(base_delay=base_delay, maximum=maximum):
                with self.assertRaises(ValueError):
                    ExponentialBackoffStrategy(base_delay, maximum)


class TestJitterBackoffStrategy(TestCase):
    TEST_SANITY_DATA = [(-1, 0), (0, -1), (1, 0)]
    TEST_DATA = [(0, 33), (1, 66), (2, 212), (3, 424), (4, 121)]
    BASE_DELAY = 3

    def test_jitter_backoff_strategy_gets_expected_values(self):
        uniform_mock = Mock(side_effect=[expected_value for _, expected_value in self.TEST_DATA])
        random_generator_mock = Mock(uniform=uniform_mock)

        backoff_strategy = JitterBackoffStrategy(random_generator_mock, 1)

        for attempt, expected_value in self.TEST_DATA:
            value = backoff_strategy(attempt)
            self.assertEqual(value, expected_value)

        uniform_mock.assert_has_calls([call(0, (2 ** attempt)) for attempt, _ in self.TEST_DATA])

    def test_jitter_backoff_strategy_is_capped(self):
        uniform_mock = Mock(side_effect=[expected_value for _, expected_value in self.TEST_DATA])
        random_generator_mock = Mock(uniform=uniform_mock)

        maximum = 3.5
        backoff_strategy = JitterBackoffStrategy(random_generator_mock, 1, maximum)

        for attempt, expected_value in self.TEST_DATA:
            expected_value = min(maximum, expected_value)
            with self.subTest(attempt=attempt, expected_value=expected_value):
                value = backoff_strategy(attempt)
                self.assertEqual(value, expected_value)

        uniform_mock.assert_has_calls([call(0, (2 ** attempt)) for attempt, _ in self.TEST_DATA])

    def test_jitter_backoff_raises_on_invalid_params(self):
        for base_delay, maximum in self.TEST_SANITY_DATA:
            with self.subTest(base_delay=base_delay, maximum=maximum):
                with self.assertRaises(ValueError):
                    JitterBackoffStrategy(object(), base_delay, maximum)
