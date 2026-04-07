"""
Global Exception Handlers for DCF Valuation Agent

This module provides centralized exception handling for FastAPI,
ensuring consistent error responses across all API endpoints.
"""
import logging
import traceback
from datetime import datetime
from typing import Any, Dict, Optional, Callable
from functools import wraps

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from backend.exceptions import (
    DCFException,
    ErrorCode,
    EXCEPTION_TO_STATUS_CODE,
    ValidationException,
    ResourceNotFoundException
)

logger = logging.getLogger(__name__)


class ErrorResponse:
    """
    Standardized error response structure.
    
    All API errors should follow this format for consistency.
    """
    
    def __init__(
        self,
        error: str,
        message: str,
        code: int,
        code_name: str,
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = True,
        request_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        path: Optional[str] = None
    ):
        self.error = error
        self.message = message
        self.code = code
        self.code_name = code_name
        self.details = details
        self.recoverable = recoverable
        self.request_id = request_id
        self.timestamp = timestamp or datetime.utcnow().isoformat()
        self.path = path
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON response"""
        result = {
            "success": False,
            "error": {
                "type": self.error,
                "message": self.message,
                "code": self.code,
                "code_name": self.code_name,
                "recoverable": self.recoverable,
                "timestamp": self.timestamp
            }
        }
        if self.details:
            result["error"]["details"] = self.details
        if self.request_id:
            result["error"]["request_id"] = self.request_id
        if self.path:
            result["error"]["path"] = self.path
        return result
    
    def to_json_response(self, status_code: int = 500) -> JSONResponse:
        """Convert to FastAPI JSONResponse"""
        return JSONResponse(
            content=self.to_dict(),
            status_code=status_code,
            media_type="application/json"
        )


class ExceptionHandlerMiddleware(BaseHTTPMiddleware):
    """
    Middleware for catching and handling all unhandled exceptions.
    
    This middleware ensures that:
    1. All exceptions are logged properly
    2. All error responses follow the standard format
    3. Request context is preserved in error responses
    """
    
    def __init__(self, app: ASGIApp, debug: bool = False):
        super().__init__(app)
        self.debug = debug
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and catch any exceptions"""
        request_id = request.headers.get("X-Request-ID", self._generate_request_id())
        
        try:
            response = await call_next(request)
            # Add request ID to response headers
            response.headers["X-Request-ID"] = request_id
            return response
            
        except Exception as exc:
            # Log the exception
            logger.error(
                f"Unhandled exception on {request.method} {request.url.path}",
                exc_info=(type(exc), exc, exc.__traceback__) if self.debug else None
            )
            
            # Handle the exception and return appropriate response
            error_response = self._handle_exception(
                exc,
                request_id=request_id,
                path=str(request.url.path)
            )
            
            return error_response.to_json_response()
    
    def _handle_exception(
        self,
        exc: Exception,
        request_id: Optional[str] = None,
        path: Optional[str] = None
    ) -> ErrorResponse:
        """Convert exception to standardized error response"""
        
        # Handle DCFException (our custom exceptions)
        if isinstance(exc, DCFException):
            return ErrorResponse(
                error=exc.__class__.__name__,
                message=exc.message,
                code=exc.code.value,
                code_name=exc.code.name,
                details=exc.details,
                recoverable=exc.is_recoverable,
                request_id=request_id,
                path=path
            )
        
        # Handle validation errors from FastAPI/Pydantic
        if isinstance(exc, ValidationException):
            return ErrorResponse(
                error="ValidationError",
                message=str(exc),
                code=ErrorCode.VALIDATION_ERROR.value,
                code_name=ErrorCode.VALIDATION_ERROR.name,
                recoverable=True,
                request_id=request_id,
                path=path
            )
        
        # Handle resource not found
        if isinstance(exc, ResourceNotFoundException):
            return ErrorResponse(
                error="ResourceNotFound",
                message=str(exc),
                code=ErrorCode.RESOURCE_NOT_FOUND.value,
                code_name=ErrorCode.RESOURCE_NOT_FOUND.name,
                recoverable=False,
                request_id=request_id,
                path=path
            )
        
        # Handle other exceptions - treat as unknown error
        error_message = str(exc) or "An unexpected error occurred"
        
        return ErrorResponse(
            error="InternalServerError",
            message=error_message,
            code=ErrorCode.UNKNOWN_ERROR.value,
            code_name=ErrorCode.UNKNOWN_ERROR.name,
            recoverable=True,
            request_id=request_id,
            path=path
        )
    
    def _generate_request_id(self) -> str:
        """Generate a unique request ID"""
        import uuid
        return str(uuid.uuid4())[:8]


def get_status_code_for_exception(exc: Exception) -> int:
    """
    Get the appropriate HTTP status code for an exception.
    
    Returns the status code based on the exception type mapping,
    defaulting to 500 for unknown exceptions.
    """
    for exception_class, status_code in EXCEPTION_TO_STATUS_CODE.items():
        if isinstance(exc, exception_class):
            return status_code
    return 500


def handle_dcf_exception(exc: DCFException) -> JSONResponse:
    """
    Convert a DCFException to a JSONResponse.
    
    Convenience function for use in try-except blocks.
    """
    status_code = get_status_code_for_exception(exc)
    
    error_response = ErrorResponse(
        error=exc.__class__.__name__,
        message=exc.message,
        code=exc.code.value,
        code_name=exc.code.name,
        details=exc.details,
        recoverable=exc.is_recoverable
    )
    
    return error_response.to_json_response(status_code)


def safe_endpoint(func: Callable) -> Callable:
    """
    Decorator to wrap endpoint functions with standardized exception handling.
    
    Usage:
        @router.get("/example")
        @safe_endpoint
        async def example_endpoint():
            # Your code here
            pass
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except DCFException as e:
            logger.warning(f"DCFException in {func.__name__}: {e}")
            return handle_dcf_exception(e)
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            error_response = ErrorResponse(
                error="InternalServerError",
                message=str(e),
                code=ErrorCode.UNKNOWN_ERROR.value,
                code_name=ErrorCode.UNKNOWN_ERROR.name,
                recoverable=True
            )
            return error_response.to_json_response(500)
    return wrapper


def log_exception(func: Callable) -> Callable:
    """
    Decorator to log exceptions without changing response behavior.
    
    Use this decorator to ensure exceptions are logged before being
    re-raised or handled elsewhere.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(
                f"Exception in {func.__name__}: {type(e).__name__}: {e}",
                exc_info=True
            )
            raise
    return wrapper


class ExceptionContext:
    """
    Context manager for exception handling with rollback support.
    
    Usage:
        try:
            with ExceptionContext("operation_name", ticker="AAPL"):
                # Your code here
                pass
        except DCFException as e:
            # Handle the exception
            pass
    """
    
    def __init__(
        self,
        operation: str,
        ticker: Optional[str] = None,
        workflow_id: Optional[str] = None,
        reraise: bool = True,
        log_level: str = "error"
    ):
        self.operation = operation
        self.ticker = ticker
        self.workflow_id = workflow_id
        self.reraise = reraise
        self.log_level = log_level
        self.exception: Optional[Exception] = None
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val is not None:
            self.exception = exc_val
            
            # Build log message
            log_msg = f"Error in {self.operation}"
            if self.ticker:
                log_msg += f" (ticker={self.ticker})"
            if self.workflow_id:
                log_msg += f" (workflow={self.workflow_id})"
            log_msg += f": {exc_type.__name__}: {exc_val}"
            
            # Log at appropriate level
            if self.log_level == "warning":
                logger.warning(log_msg)
            else:
                logger.error(log_msg, exc_info=True)
            
            # Convert if it's not already a DCFException
            if not isinstance(exc_val, DCFException):
                # Wrap in a generic DCFException
                from backend.exceptions import AgentException
                new_exc = AgentException(
                    message=str(exc_val),
                    cause=exc_val
                )
                # Replace the exception
                exc_val = new_exc
            
            if self.reraise:
                return False  # Re-raise the exception
            else:
                return True  # Suppress the exception
    
    def is_error_type(self, exc_type: type) -> bool:
        """Check if the caught exception is of a specific type"""
        return self.exception is not None and isinstance(self.exception, exc_type)


def retry_on_exception(
    max_attempts: int = 3,
    delay_seconds: float = 1.0,
    backoff_factor: float = 2.0,
    exceptions: tuple = (Exception,)
) -> Callable:
    """
    Decorator to retry a function on exception.
    
    Args:
        max_attempts: Maximum number of attempts
        delay_seconds: Initial delay between retries
        backoff_factor: Multiplier for delay after each attempt
        exceptions: Tuple of exception types to catch
    
    Usage:
        @retry_on_exception(max_attempts=3, delay_seconds=1.0)
        async def unreliable_function():
            # Your code here
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            import asyncio
            import time
            
            last_exception = None
            delay = delay_seconds
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"All {max_attempts} attempts failed for {func.__name__}: {e}"
                        )
                        raise
                    
                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed for "
                        f"{func.__name__}: {e}. Retrying in {delay}s..."
                    )
                    
                    await asyncio.sleep(delay)
                    delay *= backoff_factor
            
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator
