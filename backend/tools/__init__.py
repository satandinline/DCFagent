"""
DCF Valuation Agent - Tools Module

This module contains all tools that can be used by the LangGraph workflow.
Tools are organized by category:
- file_parsers: PDF, Excel, Word, CSV, JSON, XML parsers
- data_fetchers: Yahoo Finance, Web Search, News, Ratios
- analysts: DCF Valuation, Industry Classification, Trend Analysis
- communicators: Email, Notification
- database_tools: Add Ticker, Get History, Save Results

Usage:
    from backend.tools import tool_registry, execute_tool
    
    # Get all available tools
    all_tools = tool_registry.get_all()
    
    # Execute a specific tool
    result = execute_tool('pdf_parser', file_path='/path/to/file.pdf')
    
    # Select tools based on task
    tools = tool_registry.select_tools(criteria={'task': 'parse excel file'})
"""

# Import and register all tools
from backend.tools.base import (
    BaseTool,
    ToolCategory,
    ToolResult,
    ToolParameter,
    FileType,
    ToolSelectionCriteria,
    ToolCapability
)

from backend.tools.registry import (
    tool_registry,
    register_tool,
    get_tool,
    execute_tool
)

# Import tools to trigger registration
from backend.tools.file_parsers import register_file_parser_tools
from backend.tools.data_fetchers import register_data_fetcher_tools
from backend.tools.analysts import register_analyst_tools
from backend.tools.communicators import register_communicator_tools
from backend.tools.database_tools import register_database_tools
from backend.tools.llm_reasoner import register_llm_reasoner_tools


def initialize_tools():
    """
    Initialize and register all tools
    
    Call this function during application startup to ensure
    all tools are registered and available.
    """
    register_file_parser_tools()
    register_data_fetcher_tools()
    register_analyst_tools()
    register_communicator_tools()
    register_database_tools()
    register_llm_reasoner_tools()
    
    print(f"Initialized {len(tool_registry)} tools:")
    for category, count in tool_registry.get_categories().items():
        print(f"  - {category.value}: {count} tools")


def get_tool_by_capability(capability: str):
    """Get all tools that have a specific capability"""
    return tool_registry.get_by_capability(capability)


def get_tool_by_file_type(file_type: FileType):
    """Get all tools that can handle a specific file type"""
    return tool_registry.get_by_file_type(file_type)


def get_tools_by_category(category: ToolCategory):
    """Get all tools in a specific category"""
    return tool_registry.get_by_category(category)


__all__ = [
    # Base classes
    'BaseTool',
    'ToolCategory',
    'ToolResult',
    'ToolParameter',
    'FileType',
    'ToolSelectionCriteria',
    'ToolCapability',
    
    # Registry
    'tool_registry',
    'register_tool',
    'get_tool',
    'execute_tool',
    
    # Initialization
    'initialize_tools',
    'get_tool_by_capability',
    'get_tool_by_file_type',
    'get_tools_by_category',
]
