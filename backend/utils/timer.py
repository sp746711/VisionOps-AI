"""VisionOps AI — Timer Utilities.

Reusable timer helpers for performance measurement: synchronous timer,
async timer, context manager, and function decorator.

Usage:
    from backend.utils.timer import Timer, timeit

    with Timer() as t:
        do_work()
    print(t.elapsed)
"""

from __future__ import annotations

import asyncio
import functools
import logging
import time
from collections.abc import Awaitable, Callable
from typing import Any, ParamSpec, TypeVar

logger = logging.getLogger("visionops.utils.timer")

P = ParamSpec("P")
R = TypeVar("R")


# ---------------------------------------------------------------------------
# Timer class
# ---------------------------------------------------------------------------


class Timer:
    """Synchronous timer for measuring elapsed time.

    Supports manual start/stop, context manager usage, and provides
    elapsed time in seconds as well as a human-readable formatted string.

    Examples:
        >>> timer = Timer()
        >>> timer.start()
        >>> ... do work ...
        >>> timer.stop()
        >>> print(timer.elapsed)

        >>> with Timer() as t:
        ...     do_work()
        ...     print(t.elapsed)
    """

    def __init__(self) -> None:
        self._start_time: float | None = None
        self._stop_time: float | None = None
        self._elapsed: float = 0.0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> Timer:
        """Start the timer.

        Returns:
            Self for chaining.

        Raises:
            RuntimeError: If the timer is already running.
        """
        if self._start_time is not None and self._stop_time is None:
            raise RuntimeError("Timer is already running")

        self._start_time = time.perf_counter()
        self._stop_time = None
        self._elapsed = 0.0
        logger.debug("Timer started")
        return self

    def stop(self) -> float:
        """Stop the timer and return the elapsed seconds.

        Returns:
            Elapsed time in seconds.

        Raises:
            RuntimeError: If the timer was not started.
        """
        if self._start_time is None:
            raise RuntimeError("Timer was not started")

        self._stop_time = time.perf_counter()
        self._elapsed = self._stop_time - self._start_time
        logger.debug("Timer stopped: %.4f s", self._elapsed)
        return self._elapsed

    def reset(self) -> Timer:
        """Reset the timer to its initial state.

        Returns:
            Self for chaining.
        """
        self._start_time = None
        self._stop_time = None
        self._elapsed = 0.0
        return self

    @property
    def elapsed(self) -> float:
        """Return the elapsed time in seconds.

        If the timer is still running, returns the time since start.
        If stopped, returns the last measured interval. If never started,
        returns 0.0.

        Returns:
            Elapsed time in seconds.
        """
        if self._start_time is None:
            return 0.0
        if self._stop_time is None:
            return time.perf_counter() - self._start_time
        return self._elapsed

    @property
    def is_running(self) -> bool:
        """Check whether the timer is currently running.

        Returns:
            True if started and not yet stopped.
        """
        return self._start_time is not None and self._stop_time is None

    def format_elapsed(self, precision: int = 4) -> str:
        """Return a human-readable string of the elapsed time.

        Chooses the most appropriate unit (s, ms, us) based on magnitude.

        Args:
            precision: Number of decimal places (default: 4).

        Returns:
            Formatted string, e.g. "1.2345 s" or "42.0000 ms".
        """
        secs = self.elapsed
        if secs < 0.001:
            return f"{secs * 1_000_000:.{precision}f} us"
        if secs < 1.0:
            return f"{secs * 1_000:.{precision}f} ms"
        return f"{secs:.{precision}f} s"

    # ------------------------------------------------------------------
    # Context manager
    # ------------------------------------------------------------------

    def __enter__(self) -> Timer:
        """Start the timer when entering a with block."""
        self.start()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """Stop the timer when exiting a with block."""
        self.stop()


# ---------------------------------------------------------------------------
# AsyncTimer class
# ---------------------------------------------------------------------------


class AsyncTimer:
    """Asynchronous timer that wraps an awaitable with elapsed measurement.

    Examples:
        >>> async with AsyncTimer() as t:
        ...     await async_work()
        >>> print(t.elapsed)
    """

    def __init__(self) -> None:
        self._timer = Timer()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def start(self) -> AsyncTimer:
        """Start the timer asynchronously.

        Returns:
            Self for chaining.
        """
        self._timer.start()
        return self

    async def stop(self) -> float:
        """Stop the timer asynchronously and return elapsed seconds.

        Returns:
            Elapsed time in seconds.
        """
        return self._timer.stop()

    def reset(self) -> AsyncTimer:
        """Reset the timer to its initial state.

        Returns:
            Self for chaining.
        """
        self._timer.reset()
        return self

    @property
    def elapsed(self) -> float:
        """Return the elapsed time in seconds."""
        return self._timer.elapsed

    @property
    def is_running(self) -> bool:
        """Check whether the timer is currently running."""
        return self._timer.is_running

    def format_elapsed(self, precision: int = 4) -> str:
        """Return a human-readable string of the elapsed time.

        Args:
            precision: Number of decimal places (default: 4).

        Returns:
            Formatted string.
        """
        return self._timer.format_elapsed(precision)

    # ------------------------------------------------------------------
    # Async context manager
    # ------------------------------------------------------------------

    async def __aenter__(self) -> AsyncTimer:
        """Start the timer when entering an async with block."""
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object | None,
    ) -> None:
        """Stop the timer when exiting an async with block."""
        await self.stop()


# ---------------------------------------------------------------------------
# Decorator
# ---------------------------------------------------------------------------


def timeit(
    func: Callable[P, R] | Callable[P, Awaitable[R]],
) -> Callable[P, R | Awaitable[R]]:
    """Decorator that logs the execution time of a function.

    Works with both sync and async functions. Logs at INFO level with the
    function name and elapsed time.

    Args:
        func: The function to wrap.

    Returns:
        Wrapped function that logs its execution time.

    Example:
        >>> @timeit
        ... def compute():
        ...     return sum(range(1000))

        >>> @timeit
        ... async def fetch():
        ...     await asyncio.sleep(0.1)
    """

    if asyncio.iscoroutinefunction(func):

        @functools.wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            timer = Timer()
            timer.start()
            try:
                result = await func(*args, **kwargs)  # type: ignore[misc]
                return result  # type: ignore[return-value]
            finally:
                timer.stop()
                logger.info(
                    "%s completed in %.4f s",
                    func.__qualname__,
                    timer.elapsed,
                )

        return async_wrapper  # type: ignore[return-value]
    else:

        @functools.wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            timer = Timer()
            timer.start()
            try:
                return func(*args, **kwargs)
            finally:
                timer.stop()
                logger.info(
                    "%s completed in %.4f s",
                    func.__qualname__,
                    timer.elapsed,
                )

        return sync_wrapper  # type: ignore[return-value]
