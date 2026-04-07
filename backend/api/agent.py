"""
Agent API endpoints for DCF Valuation Agent (LangGraph Version)
"""
from typing import Optional, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# Import unified error handling
from backend.models.error_models import ErrorResponse, validation_error, not_found_error
from backend.exceptions import DCFException

# Import LangGraph-based agent
try:
    from backend.agent.langgraph_agent import langgraph_agent
except ImportError:
    from agent.langgraph_agent import langgraph_agent

router = APIRouter(prefix="/agent", tags=["Agent"])


class AddTickerRequest(BaseModel):
    """Request to add a ticker"""
    ticker: str
    locale: str = "US"


class RemoveTickerRequest(BaseModel):
    """Request to remove a ticker"""
    ticker: str


class StartAnalysisRequest(BaseModel):
    """Request to start analysis"""
    tickers: Optional[List[str]] = None
    force_update: bool = False


class SendReportRequest(BaseModel):
    """Request to send report email"""
    to_email: Optional[str] = None


class StartSchedulerRequest(BaseModel):
    """Request to start scheduler"""
    interval_hours: int = 24


@router.post("/start")
async def start_analysis(request: StartAnalysisRequest):
    """
    Start DCF Agent analysis (LangGraph Workflow)
    
    If tickers is not provided, analyzes all tickers in the database.
    """
    try:
        result = langgraph_agent.run_analysis(
            tickers=request.tickers,
            force_update=request.force_update,
            send_email=True
        )
        
        if not result.get('success', False):
            raise HTTPException(status_code=400, detail=result.get('error', 'Analysis failed'))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def get_status():
    """
    Get current agent status (LangGraph Workflow)
    """
    try:
        return langgraph_agent.get_status()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/stop")
async def stop_analysis():
    """
    Stop currently running analysis (LangGraph Workflow)
    """
    try:
        # Note: This only stops scheduled analysis, not currently running tasks
        langgraph_agent.stop_scheduled()
        return {"success": True, "message": "Analysis stopped"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/portfolio")
async def get_portfolio():
    """
    Get latest portfolio recommendations (LangGraph Workflow)
    """
    try:
        recommendations = langgraph_agent.get_recommendations(limit=50)
        
        return {
            "success": True,
            "recommendations": recommendations,
            "count": len(recommendations)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-report")
async def send_report(request: SendReportRequest):
    """
    Manually send portfolio report via email (LangGraph Workflow)
    """
    try:
        result = langgraph_agent.send_report_email(to_email=request.to_email)
        
        if not result.get('success', False):
            raise HTTPException(status_code=400, detail=result.get('error', 'Failed to send report'))
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tickers/add")
async def add_ticker(request: AddTickerRequest):
    """
    Add a ticker to the monitoring list (LangGraph Workflow)
    """
    try:
        success = langgraph_agent.add_ticker(request.ticker, request.locale)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to add ticker")
        
        return {
            "success": True,
            "message": f"Ticker {request.ticker.upper()} added successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tickers/remove")
async def remove_ticker(request: RemoveTickerRequest):
    """
    Remove a ticker from the monitoring list (LangGraph Workflow)
    """
    try:
        success = langgraph_agent.remove_ticker(request.ticker)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to remove ticker")
        
        return {
            "success": True,
            "message": f"Ticker {request.ticker.upper()} removed successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tickers")
async def get_tickers():
    """
    Get all tickers being monitored (LangGraph Workflow)
    """
    try:
        tickers = langgraph_agent.get_tickers()
        return {
            "success": True,
            "count": len(tickers),
            "tickers": tickers
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/start")
async def start_scheduler(request: StartSchedulerRequest):
    """
    Start scheduled analysis (LangGraph Workflow)
    """
    try:
        success = langgraph_agent.start_scheduled(interval_hours=request.interval_hours)
        
        if not success:
            raise HTTPException(status_code=400, detail="Failed to start scheduler")
        
        return {
            "success": True,
            "message": f"Scheduler started: analysis every {request.interval_hours} hours"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/scheduler/stop")
async def stop_scheduler():
    """
    Stop scheduled analysis (LangGraph Workflow)
    """
    try:
        success = langgraph_agent.stop_scheduled()
        
        return {
            "success": True,
            "message": "Scheduler stopped" if success else "Scheduler was not running"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
