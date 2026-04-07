"""
Scheduler Service for DCF Valuation Agent
Provides periodic task scheduling using APScheduler
"""
import logging
from datetime import datetime
from typing import Optional, Callable
import threading

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.cron import CronTrigger
from apscheduler.jobstores.memory import MemoryJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.config import AGENT_INTERVAL_HOURS

logger = logging.getLogger(__name__)

# Global scheduler instance
_scheduler: Optional[BackgroundScheduler] = None
_scheduler_lock = threading.Lock()


class SchedulerService:
    """Service for managing scheduled tasks"""
    
    def __init__(self):
        self.scheduler: Optional[BackgroundScheduler] = None
        self.is_running = False
        self._task_lock = threading.Lock()
        self._is_executing = False
    
    def init_scheduler(self) -> bool:
        """
        Initialize the APScheduler instance
        
        Returns:
            bool: True if initialization successful
        """
        try:
            with _scheduler_lock:
                if self.scheduler is not None:
                    logger.info("Scheduler already initialized")
                    return True
                
                jobstores = {
                    'default': MemoryJobStore()
                }
                
                executors = {
                    'default': ThreadPoolExecutor(10)
                }
                
                job_defaults = {
                    'coalesce': True,
                    'max_instances': 1,
                    'misfire_grace_time': 300
                }
                
                self.scheduler = BackgroundScheduler(
                    jobstores=jobstores,
                    executors=executors,
                    job_defaults=job_defaults,
                    timezone='Asia/Shanghai'
                )
                
                logger.info("Scheduler initialized successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to initialize scheduler: {e}")
            return False
    
    def start(self) -> bool:
        """
        Start the scheduler
        
        Returns:
            bool: True if started successfully
        """
        try:
            if self.scheduler is None:
                self.init_scheduler()
            
            if not self.is_running:
                self.scheduler.start()
                self.is_running = True
                logger.info("Scheduler started")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            return False
    
    def stop(self) -> bool:
        """
        Stop the scheduler
        
        Returns:
            bool: True if stopped successfully
        """
        try:
            if self.scheduler and self.is_running:
                self.scheduler.shutdown(wait=True)
                self.is_running = False
                logger.info("Scheduler stopped")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")
            return False
    
    def add_interval_job(
        self,
        job_id: str,
        func: Callable,
        hours: int = None,
        minutes: int = None,
        args: tuple = None,
        kwargs: dict = None,
        replace_existing: bool = True
    ) -> bool:
        """
        Add a job that runs at specified interval
        
        Args:
            job_id: Unique job identifier
            func: Function to execute
            hours: Interval in hours
            minutes: Interval in minutes
            args: Positional arguments for the function
            kwargs: Keyword arguments for the function
            replace_existing: Replace if job with same id exists
            
        Returns:
            bool: True if job added successfully
        """
        try:
            if self.scheduler is None:
                self.init_scheduler()
            
            if not self.is_running:
                self.start()
            
            trigger = IntervalTrigger(hours=hours, minutes=minutes)
            
            self.scheduler.add_job(
                func,
                trigger=trigger,
                id=job_id,
                args=args or (),
                kwargs=kwargs or {},
                replace_existing=replace_existing
            )
            
            logger.info(f"Job '{job_id}' added with interval: {hours}h {minutes}m")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add interval job: {e}")
            return False
    
    def add_cron_job(
        self,
        job_id: str,
        func: Callable,
        hour: int = None,
        minute: int = None,
        day_of_week: str = None,
        args: tuple = None,
        kwargs: dict = None,
        replace_existing: bool = True
    ) -> bool:
        """
        Add a job that runs at specified cron time
        
        Args:
            job_id: Unique job identifier
            func: Function to execute
            hour: Hour (0-23)
            minute: Minute (0-59)
            day_of_week: Day of week (0-6, mon-sun)
            args: Positional arguments
            kwargs: Keyword arguments
            
        Returns:
            bool: True if job added successfully
        """
        try:
            if self.scheduler is None:
                self.init_scheduler()
            
            if not self.is_running:
                self.start()
            
            trigger = CronTrigger(
                hour=hour,
                minute=minute,
                day_of_week=day_of_week
            )
            
            self.scheduler.add_job(
                func,
                trigger=trigger,
                id=job_id,
                args=args or (),
                kwargs=kwargs or {},
                replace_existing=replace_existing
            )
            
            logger.info(f"Cron job '{job_id}' added: {hour}:{minute}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add cron job: {e}")
            return False
    
    def remove_job(self, job_id: str) -> bool:
        """
        Remove a job by ID
        
        Args:
            job_id: Job identifier
            
        Returns:
            bool: True if job removed successfully
        """
        try:
            if self.scheduler:
                self.scheduler.remove_job(job_id)
                logger.info(f"Job '{job_id}' removed")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Failed to remove job: {e}")
            return False
    
    def get_job(self, job_id: str):
        """
        Get a job by ID
        
        Args:
            job_id: Job identifier
            
        Returns:
            Job object or None
        """
        if self.scheduler:
            return self.scheduler.get_job(job_id)
        return None
    
    def get_all_jobs(self) -> list:
        """
        Get all scheduled jobs
        
        Returns:
            List of job objects
        """
        if self.scheduler:
            return self.scheduler.get_jobs()
        return []
    
    def pause_job(self, job_id: str) -> bool:
        """Pause a job"""
        try:
            if self.scheduler:
                self.scheduler.pause_job(job_id)
                logger.info(f"Job '{job_id}' paused")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to pause job: {e}")
            return False
    
    def resume_job(self, job_id: str) -> bool:
        """Resume a paused job"""
        try:
            if self.scheduler:
                self.scheduler.resume_job(job_id)
                logger.info(f"Job '{job_id}' resumed")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to resume job: {e}")
            return False
    
    def run_job_now(self, job_id: str) -> bool:
        """
        Run a job immediately
        
        Args:
            job_id: Job identifier
            
        Returns:
            bool: True if job was found and run
        """
        job = self.get_job(job_id)
        if job:
            job.modify(next_run_time=datetime.now())
            logger.info(f"Job '{job_id}' scheduled to run now")
            return True
        return False
    
    @property
    def is_executing(self) -> bool:
        """Check if a job is currently executing"""
        return self._is_executing
    
    @is_executing.setter
    def is_executing(self, value: bool):
        """Set executing flag"""
        with self._task_lock:
            self._is_executing = value


# Singleton instance
scheduler_service = SchedulerService()


def setup_agent_scheduler(agent_func: Callable, interval_hours: int = None) -> bool:
    """
    Setup the DCF Agent to run on a schedule
    
    Args:
        agent_func: The agent function to schedule
        interval_hours: Hours between runs (default from config)
        
    Returns:
        bool: True if setup successful
    """
    interval = interval_hours or AGENT_INTERVAL_HOURS
    
    success = scheduler_service.add_interval_job(
        job_id='dcf_agent_analysis',
        func=agent_func,
        hours=interval,
        minutes=0,
        replace_existing=True
    )
    
    if success:
        logger.info(f"DCF Agent scheduler setup: every {interval} hours")
    
    return success
