"""
Agents Module for DCF Valuation System

Multi-agent architecture for separation of concerns:
- DataAgent: Data acquisition and preprocessing
- AnalysisAgent: Valuation and analysis
- NotificationAgent: Notifications and reporting
- CoordinatorAgent: Orchestration and workflow management
"""
from __future__ import annotations

from backend.agents.base_agent import BaseAgent, AgentResult, AgentCapability
from backend.agents.data_agent import DataAgent
from backend.agents.analysis_agent import AnalysisAgent
from backend.agents.notification_agent import NotificationAgent
from backend.agents.coordinator import CoordinatorAgent

__all__ = [
    'BaseAgent',
    'AgentResult',
    'AgentCapability',
    'DataAgent',
    'AnalysisAgent',
    'NotificationAgent',
    'CoordinatorAgent'
]
