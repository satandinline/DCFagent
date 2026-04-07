"""
DCF Valuation Agent - LangGraph Workflow Module

This module implements a flexible, stateful workflow for automated
DCF valuation analysis using LangGraph.

Main Components:
- state.py: WorkflowState and TickerData definitions
- nodes.py: Node functions that perform work
- router.py: Conditional routing logic
- langgraph_workflow.py: Graph construction and execution

Usage:
    from backend.workflow import create_workflow, run_quick_analysis
    
    # Quick run
    result = run_quick_analysis(['AAPL', 'MSFT'])
    
    # Or with more control
    workflow = create_workflow()
    workflow.compile()
    final_state = workflow.run(tickers=['AAPL'])
"""
from backend.workflow.state import (
    WorkflowState,
    TickerData,
    IndustryType,
    ValuationMethod,
    Action
)
from backend.workflow.langgraph_workflow import (
    DCFWorkflow,
    create_workflow,
    run_quick_analysis,
    get_workflow_diagram
)
from backend.workflow.nodes import NODES
from backend.workflow.router import ROUTERS
from backend.workflow.react_nodes import (
    ReActNodes,
    ReActState,
    ReActWorkflowIntegration
)
from backend.workflow.approval_nodes import (
    ApprovalNode,
    ApprovalManager,
    ApprovalStatus,
    RiskLevel,
    get_approval_manager
)

__all__ = [
    'WorkflowState',
    'TickerData', 
    'IndustryType',
    'ValuationMethod',
    'Action',
    'DCFWorkflow',
    'create_workflow',
    'run_quick_analysis',
    'get_workflow_diagram',
    'NODES',
    'ROUTERS',
    # ReAct nodes
    'ReActNodes',
    'ReActState',
    'ReActWorkflowIntegration',
    # Approval nodes
    'ApprovalNode',
    'ApprovalManager',
    'ApprovalStatus',
    'RiskLevel',
    'get_approval_manager'
]
