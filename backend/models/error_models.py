"""
Standardized Error Response Models for DCF Valuation Agent

This module provides Pydantic models for consistent API error responses
across all endpoints.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, List
from datetime import datetime
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Detailed error information"""
    type: str = Field(description="Error type/class name")
    message: str = Field(description="Human-readable error message")
    code: int = Field(description="Error code number")
    code_name: str = Field(description="Error code name")
    recoverable: bool = Field(default=True, description="Whether the error is recoverable")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Additional error details")
    request_id: Optional[str] = Field(default=None, description="Request tracking ID")
    path: Optional[str] = Field(default=None, description="Request path")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="Error timestamp"
    )
    
    class Config:
        json_schema_extra = {
            "example": {
                "type": "DatabaseConnectionError",
                "message": "Failed to connect to database",
                "code": 2001,
                "code_name": "DATABASE_CONNECTION_ERROR",
                "recoverable": True,
                "details": {"host": "localhost", "database": "dcf_db"},
                "request_id": "abc12345",
                "path": "/api/analysis/calculate",
                "timestamp": "2024-01-15T10:30:00.000Z"
            }
        }


class ErrorResponse(BaseModel):
    """Standardized error response for all API endpoints"""
    success: bool = Field(default=False, description="Always False for errors")
    error: ErrorDetail = Field(description="Error details")
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": False,
                "error": {
                    "type": "ValidationError",
                    "message": "Invalid ticker symbol",
                    "code": 1001,
                    "code_name": "VALIDATION_ERROR",
                    "recoverable": True,
                    "details": {"field": "ticker", "invalid_value": "INVALID!!!@#"},
                    "timestamp": "2024-01-15T10:30:00.000Z"
                }
            }
        }


class APIError(Exception):
    """
    Exception for API-level errors with standardized error response format.
    
    This exception can be raised in API endpoints and will be automatically
    converted to an ErrorResponse by the exception handlers.
    """
    
    def __init__(
        self,
        message: str,
        code: int = 1000,
        code_name: str = "UNKNOWN_ERROR",
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = True,
        status_code: int = 500
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.code_name = code_name
        self.details = details or {}
        self.recoverable = recoverable
        self.status_code = status_code
    
    def to_error_response(self, request_id: Optional[str] = None) -> ErrorResponse:
        """Convert to ErrorResponse model"""
        return ErrorResponse(
            success=False,
            error=ErrorDetail(
                type=self.__class__.__name__,
                message=self.message,
                code=self.code,
                code_name=self.code_name,
                recoverable=self.recoverable,
                details=self.details if self.details else None,
                request_id=request_id
            )
        )


# ============================================================================
# Common Error Factory Functions
# ============================================================================

def create_error_response(
    error_type: str,
    message: str,
    code: int,
    code_name: str,
    details: Optional[Dict[str, Any]] = None,
    recoverable: bool = True
) -> ErrorResponse:
    """
    Factory function to create standardized error responses.
    
    Usage:
        return create_error_response(
            error_type="ValidationError",
            message="Invalid input",
            code=1001,
            code_name="VALIDATION_ERROR",
            details={"field": "ticker"}
        )
    """
    return ErrorResponse(
        success=False,
        error=ErrorDetail(
            type=error_type,
            message=message,
            code=code,
            code_name=code_name,
            recoverable=recoverable,
            details=details
        )
    )


def validation_error(
    message: str,
    field: Optional[str] = None,
    invalid_value: Optional[Any] = None
) -> ErrorResponse:
    """Create a validation error response"""
    details = {}
    if field:
        details["field"] = field
    if invalid_value is not None:
        details["invalid_value"] = str(invalid_value)[:100]
    
    return create_error_response(
        error_type="ValidationError",
        message=message,
        code=1001,
        code_name="VALIDATION_ERROR",
        details=details if details else None,
        recoverable=True
    )


def not_found_error(
    resource_type: str,
    resource_id: str
) -> ErrorResponse:
    """Create a resource not found error response"""
    return create_error_response(
        error_type="ResourceNotFound",
        message=f"{resource_type} '{resource_id}' not found",
        code=1003,
        code_name="RESOURCE_NOT_FOUND",
        details={"resource_type": resource_type, "resource_id": resource_id},
        recoverable=False
    )


def database_error(
    message: str,
    operation: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None
) -> ErrorResponse:
    """Create a database error response"""
    error_details = details or {}
    if operation:
        error_details["operation"] = operation
    
    return create_error_response(
        error_type="DatabaseError",
        message=message,
        code=2002,
        code_name="DATABASE_QUERY_ERROR",
        details=error_details if error_details else None,
        recoverable=True
    )


def external_service_error(
    service_name: str,
    message: str,
    details: Optional[Dict[str, Any]] = None
) -> ErrorResponse:
    """Create an external service error response"""
    error_details = details or {}
    error_details["service_name"] = service_name
    
    return create_error_response(
        error_type="ExternalServiceError",
        message=message,
        code=7001,
        code_name="EXTERNAL_SERVICE_ERROR",
        details=error_details,
        recoverable=True
    )


# ============================================================================
# Success Response Helper
# ============================================================================

class SuccessResponse(BaseModel):
    """Standardized success response"""
    success: bool = Field(default=True)
    data: Optional[Any] = Field(default=None)
    message: Optional[str] = Field(default=None)
    request_id: Optional[str] = Field(default=None)
    
    @classmethod
    def create(
        cls,
        data: Any = None,
        message: Optional[str] = None,
        request_id: Optional[str] = None
    ) -> SuccessResponse:
        """Factory method to create a success response"""
        return cls(
            success=True,
            data=data,
            message=message,
            request_id=request_id
        )
    
    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "data": {"ticker": "AAPL", "per_share_value": 150.50},
                "message": "Operation completed successfully"
            }
        }


# ============================================================================
# Paginated Response Model
# ============================================================================

class PaginatedResponse(BaseModel):
    """Paginated response model for list endpoints"""
    success: bool = Field(default=True)
    data: List[Any] = Field(description="List of items")
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Items per page")
    has_next: bool = Field(description="Whether there are more pages")
    
    @classmethod
    def create(
        cls,
        items: List[Any],
        total: int,
        page: int = 1,
        page_size: int = 20
    ) -> PaginatedResponse:
        """Factory method to create a paginated response"""
        total_pages = (total + page_size - 1) // page_size
        return cls(
            success=True,
            data=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=page < total_pages
        )
