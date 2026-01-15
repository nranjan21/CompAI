"""
Retry utility for handling transient failures in agent operations.

Provides a decorator for retrying functions with exponential backoff.
"""

import time
import functools
from typing import Callable, Any, Optional, Type, Tuple
from app.core.config import config
from app.utils.logger import logger


def retry_on_failure(
    max_attempts: Optional[int] = None,
    delay: Optional[float] = None,
    backoff: Optional[float] = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
) -> Callable:
    """
    Decorator to retry a function on failure with exponential backoff.
    
    Args:
        max_attempts: Maximum number of attempts (default: from config)
        delay: Initial delay in seconds between retries (default: from config)
        backoff: Backoff multiplier for delay (default: from config)
        exceptions: Tuple of exception types to catch and retry on
        
    Returns:
        Decorated function with retry logic
        
    Example:
        @retry_on_failure(max_attempts=3, delay=1.0, backoff=2.0)
        def download_file(url):
            # function that might fail transiently
            pass
    """
    # Use config defaults if not specified
    max_attempts = max_attempts or config.agent.max_retries
    delay = delay or config.agent.retry_delay_seconds
    backoff = backoff or config.agent.retry_backoff_multiplier
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"❌ {func.__name__} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    logger.warning(
                        f"⚠️  {func.__name__} failed (attempt {attempt}/{max_attempts}): {e}. "
                        f"Retrying in {current_delay:.1f}s..."
                    )
                    
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            # This shouldn't be reached, but just in case
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator


def retry_with_context(
    operation_name: str,
    max_attempts: Optional[int] = None,
    delay: Optional[float] = None,
    backoff: Optional[float] = None,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
) -> Callable:
    """
    Similar to retry_on_failure but with a custom operation name for logging.
    
    Args:
        operation_name: Human-readable name for the operation (for logging)
        max_attempts: Maximum number of attempts (default: from config)
        delay: Initial delay in seconds between retries (default: from config)
        backoff: Backoff multiplier for delay (default: from config)
        exceptions: Tuple of exception types to catch and retry on
        
    Returns:
        Decorated function with retry logic
    """
    max_attempts = max_attempts or config.agent.max_retries
    delay = delay or config.agent.retry_delay_seconds
    backoff = backoff or config.agent.retry_backoff_multiplier
    
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"❌ {operation_name} failed after {max_attempts} attempts: {e}"
                        )
                        raise
                    
                    logger.warning(
                        f"⚠️  {operation_name} failed (attempt {attempt}/{max_attempts}): {e}. "
                        f"Retrying in {current_delay:.1f}s..."
                    )
                    
                    time.sleep(current_delay)
                    current_delay *= backoff
            
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator
