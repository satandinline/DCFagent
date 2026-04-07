"""
Base Classes for DCF Valuation Agent Tools
Defines the Tool interface and common utilities
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from enum import Enum
import logging
import json
from datetime import datetime

logger = logging.getLogger(__name__)


class ToolCategory(Enum):
    """Categories of tools available in the system"""
    FILE_PARSER = "file_parser"        # 文件解析
    DATA_FETCHER = "data_fetcher"      # 数据获取
    ANALYST = "analyst"                # 分析工具
    COMMUNICATOR = "communicator"      # 通信工具
    DATABASE = "database"              # 数据库工具
    UTILITY = "utility"               # 通用工具


class FileType(Enum):
    """Supported file types"""
    PDF = "pdf"
    EXCEL = "excel"      # .xlsx, .xls
    WORD = "word"        # .docx, .doc
    CSV = "csv"
    JSON = "json"
    XML = "xml"
    TEXT = "text"        # .txt
    HTML = "html"
    UNKNOWN = "unknown"


@dataclass
class ToolParameter:
    """Definition of a tool parameter"""
    name: str
    type: str  # string, integer, float, boolean, array, object
    description: str
    required: bool = True
    default: Any = None
    options: List[Any] = None  # For enum-like parameters


@dataclass
class ToolResult:
    """Result from executing a tool"""
    success: bool
    data: Any = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    tool_name: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'data': self.data,
            'error': self.error,
            'metadata': self.metadata,
            'execution_time': self.execution_time,
            'tool_name': self.tool_name
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, default=str)


@dataclass
class BaseTool(ABC):
    """
    Abstract base class for all tools in the DCF Valuation Agent
    
    Each tool should:
    1. Have a unique name
    2. Define its parameters
    3. Implement the execute method
    4. Provide metadata for tool selection
    """
    
    # Class-level attributes (override in subclasses)
    name: str = ""
    description: str = ""
    category: ToolCategory = ToolCategory.UTILITY
    parameters: List[ToolParameter] = field(default_factory=list)
    version: str = "1.0.0"
    
    def __init__(self):
        self.logger = logging.getLogger(f"{__name__}.{self.name}")
        self._execution_count = 0
        self._total_execution_time = 0.0
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Unique name of the tool"""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Human-readable description of what the tool does"""
        pass
    
    @property
    @abstractmethod
    def category(self) -> ToolCategory:
        """Category this tool belongs to"""
        pass
    
    @property
    def parameters(self) -> List[ToolParameter]:
        """List of parameters this tool accepts"""
        return self._parameters if hasattr(self, '_parameters') else []
    
    @parameters.setter
    def parameters(self, value: List[ToolParameter]):
        self._parameters = value
    
    @abstractmethod
    def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters
        
        Args:
            **kwargs: Parameters as defined by the tool's parameter schema
            
        Returns:
            ToolResult with success status and output data
        """
        pass
    
    def validate_parameters(self, **kwargs) -> tuple[bool, Optional[str]]:
        """
        Validate input parameters against the tool's schema
        
        Returns:
            (is_valid, error_message)
        """
        for param in self.parameters:
            if param.required and param.name not in kwargs:
                return False, f"Missing required parameter: {param.name}"
            
            if param.name in kwargs:
                value = kwargs[param.name]
                expected_type = param.type
                
                # Type checking
                if expected_type == "string" and not isinstance(value, str):
                    return False, f"Parameter {param.name} must be a string"
                elif expected_type == "integer" and not isinstance(value, int):
                    return False, f"Parameter {param.name} must be an integer"
                elif expected_type == "float" and not isinstance(value, (int, float)):
                    return False, f"Parameter {param.name} must be a number"
                elif expected_type == "boolean" and not isinstance(value, bool):
                    return False, f"Parameter {param.name} must be a boolean"
                elif expected_type == "array" and not isinstance(value, list):
                    return False, f"Parameter {param.name} must be an array"
                elif expected_type == "object" and not isinstance(value, dict):
                    return False, f"Parameter {param.name} must be an object"
                
                # Check options
                if param.options and value not in param.options:
                    return False, f"Parameter {param.name} must be one of: {param.options}"
        
        return True, None
    
    def _track_execution(self, execution_time: float):
        """Track tool execution metrics"""
        self._execution_count += 1
        self._total_execution_time += execution_time
    
    def get_stats(self) -> Dict[str, Any]:
        """Get execution statistics for this tool"""
        avg_time = (self._total_execution_time / self._execution_count 
                   if self._execution_count > 0 else 0)
        return {
            'name': self.name,
            'execution_count': self._execution_count,
            'total_execution_time': self._total_execution_time,
            'average_execution_time': avg_time
        }
    
    def get_schema(self) -> Dict[str, Any]:
        """Get the tool's schema for LLM consumption"""
        return {
            'name': self.name,
            'description': self.description,
            'category': self.category.value,
            'parameters': [
                {
                    'name': p.name,
                    'type': p.type,
                    'description': p.description,
                    'required': p.required,
                    'default': p.default,
                    'options': p.options
                }
                for p in self.parameters
            ],
            'version': self.version
        }


@dataclass
class ToolSelectionCriteria:
    """Criteria for selecting the right tool"""
    task: str = ""                    # Natural language description of task
    file_type: Optional[FileType] = None
    category: Optional[ToolCategory] = None
    preferred_tools: List[str] = None  # Tool names user prefers
    excluded_tools: List[str] = None   # Tool names to avoid
    requires_capabilities: List[str] = None  # Required capabilities


class ToolCapability:
    """Capabilities that tools can advertise"""
    # File parsing
    PARSE_PDF = "parse_pdf"
    PARSE_EXCEL = "parse_excel"
    PARSE_WORD = "parse_word"
    PARSE_CSV = "parse_csv"
    PARSE_JSON = "parse_json"
    PARSE_XML = "parse_xml"
    PARSE_HTML = "parse_html"
    PARSE_TEXT = "parse_text"
    
    # Data fetching
    FETCH_STOCK_DATA = "fetch_stock_data"
    FETCH_FINANCIAL_STATEMENTS = "fetch_financial_statements"
    FETCH_PRICE_HISTORY = "fetch_price_history"
    WEB_SEARCH = "web_search"
    
    # Analysis
    DCF_VALUATION = "dcf_valuation"
    INDUSTRY_CLASSIFICATION = "industry_classification"
    TREND_ANALYSIS = "trend_analysis"
    SENSITIVITY_ANALYSIS = "sensitivity_analysis"
    
    # Communication
    SEND_EMAIL = "send_email"
    SEND_NOTIFICATION = "send_notification"
    
    # Database
    QUERY_DATABASE = "query_database"
    SAVE_RESULT = "save_result"
    
    # Utility
    FORMAT_DATA = "format_data"
    VALIDATE_DATA = "validate_data"
