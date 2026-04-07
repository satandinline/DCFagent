"""
Human-in-the-Loop Approval Nodes for DCF Valuation Agent
Provides approval workflow for high-risk decisions
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import logging
import uuid

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from backend.tools.base import ToolResult

logger = logging.getLogger(__name__)


class ApprovalStatus(Enum):
    """Approval request status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class RiskLevel(Enum):
    """Risk level for decisions"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class ApprovalRequest:
    """Represents an approval request"""
    id: str
    requestor: str
    request_type: str
    description: str
    risk_level: RiskLevel
    status: ApprovalStatus
    details: Dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    expires_at: str = None
    approver_comments: str = None
    approver: str = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'id': self.id,
            'requestor': self.requestor,
            'request_type': self.request_type,
            'description': self.description,
            'risk_level': self.risk_level.value,
            'status': self.status.value,
            'details': self.details,
            'created_at': self.created_at,
            'updated_at': self.updated_at,
            'expires_at': self.expires_at,
            'approver_comments': self.approver_comments,
            'approver': self.approver
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ApprovalRequest':
        return cls(
            id=data['id'],
            requestor=data['requestor'],
            request_type=data['request_type'],
            description=data['description'],
            risk_level=RiskLevel(data['risk_level']),
            status=ApprovalStatus(data['status']),
            details=data.get('details', {}),
            created_at=data.get('created_at', datetime.now().isoformat()),
            updated_at=data.get('updated_at', datetime.now().isoformat()),
            expires_at=data.get('expires_at'),
            approver_comments=data.get('approver_comments'),
            approver=data.get('approver')
        )


class ApprovalManager:
    """
    Manages approval workflow for high-risk decisions
    
    Features:
    - Automatic risk assessment
    - Multi-level approval based on risk
    - Configurable thresholds
    - Notification integration
    """
    
    # Risk thresholds
    HIGH_RISK_THRESHOLDS = {
        'sell_action': True,           # Any SELL recommendation
        'upside_below': -15.0,         # Downside more than 15%
        'upside_above': 100.0,        # Upside above 100% (unusual)
        'confidence_low': True,         # Low confidence analysis
        'model_failed': True,           # Primary model failed
        'data_quality_low': True,      # Low quality input data
    }
    
    # Risk to approval level mapping
    RISK_APPROVAL_LEVELS = {
        RiskLevel.LOW: 0,      # No approval needed
        RiskLevel.MEDIUM: 1,   # One approver
        RiskLevel.HIGH: 2,     # Two approvers
        RiskLevel.CRITICAL: 3  # Committee approval
    }
    
    def __init__(self, notification_callback: Callable = None):
        """
        Initialize Approval Manager
        
        Args:
            notification_callback: Function to call when approval is needed
        """
        self._pending_requests: Dict[str, ApprovalRequest] = {}
        self._approval_history: List[ApprovalRequest] = []
        self.notification_callback = notification_callback
        self._default_timeout_minutes = 60
        
        logger.info("ApprovalManager initialized")
    
    def assess_risk(self, analysis_result: Dict[str, Any]) -> RiskLevel:
        """
        Assess the risk level of an analysis result
        
        Args:
            analysis_result: The valuation analysis result
            
        Returns:
            RiskLevel enum
        """
        risk_score = 0
        risk_factors = []
        
        # Check SELL action
        if analysis_result.get('action') == 'SELL':
            risk_score += 3
            risk_factors.append('SELL action')
        
        # Check upside
        upside = analysis_result.get('upside_percent', 0)
        if upside < self.HIGH_RISK_THRESHOLDS['upside_below']:
            risk_score += 2
            risk_factors.append(f'Strong downside ({upside:.1f}%)')
        elif upside > self.HIGH_RISK_THRESHOLDS['upside_above']:
            risk_score += 1
            risk_factors.append(f'Unusually high upside ({upside:.1f}%)')
        
        # Check confidence
        confidence = analysis_result.get('confidence', 'medium').lower()
        if confidence == 'low':
            risk_score += 2
            risk_factors.append('Low confidence')
        elif confidence == 'medium':
            risk_score += 1
        
        # Check if model failed
        if analysis_result.get('model_failed', False):
            risk_score += 2
            risk_factors.append('Primary model failed')
        
        # Check data quality
        if analysis_result.get('data_quality') == 'low':
            risk_score += 1
            risk_factors.append('Low data quality')
        
        # Check valuation spread (disagreement between methods)
        methods = analysis_result.get('methods_used', [])
        if len(set(methods)) > 1:
            # Multiple methods used - check for disagreement
            results = analysis_result.get('method_results', {})
            if len(results) > 1:
                # Calculate spread
                prices = [r.get('per_share_value', 0) for r in results.values() if r.get('per_share_value')]
                if prices:
                    spread = (max(prices) - min(prices)) / min(prices) * 100 if min(prices) > 0 else 0
                    if spread > 50:
                        risk_score += 2
                        risk_factors.append(f'High valuation spread ({spread:.1f}%)')
        
        # Determine risk level
        if risk_score >= 6:
            return RiskLevel.CRITICAL
        elif risk_score >= 4:
            return RiskLevel.HIGH
        elif risk_score >= 2:
            return RiskLevel.MEDIUM
        else:
            return RiskLevel.LOW
    
    def requires_approval(self, analysis_result: Dict[str, Any]) -> bool:
        """Check if the analysis result requires approval"""
        risk_level = self.assess_risk(analysis_result)
        return risk_level != RiskLevel.LOW
    
    def create_approval_request(
        self,
        requestor: str,
        request_type: str,
        description: str,
        details: Dict[str, Any],
        risk_level: RiskLevel = None,
        timeout_minutes: int = None
    ) -> ApprovalRequest:
        """
        Create a new approval request
        
        Args:
            requestor: Who is requesting approval
            request_type: Type of request (e.g., 'sell_action', 'high_risk_trade')
            description: Human-readable description
            details: Detailed information about the request
            risk_level: Risk level (auto-calculated if not provided)
            timeout_minutes: Request timeout
            
        Returns:
            ApprovalRequest object
        """
        # Auto-calculate risk if not provided
        if risk_level is None:
            risk_level = self.assess_risk(details.get('analysis_result', {}))
        
        # Generate request ID
        request_id = str(uuid.uuid4())
        
        # Calculate expiry time
        timeout = timeout_minutes or self._default_timeout_minutes
        from datetime import timedelta
        expires_at = (datetime.now() + timedelta(minutes=timeout)).isoformat()
        
        # Create request
        request = ApprovalRequest(
            id=request_id,
            requestor=requestor,
            request_type=request_type,
            description=description,
            risk_level=risk_level,
            status=ApprovalStatus.PENDING,
            details=details,
            expires_at=expires_at
        )
        
        # Store request
        self._pending_requests[request_id] = request
        
        # Send notification
        if self.notification_callback:
            self.notification_callback(request)
        
        logger.info(f"Created approval request {request_id} (risk: {risk_level.value})")
        
        return request
    
    def approve(
        self,
        request_id: str,
        approver: str,
        comments: str = None
    ) -> bool:
        """
        Approve a pending request
        
        Args:
            request_id: The request ID
            approver: Who is approving
            comments: Optional comments
            
        Returns:
            True if approved successfully
        """
        if request_id not in self._pending_requests:
            logger.warning(f"Approval request {request_id} not found")
            return False
        
        request = self._pending_requests[request_id]
        
        # Update request
        request.status = ApprovalStatus.APPROVED
        request.approver = approver
        request.approver_comments = comments
        request.updated_at = datetime.now().isoformat()
        
        # Move to history
        self._approval_history.append(request)
        del self._pending_requests[request_id]
        
        logger.info(f"Approved request {request_id} by {approver}")
        
        return True
    
    def reject(
        self,
        request_id: str,
        approver: str,
        comments: str = None
    ) -> bool:
        """
        Reject a pending request
        
        Args:
            request_id: The request ID
            approver: Who is rejecting
            comments: Rejection reason
            
        Returns:
            True if rejected successfully
        """
        if request_id not in self._pending_requests:
            logger.warning(f"Approval request {request_id} not found")
            return False
        
        request = self._pending_requests[request_id]
        
        # Update request
        request.status = ApprovalStatus.REJECTED
        request.approver = approver
        request.approver_comments = comments
        request.updated_at = datetime.now().isoformat()
        
        # Move to history
        self._approval_history.append(request)
        del self._pending_requests[request_id]
        
        logger.info(f"Rejected request {request_id} by {approver}")
        
        return True
    
    def cancel(self, request_id: str) -> bool:
        """Cancel a pending request"""
        if request_id not in self._pending_requests:
            return False
        
        request = self._pending_requests[request_id]
        request.status = ApprovalStatus.CANCELLED
        request.updated_at = datetime.now().isoformat()
        
        self._approval_history.append(request)
        del self._pending_requests[request_id]
        
        return True
    
    def get_pending_requests(self, approver: str = None) -> List[ApprovalRequest]:
        """Get all pending approval requests"""
        requests = list(self._pending_requests.values())
        
        if approver:
            # Filter by approver if specified (for role-based access)
            pass
        
        return sorted(requests, key=lambda x: x.created_at, reverse=True)
    
    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """Get a specific approval request"""
        return self._pending_requests.get(request_id)
    
    def check_expired_requests(self) -> List[str]:
        """Check for and expire old requests"""
        expired_ids = []
        now = datetime.now()
        
        for request_id, request in list(self._pending_requests.items()):
            if request.expires_at:
                from datetime import datetime
                expires = datetime.fromisoformat(request.expires_at)
                if now > expires:
                    request.status = ApprovalStatus.EXPIRED
                    request.updated_at = now.isoformat()
                    self._approval_history.append(request)
                    del self._pending_requests[request_id]
                    expired_ids.append(request_id)
                    logger.info(f"Expired approval request {request_id}")
        
        return expired_ids


class ApprovalNode:
    """
    Workflow node for approval integration with LangGraph
    
    Usage:
        approval_node = ApprovalNode()
        
        # In workflow
        if approval_node.requires_approval(state):
            state = approval_node.create_request(state)
            return "wait_for_approval"  # Pause workflow
        
        # Handle approval callback
        if callback_received:
            result = approval_node.handle_approval(state, approved=True)
            if result.approved:
                return "continue"
            else:
                return "rejected"
    """
    
    def __init__(self, manager: ApprovalManager = None):
        """
        Initialize Approval Node
        
        Args:
            manager: ApprovalManager instance (creates new if not provided)
        """
        self.manager = manager or ApprovalManager()
    
    def check_and_create_request(self, state: Dict[str, Any]) -> Optional[ApprovalRequest]:
        """
        Check if approval is needed and create request if so
        
        Args:
            state: Workflow state containing analysis result
            
        Returns:
            ApprovalRequest if approval needed, None otherwise
        """
        analysis_result = state.get('analysis_result', {})
        
        if not self.manager.requires_approval(analysis_result):
            return None
        
        # Create approval request
        request = self.manager.create_approval_request(
            requestor='DCF_Agent',
            request_type=self._determine_request_type(analysis_result),
            description=self._generate_description(analysis_result),
            details={
                'analysis_result': analysis_result,
                'ticker': state.get('ticker', 'UNKNOWN'),
                'workflow_id': state.get('workflow_id')
            },
            risk_level=self.manager.assess_risk(analysis_result)
        )
        
        # Update state
        state['requires_approval'] = True
        state['approval_request_id'] = request.id
        state['approval_status'] = ApprovalStatus.PENDING.value
        
        return request
    
    def handle_approval_callback(
        self,
        state: Dict[str, Any],
        approved: bool,
        approver: str,
        comments: str = None
    ) -> Dict[str, Any]:
        """
        Handle approval callback and update state
        
        Args:
            state: Workflow state
            approved: Whether approved
            approver: Who approved/rejected
            comments: Optional comments
            
        Returns:
            Updated state
        """
        request_id = state.get('approval_request_id')
        
        if not request_id:
            logger.warning("No approval request ID in state")
            state['approval_status'] = 'error'
            return state
        
        if approved:
            success = self.manager.approve(request_id, approver, comments)
            if success:
                state['approval_status'] = ApprovalStatus.APPROVED.value
                state['approval_approved_by'] = approver
                state['approval_comments'] = comments
            else:
                state['approval_status'] = 'error'
        else:
            success = self.manager.reject(request_id, approver, comments)
            if success:
                state['approval_status'] = ApprovalStatus.REJECTED.value
                state['approval_rejected_by'] = approver
                state['approval_comments'] = comments
            else:
                state['approval_status'] = 'error'
        
        return state
    
    def _determine_request_type(self, analysis_result: Dict) -> str:
        """Determine the type of approval request"""
        action = analysis_result.get('action', '').upper()
        
        if action == 'SELL':
            return 'sell_action'
        elif action == 'BUY':
            return 'buy_action'
        else:
            return 'high_risk_analysis'
    
    def _generate_description(self, analysis_result: Dict) -> str:
        """Generate a human-readable description"""
        ticker = analysis_result.get('ticker', 'UNKNOWN')
        action = analysis_result.get('action', 'HOLD')
        upside = analysis_result.get('upside_percent', 0)
        confidence = analysis_result.get('confidence', 'unknown')
        
        return f"{ticker}: {action} recommendation with {upside:.1f}% upside (confidence: {confidence})"


# =============================================================================
# Global Approval Manager Instance
# =============================================================================

_approval_manager: Optional[ApprovalManager] = None


def get_approval_manager() -> ApprovalManager:
    """Get or create the global approval manager"""
    global _approval_manager
    if _approval_manager is None:
        _approval_manager = ApprovalManager()
    return _approval_manager
