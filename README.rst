safepy: safety belt for Python distributed services
===================================================

.. image:: https://img.shields.io/pypi/v/safepy.svg
    :target: https://pypi.python.org/pypi/safepy

.. image:: https://img.shields.io/:license-Apache_2-blue.svg
    :target: https://github.com/prokopst/safepy/blob/master/LICENSE

.. image:: https://img.shields.io/pypi/pyversions/safepy.svg
    :target: https://pypi.python.org/pypi/safepy

.. image:: https://api.shippable.com/projects/587b8d9379509c10004a444b/coverageBadge?branch=master
    :target: https://app.shippable.com/projects/587b8d9379509c10004a444b

Safepy (rhymes with safety) is a latency and fault tolerance library for Python 3.5 (or greater) inspired by `Hystrix <https://github.com/Netflix/Hystrix>`_, `Cloud Design Patterns <https://msdn.microsoft.com/en-us/library/dn568099.aspx>`_, `AWS Architecture Blog <https://www.awsarchitectureblog.com/>`_ and many others.

How to use the library
----------------------

You can either use the mechanisms as decorators:

.. code-block:: python

    from safety.retry_mechanism import retry_async

    class ProfileService(object):
        @retry_async(attempts=3, base_delay=1)
        async def get_profile(self, username):
            ...

Or to dynamically recreate methods:

.. code-block:: python

    from safety import retry

    class ProfileService(object):
        def __init__(self):
            self.get_profile = retry_async(attempts=3, base_delay=1)(
                self.get_profile
            )

        async def get_profile(self, username):
            ...

Retry
-----

.. code-block:: python

    from safepy import retry

    class ServiceA(object):
        @retry_async(attempts=3, base_delay=1)
        async def call():
            ...

Notes
^^^^^

* The default ``retry`` is an alias for ``retry_with_jitter_backoff``, a retry mechanism which uses `jitter backoff <https://www.awsarchitectureblog.com/2015/03/backoff.html>`_. For exponential backoff use ``retry_with_exponential_backoff``.
