"""
Scheduled Tasks API for DCF Valuation System
Provides endpoints for managing scheduled data fetch tasks
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging

# Import unified error handling
from backend.models.error_models import ErrorResponse, validation_error, not_found_error
from backend.exceptions import DCFException

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/scheduled", tags=["Scheduled Tasks"])


class SchedulerStatusResponse(BaseModel):
    """Response for scheduler status"""
    is_running: bool
    is_fetching: bool
    task_enabled: bool
    next_run: Optional[str]
    recent_summary: dict


class SchedulerConfigRequest(BaseModel):
    """Request to update scheduler config"""
    fetch_hours: Optional[list] = None
    fetch_minute: Optional[int] = None
    batch_size: Optional[int] = None
    analysis_enabled: Optional[bool] = None
    report_enabled: Optional[bool] = None
    notification_emails: Optional[list] = None
    enabled: Optional[bool] = None


@router.get("/status")
async def get_scheduler_status():
    """
    Get current status of the Data Fetch Scheduler
    
    Returns:
    - is_running: Whether the scheduler is running
    - is_fetching: Whether a fetch is currently in progress
    - task_enabled: Whether scheduled tasks are enabled
    - next_run: Next scheduled run time
    - recent_summary: Summary of recent fetch operations
    """
    try:
        from backend.services.data_fetch_scheduler import data_fetch_scheduler
        
        status = data_fetch_scheduler.get_status()
        return {
            "success": True,
            "data": status
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/run-now")
async def run_scheduled_fetch_now():
    """
    Manually trigger the scheduled data fetch to run immediately
    
    This will:
    1. Check all tickers for new data
    2. Fetch new data if available
    3. Run analysis
    4. Send reports
    """
    try:
        from backend.services.data_fetch_scheduler import data_fetch_scheduler
        
        result = data_fetch_scheduler.run_now()
        
        return {
            "success": True,
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/summary")
async def get_fetch_summary(days: int = 7):
    """
    Get summary of data fetch operations for the specified number of days
    
    Args:
        days: Number of days to look back (default: 7)
    """
    try:
        from backend.services.db_service import db_service
        
        summary = db_service.get_data_fetch_summary(days=days)
        
        return {
            "success": True,
            "data": summary
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config")
async def update_scheduler_config(config: SchedulerConfigRequest):
    """
    Update the Data Fetch Scheduler configuration
    
    Args:
        fetch_hours: List of hours to run (e.g., [0, 12] for 00:00 and 12:00)
        fetch_minute: Minute of the hour to run (default: 0)
        batch_size: Number of tickers to process per batch
        analysis_enabled: Whether to run analysis after fetching
        report_enabled: Whether to send reports after analysis
        notification_emails: List of email addresses for reports
        enabled: Whether the scheduler is enabled
    """
    try:
        from backend.services.data_fetch_scheduler import data_fetch_scheduler
        
        # Build config dict
        config_dict = {}
        if config.fetch_hours is not None:
            config_dict['fetch_hours'] = config.fetch_hours
        if config.fetch_minute is not None:
            config_dict['fetch_minute'] = config.fetch_minute
        if config.batch_size is not None:
            config_dict['batch_size'] = config.batch_size
        if config.analysis_enabled is not None:
            config_dict['analysis_enabled'] = config.analysis_enabled
        if config.report_enabled is not None:
            config_dict['report_enabled'] = config.report_enabled
        if config.notification_emails is not None:
            config_dict['notification_emails'] = config.notification_emails
        if config.enabled is not None:
            config_dict['enabled'] = config.enabled
        
        # Update config
        success = data_fetch_scheduler.update_config(config_dict)
        
        # If enabling/disabling, update job
        if 'enabled' in config_dict:
            if config_dict['enabled']:
                data_fetch_scheduler.setup_scheduled_jobs()
            else:
                data_fetch_scheduler.remove_scheduled_jobs()
        
        return {
            "success": success,
            "config": data_fetch_scheduler.config
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/config")
async def get_scheduler_config():
    """
    Get current scheduler configuration
    """
    try:
        from backend.services.data_fetch_scheduler import data_fetch_scheduler
        
        # Get persisted config from database
        from backend.services.db_service import db_service
        task_config = db_service.get_scheduled_task_config('scheduled_data_fetch')
        
        return {
            "success": True,
            "config": data_fetch_scheduler.config,
            "persisted": task_config
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/enable")
async def enable_scheduler():
    """
    Enable the scheduled data fetch scheduler
    """
    try:
        from backend.services.data_fetch_scheduler import data_fetch_scheduler
        
        success = data_fetch_scheduler.setup_scheduled_jobs()
        
        return {
            "success": success,
            "message": "Scheduler enabled" if success else "Failed to enable scheduler"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/disable")
async def disable_scheduler():
    """
    Disable the scheduled data fetch scheduler
    """
    try:
        from backend.services.data_fetch_scheduler import data_fetch_scheduler
        
        success = data_fetch_scheduler.remove_scheduled_jobs()
        
        return {
            "success": success,
            "message": "Scheduler disabled" if success else "Failed to disable scheduler"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tick")
async def get_monitored_tickers():
    """
    Get list of all tickers being monitored
    """
    try:
        from backend.services.db_service import db_service
        
        tickers = db_service.get_all_tickers()
        
        return {
            "success": True,
            "count": len(tickers),
            "tickers": tickers
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/check-ticker/{ticker}")
async def check_ticker_data(ticker: str):
    """
    Check if there is new data available for a specific ticker since last fetch
    
    Returns:
    - last_fetch: Last time data was fetched
    - has_new_data: Whether new data is available in database
    - data_changes: Detailed information about what data has changed
    """
    try:
        from backend.services.db_service import db_service
        from datetime import datetime
        
        ticker = ticker.upper()
        
        # Get last fetch date
        last_fetch = db_service.get_last_fetch_date(ticker)
        
        if last_fetch is None:
            return {
                "success": True,
                "ticker": ticker,
                "last_fetch": None,
                "has_new_data": True,  # First time, consider as new
                "message": "No previous fetch found, will fetch all data"
            }
        
        # Check for new data
        has_new_data = db_service.has_new_data_since(ticker, last_fetch)
        
        # Get detailed changes
        data_changes = db_service.get_data_changes_since(ticker, last_fetch)
        
        return {
            "success": True,
            "ticker": ticker,
            "last_fetch": str(last_fetch),
            "has_new_data": has_new_data,
            "data_changes": {
                "has_changes": data_changes.get('has_changes', False),
                "new_income_statements_count": len(data_changes.get('new_income_statements', [])),
                "new_balance_sheets_count": len(data_changes.get('new_balance_sheets', [])),
                "new_cash_flows_count": len(data_changes.get('new_cash_flows', [])),
                "new_prices_count": data_changes.get('new_prices_count', 0),
                "new_prices_latest": str(data_changes.get('new_prices_latest')) if data_changes.get('new_prices_latest') else None
            },
            "message": "New data available" if has_new_data else "No new data since last fetch"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fetch-logs")
async def get_fetch_logs(ticker: str = None, limit: int = 50):
    """
    Get fetch logs for a specific ticker or all tickers
    
    Args:
        ticker: Optional ticker to filter by
        limit: Maximum number of logs to return (default: 50)
    """
    try:
        from backend.services.db_service import DatabaseService
        import pymysql
        
        db = DatabaseService()
        conn = db.get_connection()
        
        if ticker:
            cursor.execute("""
                SELECT * FROM data_fetch_logs 
                WHERE ticker = %s
                ORDER BY fetch_date DESC 
                LIMIT %s
            """, (ticker.upper(), limit))
        else:
            cursor.execute("""
                SELECT * FROM data_fetch_logs 
                ORDER BY fetch_date DESC 
                LIMIT %s
            """, (limit,))
        
        logs = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Convert datetime objects to strings
        for log in logs:
            if log.get('fetch_date'):
                log['fetch_date'] = str(log['fetch_date'])
            if log.get('fetched_data_summary'):
                import json
                try:
                    log['fetched_data_summary'] = json.loads(log['fetched_data_summary'])
                except:
                    pass
        
        return {
            "success": True,
            "count": len(logs),
            "logs": logs
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fetch-history/{ticker}")
async def get_ticker_fetch_history(ticker: str, days: int = 30):
    """
    Get fetch history for a specific ticker
    
    Args:
        ticker: Stock ticker symbol
        days: Number of days to look back (default: 30)
    """
    try:
        from backend.services.db_service import DatabaseService
        
        db = DatabaseService()
        conn = db.get_connection()
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                id,
                ticker,
                fetch_type,
                fetch_date,
                data_found,
                new_data_available,
                records_fetched,
                analysis_triggered,
                report_sent,
                error_message,
                fetched_data_summary
            FROM data_fetch_logs 
            WHERE ticker = %s 
              AND fetch_date >= DATE_SUB(NOW(), INTERVAL %s DAY)
            ORDER BY fetch_date DESC
        """, (ticker.upper(), days))
        
        logs = cursor.fetchall()
        cursor.close()
        conn.close()
        
        # Format the results
        history = []
        for log in logs:
            history.append({
                'id': log['id'],
                'fetch_date': str(log['fetch_date']),
                'fetch_type': log['fetch_type'],
                'data_found': log['data_found'],
                'new_data_available': log['new_data_available'],
                'records_fetched': log['records_fetched'],
                'analysis_triggered': log['analysis_triggered'],
                'report_sent': log['report_sent'],
                'error': log['error_message'],
                'summary': log['fetched_data_summary']
            })
        
        return {
            "success": True,
            "ticker": ticker.upper(),
            "period_days": days,
            "fetch_count": len(history),
            "history": history
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trigger-fetch/{ticker}")
async def trigger_single_fetch(ticker: str):
    """
    Manually trigger data fetch for a single ticker
    
    This will:
    1. Check if new data is available
    2. Fetch the data if available
    3. Only run analysis if data actually changed
    4. Only send report if analysis finds new insights
    """
    try:
        from backend.services.data_fetch_scheduler import data_fetch_scheduler
        
        result = data_fetch_scheduler._process_ticker(ticker.upper())
        
        return {
            "success": True,
            "ticker": ticker.upper(),
            "result": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
