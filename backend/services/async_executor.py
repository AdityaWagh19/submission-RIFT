"""
Phase 7: Async executor for blocking Algorand/IPFS operations.

Runs synchronous SDK calls (algod, asset creation, transfers) in a thread pool
to avoid blocking the asyncio event loop. NFT minting is CPU/IO bound and
blocks for ~4-5 seconds per mint.
"""
import asyncio
import functools
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Callable, TypeVar

logger = logging.getLogger(__name__)

# Shared executor for blocking operations; sized for concurrent mints
_executor: ThreadPoolExecutor | None = None
_MAX_WORKERS = 4


def get_executor() -> ThreadPoolExecutor:
    """Lazy-initialize thread pool executor."""
    global _executor
    if _executor is None:
        _executor = ThreadPoolExecutor(max_workers=_MAX_WORKERS, thread_name_prefix="algo_")
        logger.info(f"Thread pool executor initialized (max_workers={_MAX_WORKERS})")
    return _executor


T = TypeVar("T")


async def run_blocking(func: Callable[..., T], *args: Any, **kwargs: Any) -> T:
    """
    Run a blocking (synchronous) function in the thread pool.

    Use for: algod compile, asset creation, transfers, wait_for_confirmation.
    """
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        get_executor(),
        functools.partial(func, *args, **kwargs),
    )


def shutdown_executor() -> None:
    """Shutdown the thread pool on app lifecycle end."""
    global _executor
    if _executor:
        _executor.shutdown(wait=True)
        _executor = None
        logger.info("Thread pool executor shutdown")
