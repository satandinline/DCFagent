"""
Coordinator Agent for DCF Valuation System

Orchestrates multi-agent workflows and manages the overall analysis process
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Callable
import logging
import json
from datetime import datetime
import uuid

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from backend.agents.base_agent import BaseAgent, AgentResult, AgentCapability
from backend.agents.data_agent import DataAgent
from backend.agents.analysis_agent import AnalysisAgent
from backend.agents.notification_agent import NotificationAgent
from backend.memory.vector_store import get_memory_store
from backend.workflow.approval_nodes import ApprovalNode, get_approval_manager

logger = logging.getLogger(__name__)


class CoordinatorAgent(BaseAgent):
    """
    Coordinator Agent - Orchestrates multi-agent collaboration
    
    This is the main agent that:
    - Coordinates DataAgent, AnalysisAgent, and NotificationAgent
    - Manages the workflow state
    - Handles approvals
    - Stores results in memory
    - Provides the main API for valuation requests
    
    Architecture:
    
        User Request
              │
              ▼
    ┌─────────────────┐
    │ Coordinator     │
    │   Agent         │
    └────────┬────────┘
             │
       ┌─────┴─────┬─────────────┐
       ▼           ▼             ▼
    ┌──────┐  ┌──────────┐  ┌──────────────┐
    │Data  │  │ Analysis │  │ Notification │
    │Agent │  │  Agent   │  │    Agent     │
    └──────┘  └──────────┘  └──────────────┘
       │           │             │
       └───────────┴─────────────┘
                     │
                     ▼
              ┌─────────────┐
              │   Memory    │
              │   Store     │
              └─────────────┘
    """
    
    name = "coordinator_agent"
    role = "Workflow Coordinator"
    description = "Orchestrates multi-agent valuation workflow"
    
    def __init__(self):
        """Initialize Coordinator with sub-agents"""
        # Initialize sub-agents
        self.data_agent = DataAgent()
        self.analysis_agent = AnalysisAgent()
        self.notification_agent = NotificationAgent()
        
        # Initialize approval handling
        self.approval_node = ApprovalNode()
        
        # Initialize memory
        self.memory_store = get_memory_store()
        
        # Workflow state
        self._workflows: Dict[str, Dict[str, Any]] = {}
        
        super().__init__()
    
    def _initialize_capabilities(self):
        """Initialize Coordinator capabilities"""
        self._capabilities = {
            AgentCapability.DATA_FETCH,
            AgentCapability.FINANCIAL_ANALYSIS,
            AgentCapability.VALUATION,
            AgentCapability.NOTIFICATION,
            AgentCapability.REPORTING,
            AgentCapability.MEMORY,
            AgentCapability.LLM_REASONING,
        }
    
    def _initialize_tools(self):
        """Initialize Coordinator tools"""
        # Coordinator uses sub-agents, not direct tools
        self._tools = []
    
    def _get_supported_task_types(self) -> List[str]:
        """Get list of supported task types"""
        return [
            'run_valuation',
            'run_batch_valuation',
            'scheduled_valuation',
            'check_approval_status',
            'handle_approval_callback',
        ]
    
    def _execute_task(self, task: Dict[str, Any]) -> AgentResult:
        """Execute coordinated task"""
        task_type = task.get('type')
        
        if task_type == 'run_valuation':
            return self.run_valuation_workflow(task)
        elif task_type == 'run_batch_valuation':
            return self.run_batch_valuation(task)
        elif task_type == 'scheduled_valuation':
            return self.run_scheduled_valuation(task)
        elif task_type == 'check_approval_status':
            return self._check_approval_status(task)
        elif task_type == 'handle_approval_callback':
            return self._handle_approval_callback(task)
        else:
            return AgentResult(
                success=False,
                error=f"Unknown task type: {task_type}"
            )
    
    def run_valuation_workflow(self, task: Dict[str, Any]) -> AgentResult:
        """
        Run the complete valuation workflow for a single stock
        
        Workflow steps:
        1. Create workflow context
        2. Fetch data (DataAgent)
        3. Perform valuation (AnalysisAgent)
        4. Check for approval requirements
        5. Store in memory
        6. Send notification (if configured)
        """
        ticker = task.get('ticker')
        
        if not ticker:
            return AgentResult(success=False, error="Ticker not provided")
        
        # Create workflow ID
        workflow_id = str(uuid.uuid4())
        logger.info(f"Starting valuation workflow {workflow_id} for {ticker}")
        
        # Initialize workflow state
        state = {
            'workflow_id': workflow_id,
            'ticker': ticker,
            'start_time': datetime.now().isoformat(),
            'status': 'running',
            'steps_completed': [],
            'requires_approval': False,
            'approval_request_id': None
        }
        
        try:
            # Step 1: Fetch data
            logger.info(f"[{workflow_id}] Step 1: Fetching data")
            data_result = self.data_agent.run({
                'type': 'fetch_all_data',
                'ticker': ticker
            })
            
            if not data_result.success:
                state['status'] = 'failed'
                state['error'] = f"Data fetch failed: {data_result.error}"
                return AgentResult(success=False, error=state['error'], metadata=state)
            
            state['stock_data'] = data_result.data
            state['steps_completed'].append('data_fetch')
            
            # Step 2: Perform valuation
            logger.info(f"[{workflow_id}] Step 2: Performing analysis")
            analysis_result = self.analysis_agent.analyze(
                ticker=ticker,
                data=data_result.data
            )
            
            if not analysis_result.success:
                state['status'] = 'failed'
                state['error'] = f"Analysis failed: {analysis_result.error}"
                return AgentResult(success=False, error=state['error'], metadata=state)
            
            state['analysis_result'] = analysis_result.data
            state['steps_completed'].append('analysis')
            
            # Step 3: Check for approval requirements
            logger.info(f"[{workflow_id}] Step 3: Checking approval requirements")
            state['analysis_result']['ticker'] = ticker
            
            approval_request = self.approval_node.check_and_create_request(state)
            
            if approval_request:
                state['requires_approval'] = True
                state['approval_request_id'] = approval_request.id
                state['status'] = 'awaiting_approval'
                
                # Store workflow for later completion
                self._workflows[workflow_id] = state
                
                return AgentResult(
                    success=True,
                    data={
                        'workflow_id': workflow_id,
                        'status': 'awaiting_approval',
                        'approval_request_id': approval_request.id,
                        'approval_required': True,
                        'preview': self._generate_preview(analysis_result.data)
                    },
                    metadata=state
                )
            
            # Step 4: Complete workflow (no approval needed)
            return self._complete_workflow(state, analysis_result.data)
            
        except Exception as e:
            logger.exception(f"Workflow {workflow_id} failed: {e}")
            state['status'] = 'failed'
            state['error'] = str(e)
            return AgentResult(success=False, error=str(e), metadata=state)
    
    def _complete_workflow(
        self,
        state: Dict[str, Any],
        analysis_result: Dict[str, Any]
    ) -> AgentResult:
        """Complete the workflow after all steps are done"""
        workflow_id = state.get('workflow_id', 'unknown')
        ticker = state.get('ticker')
        
        # Update state
        state['status'] = 'completed'
        state['end_time'] = datetime.now().isoformat()
        state['steps_completed'].append('complete')
        
        # Store in memory
        if self.memory_store:
            try:
                self.memory_store.add_analysis({
                    'ticker': ticker,
                    **analysis_result,
                    'timestamp': datetime.now().isoformat()
                })
                logger.info(f"[{workflow_id}] Stored result in memory")
            except Exception as e:
                logger.warning(f"Failed to store in memory: {e}")
        
        # Send notification if configured
        if state.get('notify_on_complete'):
            self._send_completion_notification(state, analysis_result)
        
        logger.info(f"[{workflow_id}] Workflow completed")
        
        return AgentResult(
            success=True,
            data={
                'workflow_id': workflow_id,
                'ticker': ticker,
                'status': 'completed',
                'analysis': analysis_result,
                'requires_approval': False
            },
            metadata=state
        )
    
    def _check_approval_status(self, task: Dict[str, Any]) -> AgentResult:
        """Check the status of an approval request"""
        workflow_id = task.get('workflow_id')
        
        if not workflow_id:
            return AgentResult(success=False, error="Workflow ID not provided")
        
        state = self._workflows.get(workflow_id)
        
        if not state:
            return AgentResult(success=False, error="Workflow not found")
        
        approval_id = state.get('approval_request_id')
        
        if not approval_id:
            return AgentResult(success=False, error="No pending approval")
        
        # Get approval status
        approval_manager = get_approval_manager()
        approval = approval_manager.get_request(approval_id)
        
        if not approval:
            return AgentResult(success=False, error="Approval request not found")
        
        return AgentResult(
            success=True,
            data={
                'workflow_id': workflow_id,
                'approval_id': approval_id,
                'status': approval.status.value,
                'risk_level': approval.risk_level.value
            },
            metadata={'approval': approval.to_dict()}
        )
    
    def _handle_approval_callback(
        self,
        task: Dict[str, Any]
    ) -> AgentResult:
        """Handle approval/rejection callback"""
        workflow_id = task.get('workflow_id')
        approved = task.get('approved', False)
        approver = task.get('approver', 'unknown')
        comments = task.get('comments')
        
        if not workflow_id:
            return AgentResult(success=False, error="Workflow ID not provided")
        
        state = self._workflows.get(workflow_id)
        
        if not state:
            return AgentResult(success=False, error="Workflow not found")
        
        # Update state with approval result
        state = self.approval_node.handle_approval_callback(
            state,
            approved=approved,
            approver=approver,
            comments=comments
        )
        
        if state.get('approval_status') == 'approved':
            # Continue with workflow completion
            return self._complete_workflow(state, state.get('analysis_result', {}))
        else:
            # Workflow rejected
            state['status'] = 'rejected'
            state['end_time'] = datetime.now().isoformat()
            
            return AgentResult(
                success=False,
                data={
                    'workflow_id': workflow_id,
                    'status': 'rejected',
                    'approver': approver,
                    'comments': comments
                },
                metadata=state
            )
    
    def run_batch_valuation(self, task: Dict[str, Any]) -> AgentResult:
        """Run valuation for multiple stocks"""
        tickers = task.get('tickers', [])
        
        if not tickers:
            return AgentResult(success=False, error="No tickers provided")
        
        logger.info(f"Starting batch valuation for {len(tickers)} stocks")
        
        results = []
        pending_approvals = []
        
        for ticker in tickers:
            result = self.run_valuation_workflow({'ticker': ticker})
            
            workflow_result = {
                'ticker': ticker,
                'success': result.success,
                'workflow_id': result.data.get('workflow_id') if result.data else None
            }
            
            if result.success:
                if result.data.get('requires_approval'):
                    pending_approvals.append(workflow_result)
                else:
                    results.append(workflow_result)
            else:
                results.append({
                    'ticker': ticker,
                    'success': False,
                    'error': result.error
                })
        
        # Return summary
        return AgentResult(
            success=True,
            data={
                'total': len(tickers),
                'completed': len([r for r in results if r['success'] and 'workflow_id' in r]),
                'pending_approval': len(pending_approvals),
                'failed': len([r for r in results if not r['success']]),
                'results': results,
                'pending_approvals': pending_approvals
            },
            metadata={
                'batch_id': str(uuid.uuid4()),
                'tickes_processed': len(tickers)
            }
        )
    
    def run_scheduled_valuation(self, task: Dict[str, Any]) -> AgentResult:
        """Run scheduled valuation (called by scheduler)"""
        tickers = task.get('tickers', [])
        notification_recipients = task.get('notify', [])
        
        if not tickers:
            return AgentResult(success=False, error="No tickers provided")
        
        logger.info(f"Running scheduled valuation for {len(tickers)} stocks")
        
        # Run batch valuation
        batch_result = self.run_batch_valuation({
            'tickers': tickers,
            'notify_on_complete': True,
            'notification_recipients': notification_recipients
        })
        
        # Send summary notification if recipients configured
        if notification_recipients and batch_result.success:
            self._send_batch_summary_notification(
                batch_result.data,
                notification_recipients
            )
        
        return batch_result
    
    def _send_completion_notification(
        self,
        state: Dict[str, Any],
        analysis_result: Dict[str, Any]
    ) -> None:
        """Send notification when workflow completes"""
        try:
            recipients = state.get('notification_recipients', [])
            
            if recipients:
                self.notification_agent.send_valuation_report(
                    ticker=state.get('ticker'),
                    recipients=recipients,
                    analysis_result=analysis_result
                )
        except Exception as e:
            logger.warning(f"Failed to send completion notification: {e}")
    
    def _send_batch_summary_notification(
        self,
        batch_data: Dict[str, Any],
        recipients: List[str]
    ) -> None:
        """Send summary notification for batch operation"""
        try:
            summary = f"""
Batch Valuation Complete

Total: {batch_data['total']}
Completed: {batch_data['completed']}
Pending Approval: {batch_data['pending_approval']}
Failed: {batch_data['failed']}
"""
            
            for recipient in recipients:
                self.notification_agent.run({
                    'type': 'send_email',
                    'to': recipient,
                    'subject': 'Batch Valuation Complete',
                    'body': summary
                })
        except Exception as e:
            logger.warning(f"Failed to send batch summary: {e}")
    
    def _generate_preview(self, analysis_result: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a preview of the analysis for approval"""
        return {
            'ticker': analysis_result.get('ticker'),
            'action': analysis_result.get('action'),
            'upside': analysis_result.get('upside_percent'),
            'confidence': analysis_result.get('confidence'),
            'fair_value': analysis_result.get('fair_value'),
            'current_price': analysis_result.get('current_price')
        }
    
    def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get the status of a workflow"""
        return self._workflows.get(workflow_id)
    
    def list_pending_workflows(self) -> List[Dict[str, Any]]:
        """List all workflows awaiting approval"""
        return [
            {
                'workflow_id': wid,
                'ticker': state.get('ticker'),
                'status': state.get('status'),
                'approval_id': state.get('approval_request_id')
            }
            for wid, state in self._workflows.items()
            if state.get('status') == 'awaiting_approval'
        ]


# =============================================================================
# Factory Functions
# =============================================================================

def create_coordinator() -> CoordinatorAgent:
    """Create a new CoordinatorAgent instance"""
    return CoordinatorAgent()


def register_all_agents():
    """Register all agents with the agent registry"""
    from backend.agents.base_agent import AgentRegistry, get_agent_registry
    
    registry = get_agent_registry()
    
    agents = [
        DataAgent(),
        AnalysisAgent(),
        NotificationAgent(),
        CoordinatorAgent()
    ]
    
    for agent in agents:
        registry.register(agent)
    
    logger.info(f"Registered {len(agents)} agents")
    
    return registry
