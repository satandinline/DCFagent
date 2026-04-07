"""
DCF Valuation Agent - Backend Package

Main components:
- tools: Tool registry and implementations
- workflow: LangGraph workflow definitions
- agents: Multi-agent system (DataAgent, AnalysisAgent, etc.)
- memory: Vector-based memory storage
"""

# Core exports
from backend.tools import initialize_tools, tool_registry
from backend.workflow import create_workflow, run_quick_analysis
from backend.agents import (
    BaseAgent,
    AgentResult,
    DataAgent,
    AnalysisAgent,
    NotificationAgent,
    CoordinatorAgent
)

# Exception handling exports
from backend.exceptions import (
    DCFException,
    ErrorCode,
    DatabaseException,
    DatabaseConnectionError,
    DatabaseQueryError,
    DataFetchException,
    AgentException,
    ValuationException,
    FileProcessingException,
    ExternalServiceException,
    ValidationException,
    ResourceNotFoundException,
)
from backend.exception_handlers import (
    ExceptionHandlerMiddleware,
    ErrorResponse,
    safe_endpoint,
    log_exception,
    ExceptionContext,
    retry_on_exception,
)
from backend.models.error_models import (
    ErrorResponse as APIErrorResponse,
    SuccessResponse,
    validation_error,
    not_found_error,
    database_error,
    external_service_error,
)

__all__ = [
    # Tools
    'initialize_tools',
    'tool_registry',
    # Workflow
    'create_workflow',
    'run_quick_analysis',
    # Agents
    'BaseAgent',
    'AgentResult',
    'DataAgent',
    'AnalysisAgent',
    'NotificationAgent',
    'CoordinatorAgent',
    # Exceptions
    'DCFException',
    'ErrorCode',
    'DatabaseException',
    'DatabaseConnectionError',
    'DatabaseQueryError',
    'DataFetchException',
    'AgentException',
    'ValuationException',
    'FileProcessingException',
    'ExternalServiceException',
    'ValidationException',
    'ResourceNotFoundException',
    # Exception Handlers
    'ExceptionHandlerMiddleware',
    'ErrorResponse',
    'safe_endpoint',
    'log_exception',
    'ExceptionContext',
    'retry_on_exception',
    # Error Models
    'APIErrorResponse',
    'SuccessResponse',
    'validation_error',
    'not_found_error',
    'database_error',
    'external_service_error',
]
