"""
DCF Valuation Agent - Models Package
"""
from backend.models.schemas import (
    FinancialData,
    DCFParameters,
    FCFProjection,
    DCFResult,
    SensitivityMatrix,
    ExtractionResponse,
    NarrativeRequest,
    NarrativeResponse,
    CalculateRequest,
    AgentConfig,
    AgentStatusResponse,
    PortfolioRequest,
    EmailRequest,
)
from backend.models.error_models import (
    ErrorResponse,
    ErrorDetail,
    SuccessResponse,
    PaginatedResponse,
    APIError,
    validation_error,
    not_found_error,
    database_error,
    external_service_error,
)

__all__ = [
    # Schemas
    "FinancialData",
    "DCFParameters",
    "FCFProjection",
    "DCFResult",
    "SensitivityMatrix",
    "ExtractionResponse",
    "NarrativeRequest",
    "NarrativeResponse",
    "CalculateRequest",
    "AgentConfig",
    "AgentStatusResponse",
    "PortfolioRequest",
    "EmailRequest",
    # Error Models
    "ErrorResponse",
    "ErrorDetail",
    "SuccessResponse",
    "PaginatedResponse",
    "APIError",
    "validation_error",
    "not_found_error",
    "database_error",
    "external_service_error",
]