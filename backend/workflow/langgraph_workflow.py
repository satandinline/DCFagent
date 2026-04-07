"""
LangGraph Workflow Core for DCF Valuation Agent
Builds and compiles the StateGraph workflow
"""
from __future__ import annotations
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from backend.workflow.state import WorkflowState
from backend.workflow.nodes import NODES, init_workflow, fetch_ticker_data, classify_industry
from backend.workflow.nodes import run_valuations, aggregate_results, save_to_database
from backend.workflow.nodes import send_report, finish_workflow, handle_failure
from backend.workflow.router import (
    ROUTERS, route_after_init, route_after_fetch, route_after_classify,
    route_after_value, route_after_aggregate, route_after_save,
    route_after_email, route_after_handle_failure
)

logger = logging.getLogger(__name__)


class DCFWorkflow:
    """
    LangGraph-based workflow for DCF Valuation Agent
    
    This workflow is NOT a fixed sequential process. It supports:
    - Conditional branching (based on data characteristics)
    - Loops (processing multiple tickers)
    - State persistence (across workflow steps)
    - Flexible routing (different paths for different scenarios)
    
    Workflow Graph:
    
        [Start]
           │
           ▼
        [init] ──────────────────────┐
           │                          │
           ▼                          │ (no tickers)
        [fetch_data] ───────────────────┤
           │                          │
           ▼                          │
        [classify] ─────────────────────┤
           │                          │
           ▼                          │
        [value] ────────────────────────┤
           │                          │
           ├──────► [fetch_data] ◄────┤ (more tickers)
           │                          │
           ▼                          │
       [aggregate] ────────────────────┤
           │                          │
           ▼                          │
         [save] ───────────────────────┤
           │                          │
           ▼                          │
      [send_email] ────────────────────┤ (optional)
           │                          │
           ▼                          │
        [finish] ──────────────────────┘
           │
           ▼
         [End]
    
    Each ticker's processing path may vary based on:
    - Whether data fetch succeeds
    - Industry classification results
    - Valuation method availability
    """
    
    def __init__(self):
        self.graph: Optional[StateGraph] = None
        self.compiled_graph = None
        self._build_graph()
    
    def _build_graph(self):
        """Build the StateGraph with nodes and edges"""
        
        # Create the workflow graph
        workflow = StateGraph(WorkflowState)
        
        # =========================================================================
        # ADD NODES
        # =========================================================================
        
        # Core processing nodes
        workflow.add_node("init", init_workflow)
        workflow.add_node("fetch_data", fetch_ticker_data)
        workflow.add_node("classify", classify_industry)
        workflow.add_node("value", run_valuations)
        workflow.add_node("aggregate", aggregate_results)
        workflow.add_node("save", save_to_database)
        workflow.add_node("send_email", send_report)
        workflow.add_node("finish", finish_workflow)
        
        # Error handling node
        workflow.add_node("handle_failure", handle_failure)
        
        # =========================================================================
        # ADD EDGES - Define the flow
        # =========================================================================
        
        # Start from init
        workflow.add_conditional_edges(
            "init",
            route_after_init,
            {
                "fetch_data": "fetch_data",
                "finish": "finish"
            }
        )
        
        # After fetching data
        workflow.add_conditional_edges(
            "fetch_data",
            route_after_fetch,
            {
                "classify": "classify",
                "handle_failure": "handle_failure"
            }
        )
        
        # After classification
        workflow.add_conditional_edges(
            "classify",
            route_after_classify,
            {
                "value": "value",
                "handle_failure": "handle_failure"
            }
        )
        
        # After valuation - can loop back for more tickers or proceed to aggregate
        workflow.add_conditional_edges(
            "value",
            route_after_value,
            {
                "fetch_data": "fetch_data",  # More tickers to process
                "aggregate": "aggregate"     # All done
            }
        )
        
        # After handling failure - check if more tickers
        workflow.add_conditional_edges(
            "handle_failure",
            route_after_handle_failure,
            {
                "fetch_data": "fetch_data",  # More tickers to process
                "aggregate": "aggregate"     # All done
            }
        )
        
        # After aggregation - always go to save
        workflow.add_edge("aggregate", "save")
        
        # After save - check if email should be sent
        workflow.add_conditional_edges(
            "save",
            route_after_save,
            {
                "send_email": "send_email",
                "finish": "finish"
            }
        )
        
        # After email - always finish
        workflow.add_edge("send_email", "finish")
        
        # Finish is terminal
        workflow.add_edge("finish", END)
        
        # =========================================================================
        # SET ENTRY POINT
        # =========================================================================
        
        workflow.set_entry_point("init")
        
        # Store the graph
        self.graph = workflow
    
    def compile(self, checkpointer: bool = True):
        """
        Compile the graph into an executable graph
        
        Args:
            checkpointer: If True, use MemorySaver for state persistence
            
        Returns:
            Compiled graph ready to run
        """
        if checkpointer:
            checkpointer = MemorySaver()
            self.compiled_graph = self.graph.compile(checkpointer=checkpointer)
        else:
            self.compiled_graph = self.graph.compile()
        
        logger.info("LangGraph workflow compiled successfully")
        return self.compiled_graph
    
    def run(self, tickers: List[str] = None, config: Dict[str, Any] = None) -> WorkflowState:
        """
        Run the workflow
        
        Args:
            tickers: List of ticker symbols to process
            config: Optional configuration overrides
            
        Returns:
            Final WorkflowState after execution
        """
        # Ensure graph is compiled
        if not self.compiled_graph:
            self.compile()
        
        # Initialize state
        initial_state = WorkflowState(
            tickers=tickers or [],
            config=config or {},
            workflow_id=f"dcf_workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        logger.info(f"Starting workflow execution with {len(tickers or [])} tickers")
        
        # Run the graph
        try:
            final_state = None
            for state_update in self.compiled_graph.stream(initial_state):
                # Each state_update is a dict with node names and their output
                logger.debug(f"State update: {list(state_update.keys())}")
                final_state = state_update
            
            if final_state:
                # Get the last state
                last_key = list(final_state.keys())[-1]
                return final_state[last_key]
            
            return initial_state
            
        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
            initial_state.add_error(str(e))
            return initial_state
    
    def run_async(self, tickers: List[str] = None, config: Dict[str, Any] = None):
        """
        Async version of run - for use with FastAPI
        Returns the generator directly for streaming
        """
        if not self.compiled_graph:
            self.compile()
        
        initial_state = WorkflowState(
            tickers=tickers or [],
            config=config or {},
            workflow_id=f"dcf_workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )
        
        return self.compiled_graph.stream(initial_state)
    
    def get_graph(self) -> StateGraph:
        """Get the underlying graph object (for visualization)"""
        return self.graph


# =============================================================================
# WORKFLOW EXECUTION HELPERS
# =============================================================================

def create_workflow() -> DCFWorkflow:
    """
    Factory function to create a new workflow instance
    """
    return DCFWorkflow()


def run_quick_analysis(tickers: List[str] = None) -> Dict[str, Any]:
    """
    Quick helper to run a full analysis workflow
    
    Args:
        tickers: List of tickers to analyze
        
    Returns:
        Dict with analysis results
    """
    workflow = create_workflow()
    workflow.compile()
    
    final_state = workflow.run(tickers=tickers)
    
    return {
        'success': final_state.current_step == 'completed',
        'workflow_id': final_state.workflow_id,
        'tickers_analyzed': len(final_state.completed_tickers),
        'recommendations': final_state.recommendations,
        'summary': final_state.portfolio_summary,
        'email_sent': final_state.email_sent,
        'errors': final_state.errors
    }


# =============================================================================
# GRAPH VISUALIZATION (for debugging)
# =============================================================================

def get_workflow_diagram() -> str:
    """
    Generate a text representation of the workflow graph
    Useful for debugging and documentation
    """
    return """
    DCF Valuation Agent - LangGraph Workflow
    
    ┌─────────────────────────────────────────────────────────────────┐
    │                        WORKFLOW GRAPH                            │
    └─────────────────────────────────────────────────────────────────┘
    
    Entry Point: init
    
    Edges:
    ─────
    init ──────────────► fetch_data ───────────► classify
         │ (if no tickers)     │ (on success)        │ (on success)
         ▼                    ▼                    ▼
      finish              value ◄─────────────► handle_failure
                           │                         │
                           │ (loop for more tickers) │ (if more tickers)
                           │                         │
                           ▼                         │
                      aggregate ─────────────────────┘
                           │
                           ▼
                         save
                           │
                           ▼
                    send_email (optional)
                           │
                           ▼
                        finish ─────────────────────► END
    
    Routing Logic:
    ──────────────
    • After init: Check if tickers exist
    • After fetch_data: Proceed if data fetched, handle_failure otherwise
    • After classify: Proceed if classified, handle_failure otherwise
    • After value: Loop back for more tickers OR proceed to aggregate
    • After handle_failure: Continue with next ticker or aggregate
    • After aggregate: Always save, then optionally send email
    • After save: Send email if enabled, otherwise finish
    • After email: Always finish
    
    State Persistence:
    ─────────────────
    Uses MemorySaver checkpointer for:
    • Recovery from interruptions
    • State tracking across steps
    • Debugging and inspection
    """
