"""
Tool Registry for DCF Valuation Agent
Central registry for all available tools with dynamic tool selection
"""
from __future__ import annotations
from typing import Dict, List, Optional, Any, Callable
import logging
from collections import defaultdict

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from backend.tools.base import (
    BaseTool, 
    ToolCategory, 
    ToolResult, 
    FileType,
    ToolSelectionCriteria,
    ToolCapability
)

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central registry for all tools in the DCF Valuation Agent
    
    Features:
    - Tool registration and discovery
    - Category-based tool grouping
    - Capability-based tool selection
    - File-type based tool selection
    - Natural language tool recommendation for LLM
    """
    
    def __init__(self):
        self._tools: Dict[str, BaseTool] = {}
        self._categories: Dict[ToolCategory, List[str]] = defaultdict(list)
        self._capabilities: Dict[str, List[str]] = defaultdict(list)
        self._file_types: Dict[FileType, List[str]] = defaultdict(list)
        self._tool_descriptions: Dict[str, str] = {}
        
        # Register all built-in tools
        self._register_builtin_tools()
    
    def _register_builtin_tools(self):
        """Register all built-in tools"""
        # This will be called after all tool modules are imported
        pass
    
    def register(self, tool: BaseTool) -> bool:
        """
        Register a tool in the registry
        
        Args:
            tool: Tool instance to register
            
        Returns:
            True if registered successfully
        """
        try:
            if tool.name in self._tools:
                logger.warning(f"Tool {tool.name} already registered, replacing")
            
            self._tools[tool.name] = tool
            self._categories[tool.category].append(tool.name)
            self._tool_descriptions[tool.name] = tool.description
            
            # Register capabilities
            if hasattr(tool, 'capabilities'):
                for cap in tool.capabilities:
                    self._capabilities[cap].append(tool.name)
            
            logger.info(f"Registered tool: {tool.name} ({tool.category.value})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to register tool {tool.name}: {e}")
            return False
    
    def unregister(self, tool_name: str) -> bool:
        """Unregister a tool"""
        if tool_name not in self._tools:
            return False
        
        tool = self._tools[tool_name]
        self._categories[tool.category].remove(tool_name)
        
        # Remove from capabilities
        if hasattr(tool, 'capabilities'):
            for cap in tool.capabilities:
                if tool_name in self._capabilities[cap]:
                    self._capabilities[cap].remove(tool_name)
        
        del self._tools[tool_name]
        del self._tool_descriptions[tool_name]
        
        logger.info(f"Unregistered tool: {tool_name}")
        return True
    
    def get(self, tool_name: str) -> Optional[BaseTool]:
        """Get a tool by name"""
        return self._tools.get(tool_name)
    
    def get_all(self) -> List[BaseTool]:
        """Get all registered tools"""
        return list(self._tools.values())
    
    def get_by_category(self, category: ToolCategory) -> List[BaseTool]:
        """Get all tools in a category"""
        tool_names = self._categories.get(category, [])
        return [self._tools[name] for name in tool_names if name in self._tools]
    
    def get_by_capability(self, capability: str) -> List[BaseTool]:
        """Get all tools with a specific capability"""
        tool_names = self._capabilities.get(capability, [])
        return [self._tools[name] for name in tool_names if name in self._tools]
    
    def get_by_file_type(self, file_type: FileType) -> List[BaseTool]:
        """Get all tools that can handle a specific file type"""
        tool_names = self._file_types.get(file_type, [])
        return [self._tools[name] for name in tool_names if name in self._tools]
    
    def execute(self, tool_name: str, **kwargs) -> ToolResult:
        """
        Execute a tool by name
        
        Args:
            tool_name: Name of the tool to execute
            **kwargs: Parameters for the tool
            
        Returns:
            ToolResult from the tool execution
        """
        tool = self.get(tool_name)
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool not found: {tool_name}",
                tool_name=tool_name
            )
        
        try:
            # Validate parameters
            is_valid, error = tool.validate_parameters(**kwargs)
            if not is_valid:
                return ToolResult(
                    success=False,
                    error=error,
                    tool_name=tool_name
                )
            
            # Execute
            return tool.execute(**kwargs)
            
        except Exception as e:
            logger.error(f"Tool execution error for {tool_name}: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=tool_name
            )
    
    def select_tools(self, criteria: ToolSelectionCriteria) -> List[BaseTool]:
        """
        Select appropriate tools based on criteria
        
        This is the core intelligence for tool selection,
        used by the LLM to decide which tools to use.
        
        Args:
            criteria: Selection criteria including task, file type, category, etc.
            
        Returns:
            List of recommended tools in order of preference
        """
        candidates: Dict[str, float] = {}  # tool_name -> score
        
        for tool_name, tool in self._tools.items():
            score = 0.0
            
            # Excluded tools
            if criteria.excluded_tools and tool_name in criteria.excluded_tools:
                continue
            
            # Preferred tools get higher score
            if criteria.preferred_tools and tool_name in criteria.preferred_tools:
                score += 10.0
            
            # Category match
            if criteria.category and tool.category == criteria.category:
                score += 5.0
            
            # File type match
            if criteria.file_type and tool_name in self._file_types.get(criteria.file_type, []):
                score += 8.0
            
            # Capability match
            if criteria.requires_capabilities:
                tool_caps = getattr(tool, 'capabilities', [])
                matched_caps = set(criteria.requires_capabilities) & set(tool_caps)
                score += len(matched_caps) * 3.0
            
            # Task description keyword matching
            if criteria.task:
                task_lower = criteria.task.lower()
                desc_lower = tool.description.lower()
                
                # Direct description match
                if any(word in desc_lower for word in task_lower.split()):
                    score += 2.0
                
                # Tool name match
                if any(word in tool_name.lower() for word in task_lower.split()):
                    score += 3.0
            
            if score > 0:
                candidates[tool_name] = score
        
        # Sort by score and return tools
        sorted_tools = sorted(candidates.items(), key=lambda x: x[1], reverse=True)
        return [self._tools[name] for name, _ in sorted_tools]
    
    def recommend_tool(self, task: str, file_type: FileType = None) -> Optional[BaseTool]:
        """
        Recommend the best tool for a task
        
        Args:
            task: Natural language description of the task
            file_type: Optional file type to process
            
        Returns:
            The most appropriate tool or None
        """
        criteria = ToolSelectionCriteria(
            task=task,
            file_type=file_type
        )
        
        tools = self.select_tools(criteria)
        return tools[0] if tools else None
    
    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get schemas of all tools for LLM consumption"""
        return [tool.get_schema() for tool in self._tools.values()]
    
    def get_categories(self) -> Dict[ToolCategory, int]:
        """Get tool counts by category"""
        return {
            category: len(tools) 
            for category, tools in self._categories.items()
        }
    
    def get_capabilities_summary(self) -> Dict[str, int]:
        """Get tool counts by capability"""
        return {
            cap: len(tools) 
            for cap, tools in self._capabilities.items()
        }
    
    def __len__(self) -> int:
        return len(self._tools)
    
    def __contains__(self, tool_name: str) -> bool:
        return tool_name in self._tools
    
    def __iter__(self):
        return iter(self._tools.values())


# Global registry instance
tool_registry = ToolRegistry()


def register_tool(tool: BaseTool) -> bool:
    """Convenience function to register a tool"""
    return tool_registry.register(tool)


def get_tool(tool_name: str) -> Optional[BaseTool]:
    """Convenience function to get a tool"""
    return tool_registry.get(tool_name)


def execute_tool(tool_name: str, **kwargs) -> ToolResult:
    """Convenience function to execute a tool"""
    return tool_registry.execute(tool_name, **kwargs)
