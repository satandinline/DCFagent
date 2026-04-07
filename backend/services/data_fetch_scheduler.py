"""
Scheduled Data Fetch Scheduler for DCF Valuation Agent

This service handles automatic data fetching at scheduled times (12:00 and 00:00).
Features:
- Checks for new data since last fetch
- Only triggers analysis if new data is available
- Only sends reports if analysis finds new insights
- Records all fetch operations for audit trail
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Callable
from datetime import datetime, timedelta
import logging
import json
import threading
import asyncio

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.services.db_service import db_service
from backend.config import AGENT_ENABLED
from backend.utils import retry_with_backoff, circuit_breaker, fallback

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: Optional[BackgroundScheduler] = None
_scheduler_lock = threading.Lock()


class DataFetchScheduler:
    """
    Scheduler for automatic data fetching
    
    Runs at:
    - 12:00 (noon) - Daily check
    - 00:00 (midnight) - Daily check
    
    Workflow:
    1. Get all tickers from database
    2. For each ticker, check if new data is available since last fetch
    3. If new data found:
       - Fetch the new data
       - Run analysis
       - Generate report
       - Send to users
    4. If no new data:
       - Log the fetch but skip analysis and reporting
    5. Record all operations in data_fetch_logs
    """
    
    def __init__(self):
        self.scheduler: Optional[BackgroundScheduler] = None
        self.is_running = False
        self._lock = threading.Lock()
        self._is_fetching = False
        
        # Default configuration
        self.config = {
            'fetch_hours': [0, 12],  # 00:00 and 12:00
            'fetch_minute': 0,
            'timezone': 'Asia/Shanghai',
            'batch_size': 10,  # Process tickers in batches
            'analysis_enabled': True,
            'report_enabled': True,
            'notification_emails': []
        }
        
        logger.info("DataFetchScheduler initialized")
    
    def init_scheduler(self) -> bool:
        """Initialize the APScheduler for data fetching"""
        try:
            with _scheduler_lock:
                if self.scheduler is not None:
                    return True
                
                from apscheduler.jobstores.memory import MemoryJobStore
                from apscheduler.executors.pool import ThreadPoolExecutor
                
                jobstores = {
                    'default': MemoryJobStore()
                }
                
                executors = {
                    'default': ThreadPoolExecutor(5)
                }
                
                job_defaults = {
                    'coalesce': True,
                    'max_instances': 1,
                    'misfire_grace_time': 3600  # 1 hour grace
                }
                
                self.scheduler = BackgroundScheduler(
                    jobstores=jobstores,
                    executors=executors,
                    job_defaults=job_defaults,
                    timezone=self.config['timezone']
                )
                
                logger.info("DataFetchScheduler scheduler initialized")
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {e}")
            return False
    
    def start(self) -> bool:
        """Start the scheduler"""
        try:
            if self.scheduler is None:
                self.init_scheduler()
            
            if not self.is_running:
                self.scheduler.start()
                self.is_running = True
                logger.info("DataFetchScheduler started")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            return False
    
    def stop(self) -> bool:
        """Stop the scheduler"""
        try:
            if self.scheduler and self.is_running:
                self.scheduler.shutdown(wait=True)
                self.is_running = False
                logger.info("DataFetchScheduler stopped")
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")
            return False
    
    def setup_scheduled_jobs(self) -> bool:
        """
        Setup the cron jobs for 12:00 and 00:00
        
        Returns:
            bool: True if jobs were setup successfully
        """
        try:
            if self.scheduler is None:
                self.init_scheduler()
            
            if not self.is_running:
                self.start()
            
            # Job 1: Midnight (00:00)
            self.scheduler.add_job(
                func=self.run_scheduled_fetch,
                trigger=CronTrigger(hour=0, minute=0, timezone=self.config['timezone']),
                id='data_fetch_midnight',
                name='Scheduled Data Fetch (Midnight)',
                replace_existing=True,
                misfire_grace_time=3600
            )
            
            # Job 2: Noon (12:00)
            self.scheduler.add_job(
                func=self.run_scheduled_fetch,
                trigger=CronTrigger(hour=12, minute=0, timezone=self.config['timezone']),
                id='data_fetch_noon',
                name='Scheduled Data Fetch (Noon)',
                replace_existing=True,
                misfire_grace_time=3600
            )
            
            logger.info("Scheduled data fetch jobs setup: 00:00 and 12:00")
            
            # Update task config in database
            db_service.upsert_scheduled_task_config(
                task_name='scheduled_data_fetch',
                enabled=True,
                cron_expression='0 0,12 * * *',
                config=self.config
            )
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup scheduled jobs: {e}")
            return False
    
    def remove_scheduled_jobs(self) -> bool:
        """Remove all scheduled data fetch jobs"""
        try:
            if self.scheduler:
                self.scheduler.remove_job('data_fetch_midnight')
                self.scheduler.remove_job('data_fetch_noon')
            
            db_service.upsert_scheduled_task_config(
                task_name='scheduled_data_fetch',
                enabled=False
            )
            
            logger.info("Scheduled data fetch jobs removed")
            return True
            
        except Exception as e:
            logger.error(f"Failed to remove scheduled jobs: {e}")
            return False
    
    def run_scheduled_fetch(self) -> Dict[str, Any]:
        """
        Main entry point for scheduled data fetch
        
        This is called by APScheduler at 00:00 and 12:00
        
        Returns:
            dict: Summary of the fetch operation
        """
        if self._is_fetching:
            logger.warning("Data fetch already in progress, skipping")
            return {'skipped': True, 'reason': 'already_running'}
        
        with self._lock:
            self._is_fetching = True
        
        try:
            start_time = datetime.now()
            logger.info(f"Starting scheduled data fetch at {start_time}")
            
            # Get all tickers
            tickers = db_service.get_all_tickers()
            
            if not tickers:
                logger.info("No tickers to process")
                return {
                    'success': True,
                    'tickers_checked': 0,
                    'new_data_found': 0,
                    'analysis_triggered': 0,
                    'reports_sent': 0
                }
            
            logger.info(f"Processing {len(tickers)} tickers")
            
            # Process results
            results = {
                'tickers_checked': len(tickers),
                'new_data_found': 0,
                'analysis_triggered': 0,
                'reports_sent': 0,
                'errors': [],
                'ticker_details': []
            }
            
            # Process each ticker
            for ticker in tickers:
                try:
                    ticker_result = self._process_ticker(ticker)
                    results['ticker_details'].append(ticker_result)
                    
                    if ticker_result.get('new_data_found'):
                        results['new_data_found'] += 1
                    if ticker_result.get('analysis_triggered'):
                        results['analysis_triggered'] += 1
                    if ticker_result.get('report_sent'):
                        results['reports_sent'] += 1
                    if ticker_result.get('error'):
                        results['errors'].append({
                            'ticker': ticker,
                            'error': ticker_result['error']
                        })
                        
                except Exception as e:
                    logger.error(f"Error processing ticker {ticker}: {e}")
                    results['errors'].append({
                        'ticker': ticker,
                        'error': str(e)
                    })
            
            # Calculate duration
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            
            # Update task stats
            db_service.update_task_run_stats(
                task_name='scheduled_data_fetch',
                success=len(results['errors']) == 0,
                next_run=self._get_next_run_time()
            )
            
            logger.info(f"Scheduled data fetch completed in {duration:.1f}s: "
                       f"{results['new_data_found']} with new data, "
                       f"{results['analysis_triggered']} analyses, "
                       f"{results['reports_sent']} reports")
            
            return results
            
        finally:
            self._is_fetching = False
    
    def _process_ticker(self, ticker: str) -> Dict[str, Any]:
        """
        Process a single ticker: check for new data, fetch if needed, analyze if new data
        
        Workflow:
        1. Get last fetch date from database
        2. Check if there is truly NEW data since last fetch
        3. If no new data, skip everything (no fetch, no analysis, no report)
        4. If new data found:
           - Fetch the new data
           - Compare with previous snapshot
           - Only trigger analysis if data actually changed
           - Only send report if analysis found new insights
        5. Record everything in data_fetch_logs
        """
        result = {
            'ticker': ticker,
            'new_data_found': False,
            'analysis_triggered': False,
            'report_sent': False,
            'records_fetched': 0,
            'data_changed': False,
            'error': None,
            'fetched_summary': None
        }
        
        # Get last fetch date
        last_fetch = db_service.get_last_fetch_date(ticker)
        
        if last_fetch is None:
            # First time fetch - consider all data as "new"
            last_fetch = datetime(2000, 1, 1)  # Very old date to get all data
            logger.info(f"First time fetch for {ticker}, will fetch all available data")
        
        # Get snapshot BEFORE fetching (for comparison)
        previous_snapshot = db_service.get_latest_data_snapshot(ticker)
        
        # Check for new data in database
        try:
            has_new_in_db = db_service.has_new_data_since(ticker, last_fetch)
        except Exception as e:
            logger.warning(f"Error checking for new data for {ticker}: {e}")
            has_new_in_db = True  # Assume new data if we can't check
        
        # Check if we actually need to fetch new data
        if not has_new_in_db:
            logger.info(f"No new data in database for {ticker} since {last_fetch}, skipping")
            
            # Log the check but note no new data
            fetch_log_id = db_service.insert_data_fetch_log(
                ticker=ticker,
                fetch_type='scheduled',
                data_found=False,
                new_data_available=False,
                records_fetched=0,
                details=json.dumps({
                    'last_fetch': str(last_fetch),
                    'check_time': datetime.now().isoformat(),
                    'reason': 'no_new_data_in_db'
                })
            )
            return result
        
        # We have new data in database, now fetch and verify it
        result['new_data_found'] = True
        
        # Fetch new data
        fetch_result = None
        try:
            fetch_result = self._fetch_new_data(ticker, last_fetch)
            result['records_fetched'] = fetch_result.get('records_fetched', 0)
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {e}")
            result['error'] = f"Fetch error: {str(e)}"
            
            fetch_log_id = db_service.insert_data_fetch_log(
                ticker=ticker,
                fetch_type='scheduled',
                data_found=True,
                new_data_available=True,
                records_fetched=0,
                error_message=str(e),
                details=json.dumps({
                    'last_fetch': str(last_fetch),
                    'check_time': datetime.now().isoformat(),
                    'error': str(e)
                })
            )
            return result
        
        if not fetch_result.get('success'):
            result['error'] = fetch_result.get('error', 'Fetch failed')
            return result
        
        # Get the data changes since last fetch
        data_changes = db_service.get_data_changes_since(ticker, last_fetch)
        result['data_changed'] = data_changes.get('has_changes', False)
        
        # Build data summary for logging
        fetched_summary = self._build_fetch_summary(
            ticker, 
            fetch_result.get('data', {}),
            data_changes
        )
        result['fetched_summary'] = fetched_summary
        
        # Log the fetch with data details
        fetch_log_id = db_service.insert_data_fetch_log(
            ticker=ticker,
            fetch_type='scheduled',
            data_found=True,
            new_data_available=data_changes.get('has_changes', False),
            records_fetched=fetch_result.get('records_fetched', 0),
            fetched_data_summary=json.dumps(fetched_summary),
            fetched_data_snapshot=json.dumps(data_changes),
            details=json.dumps({
                'last_fetch': str(last_fetch),
                'fetch_time': datetime.now().isoformat(),
                'has_data_changes': data_changes.get('has_changes', False)
            })
        )
        
        # Only continue if data actually changed
        if not data_changes.get('has_changes', False):
            logger.info(f"No actual data changes for {ticker}, skipping analysis and report")
            return result
        
        # Run analysis only if data changed
        if self.config.get('analysis_enabled', True):
            try:
                analysis_result = self._run_analysis(ticker)
                result['analysis_triggered'] = analysis_result.get('success', False)
                
                # Only send report if analysis was successful
                if result['analysis_triggered'] and self.config.get('report_enabled', True):
                    report_result = self._send_report(ticker, analysis_result)
                    result['report_sent'] = report_result.get('success', False)
                
                # Update log with analysis/report status
                db_service.update_data_fetch_log(
                    fetch_log_id,
                    analysis_triggered=result['analysis_triggered'],
                    report_sent=result['report_sent']
                )
                    
            except Exception as e:
                logger.error(f"Error in analysis/report for {ticker}: {e}")
                result['error'] = f"Analysis/report error: {str(e)}"
                db_service.update_data_fetch_log(
                    fetch_log_id,
                    error_message=str(e)
                )
        
        return result
    
    def _build_fetch_summary(self, ticker: str, fetched_data: Dict[str, Any], 
                            data_changes: Dict[str, Any]) -> Dict[str, Any]:
        """Build a summary of the fetched data for logging"""
        summary = {
            'ticker': ticker,
            'fetch_time': datetime.now().isoformat(),
            'new_income_statements': len(data_changes.get('new_income_statements', [])),
            'new_balance_sheets': len(data_changes.get('new_balance_sheets', [])),
            'new_cash_flows': len(data_changes.get('new_cash_flows', [])),
            'new_prices_count': data_changes.get('new_prices_count', 0),
            'has_changes': data_changes.get('has_changes', False)
        }
        
        # Add key metrics from fetched data
        if fetched_data:
            summary['metrics'] = {
                'current_price': fetched_data.get('current_price'),
                'revenue': fetched_data.get('revenue'),
                'net_income': fetched_data.get('net_income'),
                'market_cap': fetched_data.get('market_cap'),
                'pe_ratio': fetched_data.get('pe_ratio')
            }
        
        # Add new data details
        if data_changes.get('new_income_statements'):
            latest_inc = data_changes['new_income_statements'][0]
            summary['latest_income'] = {
                'report_date': str(latest_inc.get('report_date', '')),
                'total_revenue': latest_inc.get('total_revenue'),
                'net_income': latest_inc.get('net_income')
            }
        
        return summary
    
    def _fetch_new_data(self, ticker: str, since_date: datetime) -> Dict[str, Any]:
        """
        Fetch new data for a ticker from Yahoo Finance
        
        Returns:
            dict with keys: success, records_fetched, data, error
        """
        logger.info(f"Fetching new data for {ticker} since {since_date}")
        
        try:
            # Import the fetcher
            from backend.tools.data_fetchers import YahooFinanceFetcher
            
            fetcher = YahooFinanceFetcher()
            
            # Fetch company info
            info_result = fetcher.execute(ticker=ticker, data_type='info')
            
            # Fetch financial statements
            financials_result = fetcher.execute(ticker=ticker, data_type='financials')
            
            # Fetch recent price history (last 7 days)
            history_result = fetcher.execute(ticker=ticker, data_type='history', period='7d')
            
            if not info_result.success:
                return {
                    'success': False,
                    'records_fetched': 0,
                    'error': info_result.error or 'Failed to fetch company info'
                }
            
            # Combine results
            combined_data = {
                'info': info_result.data,
                'financials': financials_result.data if financials_result.success else None,
                'history': history_result.data if history_result.success else None,
                'fetch_time': datetime.now().isoformat()
            }
            
            # Count records fetched
            records = 0
            if info_result.success:
                records += 1
            if financials_result.success and financials_result.data:
                records += 3  # income, balance, cashflow
            if history_result.success and history_result.data:
                records += history_result.data.get('data_points', 0)
            
            logger.info(f"Successfully fetched data for {ticker}: {records} records")
            
            return {
                'success': True,
                'records_fetched': records,
                'data': combined_data
            }
                
        except Exception as e:
            logger.error(f"Error in _fetch_new_data for {ticker}: {e}")
            return {
                'success': False,
                'records_fetched': 0,
                'error': str(e)
            }
    
    def _run_analysis(self, ticker: str) -> Dict[str, Any]:
        """
        Run analysis for a ticker after new data is fetched
        """
        logger.info(f"Running analysis for {ticker}")
        
        try:
            # Import and use the CoordinatorAgent
            from backend.agents.coordinator import CoordinatorAgent
            
            coordinator = CoordinatorAgent()
            result = coordinator.run_valuation_workflow({
                'ticker': ticker,
                'force_update': True
            })
            
            return {
                'success': result.success,
                'data': result.data if result.success else None,
                'error': result.error if not result.success else None
            }
            
        except Exception as e:
            logger.error(f"Error in _run_analysis for {ticker}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _send_report(self, ticker: str, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send report for a ticker
        """
        logger.info(f"Sending report for {ticker}")
        
        try:
            # Import notification agent
            from backend.agents.notification_agent import NotificationAgent
            
            notification_agent = NotificationAgent()
            
            recipients = self.config.get('notification_emails', [])
            
            if not recipients:
                # Try to get default recipients from config
                from backend.config import DEFAULT_REPORT_EMAIL
                if DEFAULT_REPORT_EMAIL:
                    recipients = [DEFAULT_REPORT_EMAIL]
            
            if not recipients:
                logger.warning(f"No recipients configured for reports")
                return {
                    'success': False,
                    'error': 'No recipients configured'
                }
            
            result = notification_agent.send_valuation_report(
                ticker=ticker,
                recipients=recipients,
                analysis_result=analysis_result.get('data', {}),
                report_format='html'
            )
            
            return {
                'success': result.success,
                'recipients': recipients
            }
            
        except Exception as e:
            logger.error(f"Error in _send_report for {ticker}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _get_next_run_time(self) -> Optional[datetime]:
        """Get the next scheduled run time"""
        try:
            if self.scheduler:
                job = self.scheduler.get_job('data_fetch_midnight')
                if job and job.next_run_time:
                    return job.next_run_time
        except Exception as e:
            logger.warning(f"Error getting next run time: {e}")
        return None
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the scheduler"""
        try:
            # Get task config
            task_config = db_service.get_scheduled_task_config('scheduled_data_fetch')
            
            # Get recent summary
            summary = db_service.get_data_fetch_summary(days=7)
            
            # Get next run
            next_run = self._get_next_run_time()
            
            return {
                'is_running': self.is_running,
                'is_fetching': self._is_fetching,
                'task_enabled': task_config.get('enabled', False) if task_config else False,
                'next_run': str(next_run) if next_run else None,
                'config': self.config,
                'recent_summary': summary
            }
            
        except Exception as e:
            logger.error(f"Error getting status: {e}")
            return {
                'error': str(e)
            }
    
    def run_now(self) -> Dict[str, Any]:
        """
        Run the scheduled fetch immediately (manual trigger)
        """
        logger.info("Manual trigger: Running scheduled data fetch now")
        return self.run_scheduled_fetch()
    
    def update_config(self, config: Dict[str, Any]) -> bool:
        """Update scheduler configuration"""
        try:
            self.config.update(config)
            
            # Persist to database
            db_service.upsert_scheduled_task_config(
                task_name='scheduled_data_fetch',
                enabled=self.config.get('enabled', True),
                config=self.config
            )
            
            logger.info(f"Scheduler config updated: {config}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating config: {e}")
            return False


# Singleton instance
data_fetch_scheduler = DataFetchScheduler()


def get_data_fetch_scheduler() -> DataFetchScheduler:
    """Get the global data fetch scheduler instance"""
    return data_fetch_scheduler
