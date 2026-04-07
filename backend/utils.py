"""
Retry and Timeout Utilities for DCF Valuation Agent

This module provides decorators and utilities for handling retries,
timeouts, and error recovery in service operations.
"""
import asyncio
import logging
import time
from functools import wraps
from typing import Callable, Optional, Tuple, Any, List, Type

logger = logging.getLogger(__name__)


class RetryableError(Exception):
    """Base exception for errors that should trigger a retry"""
    pass


def retry_with_backoff(
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
    max_delay: float = 60.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None
) -> Callable:
    """
    Decorator for retrying a function with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay between retries (seconds)
        backoff_factor: Multiplier for delay after each attempt
        max_delay: Maximum delay between retries (seconds)
        exceptions: Tuple of exception types to catch and retry
        on_retry: Optional callback function(exc, attempt) called before each retry
    
    Usage:
        @retry_with_backoff(max_attempts=3, initial_delay=1.0, backoff_factor=2.0)
        async def unreliable_operation():
            # Your code here
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            last_exception = None
            delay = initial_delay
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    
                    if on_retry:
                        on_retry(e, attempt)
                    
                    await asyncio.sleep(delay)
                    delay = min(delay * backoff_factor, max_delay)
            
            if last_exception:
                raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            last_exception = None
            delay = initial_delay
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"Function {func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for {func.__name__}: {e}. "
                        f"Retrying in {delay:.1f}s..."
                    )
                    
                    if on_retry:
                        on_retry(e, attempt)
                    
                    time.sleep(delay)
                    delay = min(delay * backoff_factor, max_delay)
            
            if last_exception:
                raise last_exception
        
        # Return appropriate wrapper based on whether function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def timeout(seconds: float, default: Any = None) -> Callable:
    """
    Decorator to add timeout to a function.
    
    Args:
        seconds: Timeout in seconds
        default: Default value to return on timeout (if None, raises TimeoutError)
    
    Usage:
        @timeout(seconds=30.0, default=None)
        async def long_operation():
            # Your code here
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                return await asyncio.wait_for(func(*args, **kwargs), timeout=seconds)
            except asyncio.TimeoutError:
                logger.warning(f"Function {func.__name__} timed out after {seconds}s")
                if default is not None:
                    return default
                raise
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            result = None
            completed = False
            
            def run_with_timeout():
                nonlocal result, completed
                result = func(*args, **kwargs)
                completed = True
            
            import threading
            thread = threading.Thread(target=run_with_timeout)
            thread.daemon = True
            thread.start()
            thread.join(timeout=seconds)
            
            if not completed:
                logger.warning(f"Function {func.__name__} timed out after {seconds}s")
                if default is not None:
                    return default
                raise TimeoutError(f"Function {func.__name__} timed out after {seconds}s")
            
            return result
        
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def circuit_breaker(
    failure_threshold: int = 5,
    recovery_timeout: float = 60.0,
    expected_exception: Type[Exception] = Exception
) -> Callable:
    """
    Decorator to implement circuit breaker pattern.
    
    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Time to wait before attempting recovery (seconds)
        expected_exception: Exception type that triggers circuit breaker
    
    Usage:
        @circuit_breaker(failure_threshold=5, recovery_timeout=60.0)
        async def unreliable_service():
            # Your code here
            pass
    """
    def decorator(func: Callable) -> Callable:
        # Circuit states
        CLOSED = "closed"      # Normal operation
        OPEN = "open"          # Failing, reject calls
        HALF_OPEN = "half_open"  # Testing recovery
        
        func._circuit_state = {
            "state": CLOSED,
            "failure_count": 0,
            "last_failure_time": None,
            "last_success_time": None
        }
        
        @wraps(func)
        async def wrapper(*args, **kwargs):
            state = func._circuit_state
            
            if state["state"] == OPEN:
                # Check if recovery timeout has passed
                if time.time() - state["last_failure_time"] >= recovery_timeout:
                    logger.info(f"Circuit breaker for {func.__name__}: OPEN -> HALF_OPEN")
                    state["state"] = HALF_OPEN
                else:
                    raise RetryableError(
                        f"Circuit breaker is OPEN for {func.__name__}. "
                        f"Recovery attempt in {recovery_timeout - (time.time() - state['last_failure_time']):.1f}s"
                    )
            
            try:
                result = await func(*args, **kwargs)
                
                # Success - update state
                if state["state"] == HALF_OPEN:
                    logger.info(f"Circuit breaker for {func.__name__}: HALF_OPEN -> CLOSED")
                    state["state"] = CLOSED
                    state["failure_count"] = 0
                
                state["last_success_time"] = time.time()
                return result
                
            except expected_exception as e:
                state["failure_count"] += 1
                state["last_failure_time"] = time.time()
                
                if state["failure_count"] >= failure_threshold:
                    logger.warning(
                        f"Circuit breaker for {func.__name__}: CLOSED -> OPEN "
                        f"(failures: {state['failure_count']})"
                    )
                    state["state"] = OPEN
                
                raise
        
        # Add helper methods
        wrapper.get_circuit_state = lambda: func._circuit_state["state"]
        wrapper.reset_circuit = lambda: (
            func._circuit_state.update({
                "state": CLOSED,
                "failure_count": 0,
                "last_failure_time": None
            })
        )
        
        return wrapper
    
    return decorator


def fallback(default_value: Any = None, log_warning: bool = True) -> Callable:
    """
    Decorator to provide a fallback value on exception.
    
    Args:
        default_value: Value to return on exception
        log_warning: Whether to log a warning when fallback is used
    
    Usage:
        @fallback(default_value=[], log_warning=True)
        async def get_data():
            # Your code here
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                if log_warning:
                    logger.warning(f"Falling back to default value for {func.__name__}: {e}")
                return default_value
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_warning:
                    logger.warning(f"Falling back to default value for {func.__name__}: {e}")
                return default_value
        
        if asyncio.iscoroutinefunction(func):
            return wrapper
        else:
            return sync_wrapper
    
    return decorator


class RateLimiter:
    """
    Simple rate limiter to prevent exceeding API limits.
    
    Usage:
        limiter = RateLimiter(max_calls=10, time_window=60.0)
        
        @limiter
        async def api_call():
            # Your code here
            pass
    """
    
    def __init__(self, max_calls: int, time_window: float):
        """
        Args:
            max_calls: Maximum number of calls allowed in time window
            time_window: Time window in seconds
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls: List[float] = []
        self._lock = asyncio.Lock() if asyncio.get_event_loop().is_running() else None
    
    def __call__(self, func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            import asyncio
            current_time = time.time()
            
            async with asyncio.Lock() if self._lock else _DummyLock():
                # Remove calls outside time window
                self.calls = [
                    call_time for call_time in self.calls
                    if current_time - call_time < self.time_window
                ]
                
                if len(self.calls) >= self.max_calls:
                    sleep_time = self.time_window - (current_time - self.calls[0])
                    if sleep_time > 0:
                        logger.warning(
                            f"Rate limit reached for {func.__name__}. "
                            f"Sleeping for {sleep_time:.1f}s"
                        )
                        await asyncio.sleep(sleep_time)
                        self.calls = [
                            call_time for call_time in self.calls
                            if time.time() - call_time < self.time_window
                        ]
                
                self.calls.append(time.time())
                return await func(*args, **kwargs)
        
        return wrapper


class _DummyLock:
    """Dummy async context manager for when no event loop is running"""
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        pass


def batch_with_retry(
    batch_size: int = 10,
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0
) -> Callable:
    """
    Decorator to process items in batches with retry on failure.
    
    Args:
        batch_size: Number of items to process per batch
        max_attempts: Maximum retry attempts per batch
        delay: Initial delay between retries
        backoff: Backoff multiplier
    
    Usage:
        @batch_with_retry(batch_size=10, max_attempts=3)
        async def process_items(items: List[str]) -> List[Result]:
            # Your batch processing code here
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Extract items from kwargs or use first arg if it's a list
            items = kwargs.get('items', args[1] if len(args) > 1 else [])
            
            if not items:
                return []
            
            results = []
            current_delay = delay
            
            for i in range(0, len(items), batch_size):
                batch = items[i:i + batch_size]
                last_exception = None
                
                for attempt in range(1, max_attempts + 1):
                    try:
                        batch_results = await func(batch, *args, **kwargs)
                        results.extend(batch_results if isinstance(batch_results, list) else [batch_results])
                        break
                    except Exception as e:
                        last_exception = e
                        
                        if attempt == max_attempts:
                            logger.error(
                                f"Batch {i//batch_size + 1} failed after {max_attempts} attempts: {e}"
                            )
                            # Continue with next batch instead of failing completely
                            break
                        
                        logger.warning(
                            f"Batch {i//batch_size + 1} attempt {attempt} failed: {e}. "
                            f"Retrying in {current_delay:.1f}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                
                if last_exception and not results:
                    raise last_exception
            
            return results
        
        return wrapper
    
    return decorator
