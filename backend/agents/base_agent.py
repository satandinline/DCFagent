"""
Base Agent Class for DCF Valuation System

Provides common functionality for all agent types
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import time
import json

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from backend.tools.registry import tool_registry

logger = logging.getLogger(__name__)


class AgentCapability(Enum):
    """Agent capabilities"""
    DATA_FETCH = "data_fetch"
    DATA_PARSE = "data_parse"
    FINANCIAL_ANALYSIS = "financial_analysis"
    VALUATION = "valuation"
    INDUSTRY_ANALYSIS = "industry_analysis"
    NOTIFICATION = "notification"
    REPORTING = "reporting"
    MEMORY = "memory"
    LLM_REASONING = "llm_reasoning"


@dataclass
class AgentResult:
    """
    Result returned by an agent after task execution
    """
    success: bool
    data: Any = None
    error: str = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    execution_time: float = 0.0
    agent_name: str = ""
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'success': self.success,
            'data': self.data,
            'error': self.error,
            'metadata': self.metadata,
            'execution_time': self.execution_time,
            'agent_name': self.agent_name,
            'timestamp': self.timestamp
        }


class BaseAgent(ABC):
    """
    Abstract base class for all agents in the system
    
    Agents are specialized components that perform specific tasks:
    - DataAgent: Fetches and parses data
    - AnalysisAgent: Performs valuations
    - NotificationAgent: Sends notifications
    
    Each agent has:
    - name: Unique identifier
    - role: Human-readable description of role
    - capabilities: Set of capabilities this agent possesses
    - tools: Tools available to this agent
    """
    
    name: str = "base_agent"
    role: str = "Base Agent"
    description: str = "Abstract base agent"
    
    def __init__(self):
        self._capabilities: Set[AgentCapability] = set()
        self._tools: List[str] = []
        self._metrics = {
            'tasks_executed': 0,
            'tasks_succeeded': 0,
            'tasks_failed': 0,
            'total_execution_time': 0.0
        }
        self._initialize_tools()
        self._initialize_capabilities()
        
        logger.info(f"Initialized {self.name}")
    
    @abstractmethod
    def _initialize_capabilities(self):
        """Initialize agent capabilities (to be implemented by subclasses)"""
        pass
    
    @abstractmethod
    def _initialize_tools(self):
        """Initialize available tools (to be implemented by subclasses)"""
        pass
    
    @abstractmethod
    def _execute_task(self, task: Dict[str, Any]) -> AgentResult:
        """
        Execute the actual task (to be implemented by subclasses)
        
        Args:
            task: Task specification dictionary
            
        Returns:
            AgentResult with execution outcome
        """
        pass
    
    def run(self, task: Dict[str, Any]) -> AgentResult:
        """
        Run a task with this agent
        
        This is the main entry point for executing tasks. It handles:
        - Task validation
        - Execution timing
        - Error handling
        - Metrics tracking
        
        Args:
            task: Task specification dictionary
            
        Returns:
            AgentResult with execution outcome
        """
        start_time = time.time()
        
        # Validate task
        if not self._validate_task(task):
            return AgentResult(
                success=False,
                error="Invalid task specification",
                agent_name=self.name
            )
        
        # Log execution
        logger.info(f"{self.name} executing task: {task.get('type', 'unknown')}")
        
        try:
            # Execute task
            result = self._execute_task(task)
            result.agent_name = self.name
            result.execution_time = time.time() - start_time
            
            # Update metrics
            self._metrics['tasks_executed'] += 1
            if result.success:
                self._metrics['tasks_succeeded'] += 1
            else:
                self._metrics['tasks_failed'] += 1
            self._metrics['total_execution_time'] += result.execution_time
            
            return result
            
        except Exception as e:
            logger.exception(f"{self.name} task execution failed: {e}")
            self._metrics['tasks_failed'] += 1
            
            return AgentResult(
                success=False,
                error=str(e),
                agent_name=self.name,
                execution_time=time.time() - start_time
            )
    
    def _validate_task(self, task: Dict[str, Any]) -> bool:
        """Validate task specification"""
        if not isinstance(task, dict):
            return False
        
        # Check for required fields
        required_fields = ['type']
        for field in required_fields:
            if field not in task:
                logger.warning(f"Task missing required field: {field}")
                return False
        
        return True
    
    def can_handle(self, task: Dict[str, Any]) -> bool:
        """Check if this agent can handle the given task"""
        task_type = task.get('type', '')
        
        # Map task types to capabilities
        task_capability_map = {
            'fetch_data': AgentCapability.DATA_FETCH,
            'parse_file': AgentCapability.DATA_PARSE,
            'dcf_valuation': AgentCapability.VALUATION,
            'industry_classification': AgentCapability.INDUSTRY_ANALYSIS,
            'send_notification': AgentCapability.NOTIFICATION,
            'generate_report': AgentCapability.REPORTING,
            'reason': AgentCapability.LLM_REASONING,
        }
        
        required_capability = task_capability_map.get(task_type)
        
        if required_capability:
            return required_capability in self._capabilities
        
        # Fallback: check if task type is in supported types
        return task_type in self._get_supported_task_types()
    
    def _get_supported_task_types(self) -> List[str]:
        """Get list of task types this agent supports"""
        return []
    
    def has_capability(self, capability: AgentCapability) -> bool:
        """Check if agent has a specific capability"""
        return capability in self._capabilities
    
    def add_tool(self, tool_name: str):
        """Add a tool to this agent's available tools"""
        if tool_name not in self._tools:
            self._tools.append(tool_name)
    
    def remove_tool(self, tool_name: str):
        """Remove a tool from this agent's available tools"""
        if tool_name in self._tools:
            self._tools.remove(tool_name)
    
    def execute_tool(self, tool_name: str, **kwargs):
        """Execute a tool using the tool registry"""
        if tool_name not in self._tools:
            logger.warning(f"{self.name} does not have tool: {tool_name}")
            return None
        
        return tool_registry.execute(tool_name, **kwargs)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get agent execution metrics"""
        metrics = self._metrics.copy()
        if metrics['tasks_executed'] > 0:
            metrics['success_rate'] = metrics['tasks_succeeded'] / metrics['tasks_executed']
            metrics['avg_execution_time'] = metrics['total_execution_time'] / metrics['tasks_executed']
        else:
            metrics['success_rate'] = 0.0
            metrics['avg_execution_time'] = 0.0
        return metrics
    
    def reset_metrics(self):
        """Reset agent metrics"""
        self._metrics = {
            'tasks_executed': 0,
            'tasks_succeeded': 0,
            'tasks_failed': 0,
            'total_execution_time': 0.0
        }
    
    def get_info(self) -> Dict[str, Any]:
        """Get agent information"""
        return {
            'name': self.name,
            'role': self.role,
            'description': self.description,
            'capabilities': [c.value for c in self._capabilities],
            'tools': self._tools,
            'metrics': self.get_metrics()
        }


class AgentRegistry:
    """
    Registry for managing multiple agents
    """
    
    _instance = None
    _agents: Dict[str, BaseAgent] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def register(self, agent: BaseAgent):
        """Register an agent"""
        self._agents[agent.name] = agent
        logger.info(f"Registered agent: {agent.name}")
    
    def get(self, name: str) -> Optional[BaseAgent]:
        """Get an agent by name"""
        return self._agents.get(name)
    
    def get_all(self) -> List[BaseAgent]:
        """Get all registered agents"""
        return list(self._agents.values())
    
    def find_agent_for_task(self, task: Dict[str, Any]) -> Optional[BaseAgent]:
        """Find an agent that can handle the given task"""
        for agent in self._agents.values():
            if agent.can_handle(task):
                return agent
        return None
    
    def unregister(self, name: str) -> bool:
        """Unregister an agent"""
        if name in self._agents:
            del self._agents[name]
            return True
        return False


def get_agent_registry() -> AgentRegistry:
    """Get the global agent registry"""
    return AgentRegistry()
