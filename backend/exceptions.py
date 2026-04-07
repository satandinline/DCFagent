"""
Custom Exception Classes for DCF Valuation Agent

This module defines a hierarchical exception system for consistent error handling
across the entire application.
"""
from typing import Any, Dict, Optional
from enum import Enum


class ErrorCode(Enum):
    """Error codes for the application"""
    # General errors (1000-1999)
    UNKNOWN_ERROR = 1000
    VALIDATION_ERROR = 1001
    CONFIGURATION_ERROR = 1002
    RESOURCE_NOT_FOUND = 1003
    DUPLICATE_RESOURCE = 1004
    
    # Database errors (2000-2999)
    DATABASE_CONNECTION_ERROR = 2001
    DATABASE_QUERY_ERROR = 2002
    DATABASE_TIMEOUT = 2003
    TRANSACTION_FAILED = 2004
    
    # Data fetch errors (3000-3999)
    DATA_FETCH_ERROR = 3001
    DATA_PARSE_ERROR = 3002
    DATA_VALIDATION_ERROR = 3003
    API_RATE_LIMIT = 3004
    API_AUTH_ERROR = 3005
    NETWORK_ERROR = 3006
    
    # Agent errors (4000-4999)
    AGENT_INIT_ERROR = 4001
    AGENT_EXECUTION_ERROR = 4002
    WORKFLOW_ERROR = 4003
    APPROVAL_TIMEOUT = 4004
    
    # Valuation errors (5000-5999)
    VALUATION_ERROR = 5001
    DCF_CALCULATION_ERROR = 5002
    PARAMETER_ERROR = 5003
    INSUFFICIENT_DATA = 5004
    
    # File processing errors (6000-6999)
    FILE_READ_ERROR = 6001
    FILE_WRITE_ERROR = 6002
    INVALID_FILE_FORMAT = 6003
    PDF_PARSING_ERROR = 6004
    
    # External service errors (7000-7999)
    LLM_SERVICE_ERROR = 7001
    EMAIL_SERVICE_ERROR = 7002
    SCHEDULER_ERROR = 7003


class DCFException(Exception):
    """
    Base exception for all DCF Agent exceptions.
    
    All custom exceptions should inherit from this class to enable
    centralized exception handling.
    """
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None,
        is_recoverable: bool = True
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.details = details or {}
        self.cause = cause
        self.is_recoverable = is_recoverable
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON serialization"""
        result = {
            "error": self.__class__.__name__,
            "message": self.message,
            "code": self.code.value,
            "code_name": self.code.name,
            "recoverable": self.is_recoverable
        }
        if self.details:
            result["details"] = self.details
        if self.cause and not isinstance(self.cause, DCFException):
            result["cause"] = str(self.cause)
        return result
    
    def __str__(self) -> str:
        if self.cause:
            return f"{self.message} (caused by: {self.cause})"
        return self.message


# ============================================================================
# Database Exceptions
# ============================================================================

class DatabaseException(DCFException):
    """Base class for database-related exceptions"""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.DATABASE_QUERY_ERROR,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(message, code, details, cause, is_recoverable=True)


class DatabaseConnectionError(DatabaseException):
    """Raised when database connection fails"""
    
    def __init__(
        self,
        message: str = "Failed to connect to database",
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message,
            ErrorCode.DATABASE_CONNECTION_ERROR,
            details,
            cause
        )
        self.is_recoverable = True  # Connection issues might be transient


class DatabaseQueryError(DatabaseException):
    """Raised when a database query fails"""
    
    def __init__(
        self,
        message: str = "Database query failed",
        query: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if query:
            details["query"] = query[:200]  # Truncate long queries
        super().__init__(
            message,
            ErrorCode.DATABASE_QUERY_ERROR,
            details,
            cause
        )


class DatabaseTimeoutError(DatabaseException):
    """Raised when database operation times out"""
    
    def __init__(
        self,
        message: str = "Database operation timed out",
        timeout_seconds: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if timeout_seconds:
            details["timeout_seconds"] = timeout_seconds
        super().__init__(
            message,
            ErrorCode.DATABASE_TIMEOUT,
            details,
            cause
        )


# ============================================================================
# Data Fetch Exceptions
# ============================================================================

class DataFetchException(DCFException):
    """Base class for data fetching exceptions"""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.DATA_FETCH_ERROR,
        ticker: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if ticker:
            details["ticker"] = ticker
        super().__init__(message, code, details, cause, is_recoverable=True)


class DataParseException(DataFetchException):
    """Raised when data parsing fails"""
    
    def __init__(
        self,
        message: str = "Failed to parse fetched data",
        ticker: Optional[str] = None,
        data_type: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if data_type:
            details["data_type"] = data_type
        super().__init__(
            message,
            ErrorCode.DATA_PARSE_ERROR,
            ticker,
            details,
            cause
        )


class APIRateLimitException(DataFetchException):
    """Raised when API rate limit is exceeded"""
    
    def __init__(
        self,
        message: str = "API rate limit exceeded",
        ticker: Optional[str] = None,
        retry_after: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if retry_after:
            details["retry_after_seconds"] = retry_after
        super().__init__(
            message,
            ErrorCode.API_RATE_LIMIT,
            ticker,
            details,
            cause
        )
        self.is_recoverable = True


class NetworkException(DataFetchException):
    """Raised when network communication fails"""
    
    def __init__(
        self,
        message: str = "Network communication failed",
        ticker: Optional[str] = None,
        url: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if url:
            details["url"] = url
        super().__init__(
            message,
            ErrorCode.NETWORK_ERROR,
            ticker,
            details,
            cause
        )
        self.is_recoverable = True


# ============================================================================
# Agent Exceptions
# ============================================================================

class AgentException(DCFException):
    """Base class for agent-related exceptions"""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.AGENT_EXECUTION_ERROR,
        agent_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if agent_name:
            details["agent_name"] = agent_name
        super().__init__(message, code, details, cause, is_recoverable=True)


class AgentInitException(AgentException):
    """Raised when agent initialization fails"""
    
    def __init__(
        self,
        message: str = "Failed to initialize agent",
        agent_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        super().__init__(
            message,
            ErrorCode.AGENT_INIT_ERROR,
            agent_name,
            details,
            cause
        )
        self.is_recoverable = False


class WorkflowException(AgentException):
    """Raised when workflow execution fails"""
    
    def __init__(
        self,
        message: str = "Workflow execution failed",
        workflow_id: Optional[str] = None,
        step: Optional[str] = None,
        agent_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if workflow_id:
            details["workflow_id"] = workflow_id
        if step:
            details["failed_step"] = step
        super().__init__(
            message,
            ErrorCode.WORKFLOW_ERROR,
            agent_name,
            details,
            cause
        )


class ApprovalTimeoutException(AgentException):
    """Raised when human approval times out"""
    
    def __init__(
        self,
        message: str = "Approval request timed out",
        approval_id: Optional[str] = None,
        timeout_minutes: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if approval_id:
            details["approval_id"] = approval_id
        if timeout_minutes:
            details["timeout_minutes"] = timeout_minutes
        super().__init__(
            message,
            ErrorCode.APPROVAL_TIMEOUT,
            details=details,
            cause=cause
        )
        self.is_recoverable = True


# ============================================================================
# Valuation Exceptions
# ============================================================================

class ValuationException(DCFException):
    """Base class for valuation-related exceptions"""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.VALUATION_ERROR,
        ticker: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if ticker:
            details["ticker"] = ticker
        super().__init__(message, code, details, cause, is_recoverable=False)


class DCFCalculationException(ValuationException):
    """Raised when DCF calculation fails"""
    
    def __init__(
        self,
        message: str = "DCF calculation failed",
        ticker: Optional[str] = None,
        calculation_step: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if calculation_step:
            details["calculation_step"] = calculation_step
        super().__init__(
            message,
            ErrorCode.DCF_CALCULATION_ERROR,
            ticker,
            details,
            cause
        )


class InsufficientDataException(ValuationException):
    """Raised when there's insufficient data for valuation"""
    
    def __init__(
        self,
        message: str = "Insufficient data for valuation",
        ticker: Optional[str] = None,
        missing_data: Optional[list] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if missing_data:
            details["missing_data"] = missing_data
        super().__init__(
            message,
            ErrorCode.INSUFFICIENT_DATA,
            ticker,
            details,
            cause
        )
        self.is_recoverable = True


class ParameterValidationException(ValuationException):
    """Raised when valuation parameters are invalid"""
    
    def __init__(
        self,
        message: str = "Invalid valuation parameters",
        ticker: Optional[str] = None,
        invalid_params: Optional[Dict[str, Any]] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if invalid_params:
            details["invalid_parameters"] = invalid_params
        super().__init__(
            message,
            ErrorCode.PARAMETER_ERROR,
            ticker,
            details,
            cause
        )
        self.is_recoverable = True


# ============================================================================
# File Processing Exceptions
# ============================================================================

class FileProcessingException(DCFException):
    """Base class for file processing exceptions"""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.FILE_READ_ERROR,
        file_path: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if file_path:
            details["file_path"] = file_path
        super().__init__(message, code, details, cause, is_recoverable=False)


class PDFParsingException(FileProcessingException):
    """Raised when PDF parsing fails"""
    
    def __init__(
        self,
        message: str = "Failed to parse PDF file",
        file_path: Optional[str] = None,
        page_number: Optional[int] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if page_number is not None:
            details["page_number"] = page_number
        super().__init__(
            message,
            ErrorCode.PDF_PARSING_ERROR,
            file_path,
            details,
            cause
        )


class InvalidFileFormatException(FileProcessingException):
    """Raised when file format is invalid"""
    
    def __init__(
        self,
        message: str = "Invalid file format",
        file_path: Optional[str] = None,
        expected_format: Optional[str] = None,
        actual_format: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if expected_format:
            details["expected_format"] = expected_format
        if actual_format:
            details["actual_format"] = actual_format
        super().__init__(
            message,
            ErrorCode.INVALID_FILE_FORMAT,
            file_path,
            details,
            cause
        )
        self.is_recoverable = True


# ============================================================================
# External Service Exceptions
# ============================================================================

class ExternalServiceException(DCFException):
    """Base class for external service exceptions"""
    
    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.LLM_SERVICE_ERROR,
        service_name: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if service_name:
            details["service_name"] = service_name
        super().__init__(message, code, details, cause, is_recoverable=True)


class LLMServiceException(ExternalServiceException):
    """Raised when LLM service fails"""
    
    def __init__(
        self,
        message: str = "LLM service failed",
        service_name: str = "MiniMax",
        model: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if model:
            details["model"] = model
        super().__init__(
            message,
            ErrorCode.LLM_SERVICE_ERROR,
            service_name,
            details,
            cause
        )


class EmailServiceException(ExternalServiceException):
    """Raised when email service fails"""
    
    def __init__(
        self,
        message: str = "Email service failed",
        recipient: Optional[str] = None,
        subject: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if recipient:
            details["recipient"] = recipient
        if subject:
            details["subject"] = subject
        super().__init__(
            message,
            ErrorCode.EMAIL_SERVICE_ERROR,
            "EmailService",
            details,
            cause
        )


class SchedulerServiceException(ExternalServiceException):
    """Raised when scheduler service fails"""
    
    def __init__(
        self,
        message: str = "Scheduler service failed",
        job_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if job_id:
            details["job_id"] = job_id
        super().__init__(
            message,
            ErrorCode.SCHEDULER_ERROR,
            "SchedulerService",
            details,
            cause
        )


# ============================================================================
# Validation Exceptions
# ============================================================================

class ValidationException(DCFException):
    """Raised when input validation fails"""
    
    def __init__(
        self,
        message: str,
        field: Optional[str] = None,
        invalid_value: Optional[Any] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if field:
            details["field"] = field
        if invalid_value is not None:
            details["invalid_value"] = str(invalid_value)[:100]  # Truncate long values
        super().__init__(
            message,
            ErrorCode.VALIDATION_ERROR,
            details,
            cause,
            is_recoverable=True
        )


class ResourceNotFoundException(DCFException):
    """Raised when a requested resource is not found"""
    
    def __init__(
        self,
        message: str = "Resource not found",
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        cause: Optional[Exception] = None
    ):
        details = details or {}
        if resource_type:
            details["resource_type"] = resource_type
        if resource_id:
            details["resource_id"] = resource_id
        super().__init__(
            message,
            ErrorCode.RESOURCE_NOT_FOUND,
            details,
            cause,
            is_recoverable=False
        )


# ============================================================================
# Exception Mapping for HTTP Status Codes
# ============================================================================

EXCEPTION_TO_STATUS_CODE = {
    DatabaseConnectionError: 503,
    DatabaseTimeoutError: 504,
    DatabaseQueryError: 500,
    APIRateLimitException: 429,
    NetworkException: 502,
    AgentInitException: 500,
    WorkflowException: 500,
    ApprovalTimeoutException: 408,
    DCFCalculationException: 422,
    InsufficientDataException: 422,
    ParameterValidationException: 400,
    PDFParsingException: 422,
    InvalidFileFormatException: 400,
    ValidationException: 400,
    ResourceNotFoundException: 404,
    LLMServiceException: 502,
    EmailServiceException: 500,
    SchedulerServiceException: 500,
}
