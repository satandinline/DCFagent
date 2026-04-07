"""
LangGraph Workflow Routers for DCF Valuation Agent
Defines conditional routing logic for the workflow
"""
from __future__ import annotations
from typing import Literal, Dict, Any
import logging

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from backend.workflow.state import WorkflowState

logger = logging.getLogger(__name__)


# =============================================================================
# ROUTER FUNCTIONS - Return the next node to execute based on state
# =============================================================================


def route_after_init(state: WorkflowState) -> str:
    """
    Route after initialization
    Routes to fetch_data if there are tickers to process, otherwise to finish
    """
    if not state.tickers:
        logger.info("No tickers to process, ending workflow")
        return "finish"
    
    if state.errors and len(state.errors) == len(state.tickers):
        # All tickers failed during init
        logger.warning("All tickers failed during init")
        return "finish"
    
    return "fetch_data"


def route_after_fetch(state: WorkflowState) -> str:
    """
    Route after fetching data
    Routes to classify if successful, handle_failure otherwise
    """
    ticker = state.get_current_ticker()
    ticker_data = state.ticker_data.get(ticker)
    
    if not ticker_data:
        return "handle_failure"
    
    if ticker_data.status == "failed":
        logger.warning(f"Data fetch failed for {ticker}")
        return "handle_failure"
    
    if ticker_data.status == "data_fetched":
        return "classify"
    
    # Default fallback
    return "handle_failure"


def route_after_classify(state: WorkflowState) -> str:
    """
    Route after classification
    Routes to value if successful, handle_failure otherwise
    """
    ticker = state.get_current_ticker()
    ticker_data = state.ticker_data.get(ticker)
    
    if not ticker_data:
        return "handle_failure"
    
    if ticker_data.status == "failed":
        logger.warning(f"Classification failed for {ticker}")
        return "handle_failure"
    
    if ticker_data.status == "classified":
        return "value"
    
    return "handle_failure"


def route_after_value(state: WorkflowState) -> str:
    """
    Route after valuation
    Routes to either next ticker processing or aggregation based on whether there are more tickers
    """
    ticker = state.get_current_ticker()
    ticker_data = state.ticker_data.get(ticker)
    
    if not ticker_data:
        return "handle_failure"
    
    if ticker_data.status == "failed":
        logger.warning(f"Valuation failed for {ticker}")
        return "handle_failure"
    
    if ticker_data.status == "valued":
        # Mark as completed
        if ticker not in state.completed_tickers:
            state.completed_tickers.append(ticker)
        
        # Check if there are more tickers to process
        if state.advance_to_next_ticker():
            # More tickers to process, loop back to fetch
            logger.info(f"Processed {ticker}, moving to next ticker")
            return "fetch_data"
        else:
            # No more tickers, proceed to aggregation
            logger.info("All tickers processed, proceeding to aggregation")
            return "aggregate"
    
    return "handle_failure"


def route_after_aggregate(state: WorkflowState) -> str:
    """
    Route after aggregation
    Routes to email, save, or finish based on configuration
    """
    # Always save to database first
    next_step = "save"
    
    # If email is enabled, add it to the chain
    if state.should_send_email:
        next_step = "send_email"
    
    return next_step


def route_after_save(state: WorkflowState) -> str:
    """
    Route after saving to database
    Routes to email if enabled and not sent, otherwise to finish
    """
    if state.should_send_email and not state.email_sent:
        return "send_email"
    
    return "finish"


def route_after_email(state: WorkflowState) -> str:
    """
    Route after sending email
    Always goes to finish
    """
    return "finish"


def route_after_handle_failure(state: WorkflowState) -> str:
    """
    Route after handling a failure
    Checks if there are more tickers to process
    """
    if state.advance_to_next_ticker():
        return "fetch_data"
    else:
        return "aggregate"


# =============================================================================
# CONDITIONAL EDGE FUNCTIONS - Used with LangGraph's conditional_edges
# =============================================================================

def should_continue_workflow(state: WorkflowState) -> Literal["continue", "end"]:
    """
    Determines if the workflow should continue processing
    Returns "continue" to keep going, "end" to finish
    """
    if state.should_continue and state.current_step != "completed":
        return "continue"
    return "end"


def should_send_email(state: WorkflowState) -> Literal["send_email", "skip_email"]:
    """
    Determines if email should be sent
    Based on configuration and whether email was already sent
    """
    if state.should_send_email and not state.email_sent:
        return "send_email"
    return "skip_email"


# =============================================================================
# ROUTER REGISTRY - Maps states to routing functions
# =============================================================================

ROUTERS: Dict[str, Any] = {
    'after_init': route_after_init,
    'after_fetch': route_after_fetch,
    'after_classify': route_after_classify,
    'after_value': route_after_value,
    'after_aggregate': route_after_aggregate,
    'after_save': route_after_save,
    'after_email': route_after_email,
    'after_handle_failure': route_after_handle_failure,
}
