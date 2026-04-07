"""
DCF Valuation Agent Controller
Coordinates all agent components for automated valuation
"""
from __future__ import annotations
import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
import threading
import json

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from backend.models.schemas import FinancialData, DCFParameters
from backend.services.db_service import db_service
from backend.services.web_search_service import web_search_service
from backend.services.industry_classifier import industry_classifier, IndustryType
from backend.services.valuation_engine import valuation_engine, ValuationMethod
from backend.services.portfolio_service import portfolio_service, StockRecommendation
from backend.services.email_service import email_service
from backend.services.scheduler_service import scheduler_service

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Agent execution status"""
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class AgentTask:
    """Represents an agent task"""
    task_id: str
    status: AgentStatus = AgentStatus.IDLE
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    tickers_processed: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    result: Optional[Dict[str, Any]] = None


class DCFAgentController:
    """
    Main controller for the DCF Valuation Agent
    
    Coordinates:
    1. Data fetching from Yahoo Finance
    2. Industry classification
    3. Valuation execution
    4. Portfolio generation
    5. Email reporting
    """
    
    def __init__(self):
        self.current_task: Optional[AgentTask] = None
        self.task_lock = threading.Lock()
        self._status = AgentStatus.IDLE
        self._is_scheduled = False
        
        # Track last analysis for comparison
        self.last_analysis_time: Optional[datetime] = None
    
    @property
    def status(self) -> AgentStatus:
        """Get current agent status"""
        return self._status
    
    @status.setter
    def status(self, value: AgentStatus):
        """Set agent status"""
        self._status = value
        logger.info(f"Agent status changed to: {value.value}")
    
    def run_analysis(self, tickers: List[str] = None, force_update: bool = False) -> Dict[str, Any]:
        """
        Run complete analysis on specified tickers or all tickers in database
        
        Args:
            tickers: List of ticker symbols to analyze. If None, analyze all in DB.
            force_update: Force update even if recently analyzed
            
        Returns:
            Dict with analysis results
        """
        with self.task_lock:
            if self._status == AgentStatus.RUNNING:
                return {
                    'success': False,
                    'error': 'Agent is already running a task'
                }
            
            # Create new task
            task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            self.current_task = AgentTask(task_id=task_id)
            self.current_task.started_at = datetime.now()
            self.status = AgentStatus.RUNNING
        
        logger.info(f"Starting DCF Agent analysis: {task_id}")
        
        try:
            # Step 1: Get tickers to analyze
            if tickers is None:
                tickers = self._get_tickers_from_db()
            
            if not tickers:
                return {
                    'success': False,
                    'error': 'No tickers to analyze. Add stocks to the database first.'
                }
            
            logger.info(f"Analyzing {len(tickers)} tickers: {tickers}")
            
            # Step 2: Analyze each ticker
            recommendations: List[StockRecommendation] = []
            
            for ticker in tickers:
                try:
                    logger.info(f"Processing {ticker}...")
                    
                    # Fetch data from Yahoo Finance
                    company_data = self._fetch_company_data(ticker)
                    
                    if not company_data:
                        self.current_task.errors.append(f"Failed to fetch data for {ticker}")
                        continue
                    
                    # Classify industry
                    industry_type, valuation_rec = industry_classifier.classify(
                        sector=company_data.get('sector'),
                        industry=company_data.get('industry'),
                        company_name=company_data.get('company_name'),
                        is_profitable=company_data.get('net_income', 0) > 0,
                        has_dividends=company_data.get('dividend_yield', 0) > 0,
                        revenue_growth=company_data.get('revenue_growth', 0),
                        net_income=company_data.get('net_income', 0)
                    )
                    
                    logger.info(f"{ticker}: Industry type = {industry_type.value}")
                    
                    # Create financial data
                    financial_data = self._create_financial_data(ticker, company_data)
                    
                    # Select valuation methods based on industry
                    methods = self._get_valuation_methods(industry_type)
                    
                    # Run valuations
                    valuation_result = valuation_engine.evaluate(
                        financial_data,
                        methods=methods
                    )
                    
                    # Generate recommendation
                    recommendation = portfolio_service.generate_recommendation(
                        valuation_result,
                        industry=company_data.get('industry', ''),
                        sector=company_data.get('sector', '')
                    )
                    
                    # Save to database
                    portfolio_service.save_recommendation_to_db(recommendation)
                    self._save_valuation_result(ticker, company_data, valuation_result)
                    
                    recommendations.append(recommendation)
                    self.current_task.tickers_processed.append(ticker)
                    
                    logger.info(f"{ticker}: {recommendation.action} - {recommendation.upside:.1f}%")
                    
                    # Small delay to avoid rate limiting
                    asyncio.run(asyncio.sleep(1))
                    
                except Exception as e:
                    error_msg = f"Error processing {ticker}: {str(e)}"
                    logger.error(error_msg)
                    self.current_task.errors.append(error_msg)
            
            # Step 3: Generate portfolio report
            if recommendations:
                portfolio_report = portfolio_service.generate_portfolio_report(recommendations)
                
                # Update task result
                self.current_task.result = {
                    'success': True,
                    'tickers_analyzed': len(self.current_task.tickers_processed),
                    'recommendations': [r.ticker for r in recommendations],
                    'portfolio_report': portfolio_service.to_dict(portfolio_report),
                    'errors': self.current_task.errors
                }
            else:
                self.current_task.result = {
                    'success': False,
                    'error': 'No recommendations generated',
                    'errors': self.current_task.errors
                }
            
            self.status = AgentStatus.COMPLETED
            self.current_task.completed_at = datetime.now()
            self.last_analysis_time = datetime.now()
            
            return self.current_task.result
            
        except Exception as e:
            logger.error(f"Agent analysis failed: {e}")
            self.status = AgentStatus.FAILED
            self.current_task.errors.append(str(e))
            return {
                'success': False,
                'error': str(e)
            }
    
    def run_scheduled_analysis(self):
        """
        Entry point for scheduled analysis task
        This method is called by the scheduler
        """
        logger.info("Starting scheduled DCF Agent analysis")
        
        # Run analysis
        result = self.run_analysis()
        
        # If successful, send email report
        if result.get('success', False):
            try:
                portfolio_data = result.get('portfolio_report', {})
                email_service.send_portfolio_report(portfolio_data)
                logger.info("Portfolio report sent successfully")
            except Exception as e:
                logger.error(f"Failed to send portfolio report: {e}")
        
        return result
    
    def _get_tickers_from_db(self) -> List[str]:
        """Get all tickers from the database"""
        try:
            conn = db_service.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("SELECT ticker FROM stocks")
                rows = cursor.fetchall()
                return [row['ticker'] for row in rows]
        except Exception as e:
            logger.error(f"Error getting tickers from database: {e}")
            return []
    
    async def _fetch_company_data_async(self, ticker: str) -> Optional[Dict[str, Any]]:
        """
        Asynchronously fetch company data from Yahoo Finance
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Dict with company data or None
        """
        try:
            # Use Yahoo Finance
            result = await web_search_service._search_yahoo_finance(ticker)
            
            if result.get('success'):
                return result.get('data', {})
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            return None
    
    def _fetch_company_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Synchronous wrapper for data fetching"""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self._fetch_company_data_async(ticker))
                return result
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error in sync fetch for {ticker}: {e}")
            return None
    
    def _create_financial_data(self, ticker: str, company_data: Dict[str, Any]) -> FinancialData:
        """Create FinancialData object from company data"""
        
        # Calculate revenue growth
        revenue_growth = company_data.get('revenue_growth', 0.05)
        if isinstance(revenue_growth, bool):
            revenue_growth = 0.05
        
        # Calculate operating margin
        operating_margin = 0.15
        if company_data.get('operating_margin'):
            operating_margin = float(company_data.get('operating_margin', 0.15))
        
        return FinancialData(
            company_name=company_data.get('company_name', ticker),
            ticker=ticker,
            currency='USD',
            fiscal_year=datetime.now().year,
            revenue=float(company_data.get('revenue', 0)),
            revenue_growth=float(revenue_growth),
            operating_income=float(company_data.get('operating_income', 0)),
            operating_margin=float(operating_margin),
            net_income=float(company_data.get('net_income', 0)),
            depreciation_amortization=0,
            capital_expenditure=0,
            change_in_working_capital=0,
            total_debt=float(company_data.get('total_debt', 0)),
            cash_and_equivalents=float(company_data.get('total_cash', 0)),
            shares_outstanding=float(company_data.get('shares_outstanding', 1)),
            tax_rate=0.25,
            beta=float(company_data.get('beta', 1.0)),
            risk_free_rate=0.03,
            market_return=0.09,
            cost_of_debt=0.05,
            current_stock_price=float(company_data.get('current_price', 0)) if company_data.get('current_price') else None
        )
    
    def _get_valuation_methods(self, industry_type: IndustryType) -> List[ValuationMethod]:
        """Get appropriate valuation methods for industry type"""
        
        method_map = {
            IndustryType.MANUFACTURING_CONSUMER: [
                ValuationMethod.DCF,
                ValuationMethod.EV_EBITDA
            ],
            IndustryType.FINANCIAL_INSTITUTION: [
                ValuationMethod.DDM,
                ValuationMethod.PB
            ],
            IndustryType.HIGH_GROWTH_LOSS: [
                ValuationMethod.PS,
                ValuationMethod.DCF
            ],
            IndustryType.DIVERSIFIED_GROUP: [
                ValuationMethod.SOTP,
                ValuationMethod.DCF,
                ValuationMethod.EV_EBITDA
            ],
            IndustryType.TECHNOLOGY: [
                ValuationMethod.DCF,
                ValuationMethod.PS
            ],
            IndustryType.UNKNOWN: [
                ValuationMethod.DCF,
                ValuationMethod.EV_EBITDA
            ]
        }
        
        return method_map.get(industry_type, [ValuationMethod.DCF])
    
    def _save_valuation_result(
        self,
        ticker: str,
        company_data: Dict[str, Any],
        valuation_result
    ):
        """Save valuation result to database"""
        try:
            # Get primary valuation
            primary_value = valuation_result.average_fair_value
            current_price = None
            for result in valuation_result.results.values():
                if hasattr(result, 'current_price'):
                    current_price = result.current_price
                    break
            
            upside = 0
            if current_price and current_price > 0:
                upside = ((primary_value - current_price) / current_price) * 100
            
            valuation_data = {
                'company_name': company_data.get('company_name', ticker),
                'fiscal_year': datetime.now().year,
                'currency': 'USD',
                'per_share_value': primary_value,
                'enterprise_value': 0,
                'equity_value': 0,
                'wacc_used': 0.1,
                'terminal_growth_rate': 0.025,
                'projection_years': 5,
                'current_price': current_price,
                'upside_downside': upside,
                'revenue_growth_rate': company_data.get('revenue_growth', 0),
                'operating_margin': company_data.get('operating_margin', 0.15),
                'tax_rate': 0.25,
                'free_cash_flow': 0,
                'terminal_value': 0,
                'pv_fcf_sum': 0,
                'sensitivity_data': json.dumps({}),
                'narrative': f"自动分析 - {valuation_result.consensus_action}",
                'created_by': 'DCF_Agent',
                'notes': f"行业分类: {industry_classifier.classify(company_data.get('sector'), company_data.get('industry'))[0].value}"
            }
            
            db_service.insert_valuation_result(ticker, valuation_data)
            logger.info(f"Saved valuation result for {ticker}")
            
        except Exception as e:
            logger.error(f"Error saving valuation result for {ticker}: {e}")
    
    def add_ticker(self, ticker: str, locale: str = 'US') -> bool:
        """
        Add a ticker to the database for monitoring
        
        Args:
            ticker: Stock ticker symbol
            locale: Locale (US, CN, etc.)
            
        Returns:
            bool: True if added successfully
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
            bool: True if removed successfully
        """
        try:
            conn = db_service.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM stocks WHERE ticker = %s", (ticker.upper(),))
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
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        task_info = None
        if self.current_task:
            task_info = {
                'task_id': self.current_task.task_id,
                'status': self.current_task.status.value,
                'started_at': self.current_task.started_at.isoformat() if self.current_task.started_at else None,
                'completed_at': self.current_task.completed_at.isoformat() if self.current_task.completed_at else None,
                'tickers_processed': self.current_task.tickers_processed,
                'errors': self.current_task.errors
            }
        
        return {
            'agent_status': self._status.value,
            'is_scheduled': self._is_scheduled,
            'last_analysis': self.last_analysis_time.isoformat() if self.last_analysis_time else None,
            'current_task': task_info
        }
    
    def start_scheduled(self, interval_hours: int = 24) -> bool:
        """
        Start scheduled analysis
        
        Args:
            interval_hours: Hours between analysis runs
            
        Returns:
            bool: True if started successfully
        """
        if self._is_scheduled:
            logger.info("Scheduler already running")
            return True
        
        success = scheduler_service.add_interval_job(
            job_id='dcf_agent_scheduled_analysis',
            func=self.run_scheduled_analysis,
            hours=interval_hours,
            minutes=0,
            replace_existing=True
        )
        
        if success:
            self._is_scheduled = True
            logger.info(f"Scheduled analysis started: every {interval_hours} hours")
        
        return success
    
    def stop_scheduled(self) -> bool:
        """Stop scheduled analysis"""
        if not self._is_scheduled:
            return True
        
        success = scheduler_service.remove_job('dcf_agent_scheduled_analysis')
        
        if success:
            self._is_scheduled = False
            logger.info("Scheduled analysis stopped")
        
        return success
    
    def send_report_email(self, to_email: str = None) -> Dict[str, Any]:
        """
        Manually send portfolio report email
        
        Args:
            to_email: Override recipient email
            
        Returns:
            Dict with send result
        """
        try:
            # Get latest recommendations
            recommendations = portfolio_service.get_latest_recommendations(limit=50)
            
            if not recommendations:
                return {
                    'success': False,
                    'error': 'No recommendations to send'
                }
            
            # Generate report
            portfolio_report = portfolio_service.generate_portfolio_report(recommendations)
            
            # Send email
            result = email_service.send_portfolio_report(
                portfolio_service.to_dict(portfolio_report),
                to_email=to_email
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error sending report email: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Singleton instance
agent_controller = DCFAgentController()
