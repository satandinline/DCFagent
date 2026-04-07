"""
Agent Management API for DCF Valuation System
Provides endpoints for multi-agent coordination, approvals, and memory
"""
from __future__ import annotations

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime
import logging

# Import unified error handling
from backend.models.error_models import ErrorResponse, validation_error, not_found_error
from backend.exceptions import DCFException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/agent/v2", tags=["Agent V2 - Multi-Agent"])


# =============================================================================
# Request/Response Models
# =============================================================================

class ValuationRequest(BaseModel):
    """Request to run valuation with multi-agent system"""
    ticker: str
    force_update: bool = False


class BatchValuationRequest(BaseModel):
    """Request for batch valuation"""
    tickers: List[str]
    force_update: bool = False


class ApprovalResponseRequest(BaseModel):
    """Request to approve or reject"""
    workflow_id: str
    approved: bool
    approver: str = "web_user"
    comments: Optional[str] = None


class MemorySearchRequest(BaseModel):
    """Request to search memory"""
    query: str
    limit: int = 10
    ticker: Optional[str] = None


# =============================================================================
# Agent Endpoints - Multi-Agent System
# =============================================================================

@router.post("/valuation")
async def run_valuation(request: ValuationRequest):
    """
    Run valuation using the multi-agent Coordinator Agent
    
    This endpoint uses the new multi-agent system with:
    - DataAgent for data fetching
    - AnalysisAgent for valuation
    - ApprovalNode for high-risk decisions
    - VectorMemoryStore for persistence
    """
    try:
        from backend.agents.coordinator import CoordinatorAgent
        
        coordinator = CoordinatorAgent()
        result = coordinator.run_valuation_workflow({
            'ticker': request.ticker.upper(),
            'force_update': request.force_update
        })
        
        if result.success:
            return {
                "success": True,
                "workflow_id": result.data.get('workflow_id'),
                "status": result.data.get('status'),
                "requires_approval": result.data.get('requires_approval'),
                "approval_request_id": result.data.get('approval_request_id'),
                "preview": result.data.get('preview'),
                "analysis": result.data.get('analysis') if result.data.get('status') == 'completed' else None,
                "metadata": result.metadata
            }
        else:
            return {
                "success": False,
                "error": result.error,
                "metadata": result.metadata
            }
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/valuation/batch")
async def run_batch_valuation(request: BatchValuationRequest):
    """
    Run batch valuation for multiple tickers
    """
    try:
        from backend.agents.coordinator import CoordinatorAgent
        
        coordinator = CoordinatorAgent()
        result = coordinator.run_batch_valuation({
            'tickers': [t.upper() for t in request.tickers],
            'force_update': request.force_update
        })
        
        return result.data if result.success else {"success": False, "error": result.error}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/valuation/status/{workflow_id}")
async def get_workflow_status(workflow_id: str):
    """
    Get the status of a valuation workflow
    """
    try:
        from backend.agents.coordinator import CoordinatorAgent
        
        coordinator = CoordinatorAgent()
        status = coordinator.get_workflow_status(workflow_id)
        
        if not status:
            raise HTTPException(status_code=404, detail="Workflow not found")
        
        return {
            "success": True,
            "workflow_id": workflow_id,
            "status": status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/valuation/pending")
async def get_pending_workflows():
    """
    Get all workflows awaiting approval
    """
    try:
        from backend.agents.coordinator import CoordinatorAgent
        
        coordinator = CoordinatorAgent()
        pending = coordinator.list_pending_workflows()
        
        return {
            "success": True,
            "count": len(pending),
            "pending": pending
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Approval Endpoints - Human-in-the-Loop
# =============================================================================

@router.post("/approval/respond")
async def respond_to_approval(request: ApprovalResponseRequest):
    """
    Approve or reject a pending approval request
    """
    try:
        from backend.agents.coordinator import CoordinatorAgent
        
        coordinator = CoordinatorAgent()
        result = coordinator._handle_approval_callback({
            'workflow_id': request.workflow_id,
            'approved': request.approved,
            'approver': request.approver,
            'comments': request.comments
        })
        
        return result.data if result.success else {"success": False, "error": result.error}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/approval/pending")
async def get_pending_approvals():
    """
    Get all pending approval requests
    """
    try:
        from backend.workflow.approval_nodes import get_approval_manager
        
        manager = get_approval_manager()
        pending = manager.get_pending_requests()
        
        return {
            "success": True,
            "count": len(pending),
            "approvals": [p.to_dict() for p in pending]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/approval/{approval_id}")
async def get_approval(approval_id: str):
    """
    Get a specific approval request
    """
    try:
        from backend.workflow.approval_nodes import get_approval_manager
        
        manager = get_approval_manager()
        approval = manager.get_request(approval_id)
        
        if not approval:
            raise HTTPException(status_code=404, detail="Approval request not found")
        
        return {
            "success": True,
            "approval": approval.to_dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Memory Endpoints - Vector Memory Store
# =============================================================================

@router.post("/memory/search")
async def search_memory(request: MemorySearchRequest):
    """
    Search the vector memory store for similar analyses
    """
    try:
        from backend.memory.vector_store import get_memory_store
        
        memory = get_memory_store()
        
        # Build filter if ticker provided
        filter_metadata = None
        if request.ticker:
            filter_metadata = {'ticker': request.ticker.upper()}
        
        results = memory.search(
            query=request.query,
            n_results=request.limit,
            filter_metadata=filter_metadata
        )
        
        return {
            "success": True,
            "count": len(results),
            "results": [
                {
                    'memory_id': r.id,
                    'content': r.content,
                    'metadata': r.metadata,
                    'created_at': r.created_at
                }
                for r in results
            ]
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/company/{ticker}")
async def get_company_memory(ticker: str, limit: int = 20):
    """
    Get all memory entries for a specific company
    """
    try:
        from backend.memory.vector_store import get_memory_store
        
        memory = get_memory_store()
        history = memory.get_company_history(ticker.upper(), limit=limit)
        
        return {
            "success": True,
            "ticker": ticker.upper(),
            "count": len(history),
            "history": history
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/insights/{ticker}")
async def get_company_insights(ticker: str):
    """
    Get aggregated insights for a company based on historical analyses
    """
    try:
        from backend.memory.vector_store import get_memory_store
        
        memory = get_memory_store()
        insights = memory.get_insights(ticker.upper())
        
        return {
            "success": True,
            "ticker": ticker.upper(),
            "insights": insights
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/memory/stats")
async def get_memory_stats():
    """
    Get memory store statistics
    """
    try:
        from backend.memory.vector_store import get_memory_store
        
        memory = get_memory_store()
        stats = memory.get_stats()
        
        return {
            "success": True,
            "stats": stats
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/memory/clear")
async def clear_memory(older_than_days: Optional[int] = None):
    """
    Clear memory entries, optionally only those older than specified days
    """
    try:
        from backend.memory.vector_store import get_memory_store
        from datetime import timedelta, datetime
        
        memory = get_memory_store()
        
        if older_than_days:
            older_than = datetime.now() - timedelta(days=older_than_days)
            count = memory.clear(older_than=older_than)
        else:
            count = memory.clear()
        
        return {
            "success": True,
            "cleared_count": count
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# LLM Reasoning Endpoints
# =============================================================================

class LLMReasoningRequest(BaseModel):
    """Request for LLM reasoning"""
    task_type: str  # classify_industry, recommend_valuation, decide_action, explain_result
    context: Dict[str, Any]


@router.post("/reasoning")
async def llm_reasoning(request: LLMReasoningRequest):
    """
    Use LLM for intelligent reasoning
    """
    try:
        from backend.tools.llm_reasoner import LLMReasonerTool
        
        reasoner = LLMReasonerTool()
        result = reasoner.execute(
            task_type=request.task_type,
            context=request.context
        )
        
        return {
            "success": result.success,
            "data": result.data,
            "error": result.error
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# =============================================================================
# Agent Info Endpoint
# =============================================================================

@router.get("/info")
async def get_agent_info():
    """
    Get information about available agents and their capabilities
    """
    try:
        from backend.agents import register_all_agents
        from backend.agents.base_agent import get_agent_registry
        
        registry = register_all_agents()
        agents = registry.get_all()
        
        return {
            "success": True,
            "agents": [
                {
                    "name": agent.name,
                    "role": agent.role,
                    "description": agent.description,
                    "capabilities": [c.value for c in agent._capabilities],
                    "tools": agent._tools,
                    "metrics": agent.get_metrics()
                }
                for agent in agents
            ],
            "total_agents": len(agents)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/react/test")
async def test_react_loop(ticker: str = "AAPL"):
    """
    Test the ReAct reasoning loop with a simple example
    """
    try:
        from backend.workflow.react_nodes import ReActNodes, ReActWorkflowIntegration
        
        state = ReActWorkflowIntegration.create_react_enabled_state({
            'ticker': ticker
        })
        
        result = ReActNodes.run_reflection_loop(
            state,
            {'ticker': ticker},
            max_iterations=5
        )
        
        return {
            "success": True,
            "result": ReActWorkflowIntegration.extract_react_insights(result)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
