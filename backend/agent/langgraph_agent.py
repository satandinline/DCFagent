"""
DCF Agent with LangGraph Workflow
Integrates LangGraph workflow with the existing agent infrastructure
"""
from __future__ import annotations
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Any
import threading
import asyncio

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from backend.workflow import create_workflow, run_quick_analysis, DCFWorkflow
from backend.workflow.state import WorkflowState
from backend.services.db_service import db_service
from backend.services.scheduler_service import scheduler_service
from backend.services.email_service import email_service

logger = logging.getLogger(__name__)


class AgentStatus:
    """Agent status enum"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class WorkflowExecution:
    """Tracks a workflow execution"""
    execution_id: str
    workflow_id: str
    status: str
    started_at: str
    completed_at: Optional[str] = None
    tickers: List[str] = None
    result: Optional[Dict[str, Any]] = None


class LangGraphAgent:
    """
    DCF Valuation Agent powered by LangGraph
    
    This agent uses LangGraph's StateGraph for flexible,
    conditional workflow execution rather than fixed sequence.
    
    Key Features:
    - Dynamic routing based on data characteristics
    - Loop support for processing multiple tickers
    - State persistence across workflow steps
    - Human-in-the-loop ready architecture
    - Streaming execution for long-running tasks
    
    Workflow Steps:
    1. Init -> Get tickers from DB or use provided
    2. For each ticker:
       a. Fetch data from Yahoo Finance
       b. Classify industry type
       c. Run appropriate valuation methods
       d. Handle failures gracefully
    3. Aggregate results
    4. Save to database
    5. Send email report (optional)
    6. Finish
    """
    
    def __init__(self):
        self._workflow: Optional[DCFWorkflow] = None
        self._current_execution: Optional[WorkflowExecution] = None
        self._execution_lock = threading.Lock()
        self._is_scheduled = False
        self._last_execution_time: Optional[datetime] = None
    
    @property
    def workflow(self) -> DCFWorkflow:
        """Lazy-load the workflow"""
        if self._workflow is None:
            self._workflow = create_workflow()
            self._workflow.compile()
        return self._workflow
    
    def run_analysis(
        self,
        tickers: List[str] = None,
        force_update: bool = False,
        send_email: bool = True
    ) -> Dict[str, Any]:
        """
        Run the full analysis workflow
        
        Args:
            tickers: List of tickers to analyze. If None, fetches from DB.
            force_update: Force analysis even if recently run
            send_email: Whether to send email report
            
        Returns:
            Dict with execution results
        """
        with self._execution_lock:
            if self._current_execution and self._current_execution.status == "running":
                return {
                    'success': False,
                    'error': 'Agent is already running a workflow'
                }
            
            # Create new execution tracking
            execution_id = f"exec_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self._current_execution = WorkflowExecution(
                execution_id=execution_id,
                workflow_id="",
                status="running",
                started_at=datetime.now().isoformat(),
                tickers=tickers
            )
        
        logger.info(f"Starting LangGraph workflow execution: {execution_id}")
        
        try:
            # Prepare config
            config = {
                'force_update': force_update,
                'send_email': send_email
            }
            
            # Run the workflow
            final_state = self.workflow.run(
                tickers=tickers,
                config=config
            )
            
            # Update execution status
            self._current_execution.status = "completed"
            self._current_execution.completed_at = datetime.now().isoformat()
            self._current_execution.workflow_id = final_state.workflow_id
            self._current_execution.result = {
                'success': final_state.current_step == 'completed',
                'workflow_id': final_state.workflow_id,
                'tickers_analyzed': len(final_state.completed_tickers),
                'tickers_failed': len(final_state.failed_tickers),
                'recommendations': final_state.recommendations,
                'summary': final_state.portfolio_summary,
                'email_sent': final_state.email_sent,
                'errors': final_state.errors,
                'warnings': final_state.warnings
            }
            
            self._last_execution_time = datetime.now()
            
            logger.info(f"Workflow {execution_id} completed successfully")
            
            return self._current_execution.result
            
        except Exception as e:
            logger.error(f"Workflow execution error: {e}")
            
            self._current_execution.status = "failed"
            self._current_execution.completed_at = datetime.now().isoformat()
            self._current_execution.result = {
                'success': False,
                'error': str(e)
            }
            
            return self._current_execution.result
    
    def run_scheduled_analysis(self):
        """
        Entry point for scheduled analysis
        Called by the scheduler service
        """
        logger.info("Starting scheduled LangGraph analysis")
        
        result = self.run_analysis(
            tickers=None,  # Will fetch from DB
            force_update=True,
            send_email=True
        )
        
        return result
    
    def get_status(self) -> Dict[str, Any]:
        """
        Get current agent status
        
        Returns:
            Dict with status information
        """
        execution_info = None
        if self._current_execution:
            execution_info = {
                'execution_id': self._current_execution.execution_id,
                'status': self._current_execution.status,
                'started_at': self._current_execution.started_at,
                'completed_at': self._current_execution.completed_at,
                'tickers': self._current_execution.tickers
            }
        
        return {
            'agent_status': self._current_execution.status if self._current_execution else "idle",
            'is_scheduled': self._is_scheduled,
            'last_execution': self._last_execution_time.isoformat() if self._last_execution_time else None,
            'current_execution': execution_info,
            'workflow_diagram': get_workflow_diagram_text()
        }
    
    def add_ticker(self, ticker: str, locale: str = "US") -> bool:
        """
        Add a ticker to the database for monitoring
        
        Args:
            ticker: Stock ticker symbol
            locale: Locale (US, CN, etc.)
            
        Returns:
            bool: Success status
        """
        try:
            return db_service.insert_stock(ticker.upper(), locale)
        except Exception as e:
            logger.error(f"Error adding ticker {ticker}: {e}")
            return False
    
    def remove_ticker(self, ticker: str) -> bool:
        """
        Remove a ticker from monitoring
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            bool: Success status
        """
        try:
            conn = db_service.get_connection()
            with conn.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM stocks WHERE ticker = %s",
                    (ticker.upper(),)
                )
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"Error removing ticker {ticker}: {e}")
            return False
    
    def get_tickers(self) -> List[Dict[str, Any]]:
        """
        Get all tickers being monitored
        
        Returns:
            List of ticker info dicts
        """
        try:
            conn = db_service.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM stocks ORDER BY created_at DESC")
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting tickers: {e}")
            return []
    
    def get_recommendations(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get latest recommendations from database
        
        Args:
            limit: Maximum number to return
            
        Returns:
            List of recommendation dicts
        """
        try:
            conn = db_service.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM portfolio_recommendations 
                    ORDER BY created_at DESC 
                    LIMIT %s
                """, (limit,))
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"Error getting recommendations: {e}")
            return []
    
    def start_scheduled(self, interval_hours: int = 24) -> bool:
        """
        Start scheduled analysis
        
        Args:
            interval_hours: Hours between runs
            
        Returns:
            bool: Success status
        """
        if self._is_scheduled:
            logger.info("Scheduler already running")
            return True
        
        try:
            scheduler_service.init_scheduler()
            scheduler_service.start()
            
            success = scheduler_service.add_interval_job(
                job_id='langgraph_agent_scheduled',
                func=self.run_scheduled_analysis,
                hours=interval_hours,
                minutes=0,
                replace_existing=True
            )
            
            if success:
                self._is_scheduled = True
                logger.info(f"Scheduled analysis started: every {interval_hours} hours")
            
            return success
            
        except Exception as e:
            logger.error(f"Error starting scheduler: {e}")
            return False
    
    def stop_scheduled(self) -> bool:
        """
        Stop scheduled analysis
        
        Returns:
            bool: Success status
        """
        if not self._is_scheduled:
            return True
        
        success = scheduler_service.remove_job('langgraph_agent_scheduled')
        
        if success:
            self._is_scheduled = False
            logger.info("Scheduled analysis stopped")
        
        return success
    
    def send_report_email(self, to_email: str = None) -> Dict[str, Any]:
        """
        Manually send portfolio report
        
        Args:
            to_email: Override recipient email
            
        Returns:
            Dict with send result
        """
        try:
            # Get latest recommendations
            recommendations = self.get_recommendations(limit=50)
            
            if not recommendations:
                return {
                    'success': False,
                    'error': 'No recommendations to send'
                }
            
            # Prepare portfolio data
            portfolio_data = {
                'report_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'stocks_analyzed': len(recommendations),
                'recommendations': recommendations,
                'summary': {
                    'total_stocks': len(recommendations),
                    'action_distribution': self._calculate_action_distribution(recommendations)
                },
                'details': recommendations
            }
            
            # Send email
            result = email_service.send_portfolio_report(
                portfolio_data,
                to_email=to_email
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending report email: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _calculate_action_distribution(self, recommendations: List[Dict]) -> Dict[str, int]:
        """Calculate action distribution from recommendations"""
        distribution = {'BUY': 0, 'HOLD': 0, 'SELL': 0}
        for rec in recommendations:
            action = rec.get('action', 'HOLD')
            if action in distribution:
                distribution[action] += 1
        return distribution


# Singleton instance
langgraph_agent = LangGraphAgent()


# Helper function for workflow diagram
def get_workflow_diagram_text() -> str:
    """Get a text representation of the workflow"""
    return """
    LangGraph DCF Agent Workflow
    
    [START] --> [init] --> [fetch_data] --> [classify] --> [value]
                                                          |
        <----------- (loop for more tickers) <-----------+
                                                          |
                                                     [aggregate]
                                                          |
                                                     [save]
                                                          |
                                              [send_email] (optional)
                                                          |
                                                     [finish]
                                                          |
                                                     [END]
    
    Conditional Routing:
    - init: Go to fetch_data if tickers exist, else finish
    - fetch_data: Proceed if success, handle_failure otherwise
    - classify: Proceed if success, handle_failure otherwise
    - value: Loop for more tickers OR aggregate
    - handle_failure: Continue with next ticker or aggregate
    - aggregate: Always save
    - save: Send email if enabled, else finish
    """
