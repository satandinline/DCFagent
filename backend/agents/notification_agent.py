"""
Notification Agent for DCF Valuation System

Specialized agent for notifications and reporting
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
import logging
import json
from datetime import datetime

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from backend.agents.base_agent import BaseAgent, AgentResult, AgentCapability
from backend.tools.registry import tool_registry

logger = logging.getLogger(__name__)


class NotificationAgent(BaseAgent):
    """
    Notification Agent - Specialized for notifications and reporting
    
    Capabilities:
    - Send email notifications
    - Generate PDF/HTML reports
    - Send approval requests
    - Push notifications (webhook)
    - Dashboard updates
    
    Tools used:
    - email_sender
    - report_generator
    - webhook_notifier
    - approval_requester
    """
    
    name = "notification_agent"
    role = "Notification and Reporting Specialist"
    description = "Handles all notifications and report generation"
    
    def _initialize_capabilities(self):
        """Initialize Notification Agent capabilities"""
        self._capabilities = {
            AgentCapability.NOTIFICATION,
            AgentCapability.REPORTING,
        }
    
    def _initialize_tools(self):
        """Initialize Notification Agent tools"""
        self._tools = [
            'email_sender',
            'report_generator',
            'webhook_notifier',
            'generate_pdf_report',
            'generate_html_report',
            'send_approval_notification',
        ]
    
    def _get_supported_task_types(self) -> List[str]:
        """Get list of supported task types"""
        return [
            'send_notification',
            'send_email',
            'generate_report',
            'approval_notification',
            'webhook_notification',
            'send_approval_request',
        ]
    
    def _execute_task(self, task: Dict[str, Any]) -> AgentResult:
        """
        Execute notification-related task
        """
        task_type = task.get('type')
        
        if task_type == 'send_notification':
            return self._send_notification(task)
        elif task_type == 'send_email':
            return self._send_email(task)
        elif task_type == 'generate_report':
            return self._generate_report(task)
        elif task_type == 'approval_notification':
            return self._send_approval_notification(task)
        elif task_type == 'webhook_notification':
            return self._send_webhook_notification(task)
        elif task_type == 'send_approval_request':
            return self._send_approval_request(task)
        else:
            return AgentResult(
                success=False,
                error=f"Unknown task type: {task_type}"
            )
    
    def _send_notification(self, task: Dict[str, Any]) -> AgentResult:
        """Send a generic notification through configured channels"""
        notification_type = task.get('notification_type', 'email')
        content = task.get('content', {})
        
        logger.info(f"Sending {notification_type} notification")
        
        if notification_type == 'email':
            return self._send_email({
                'to': task.get('to'),
                'subject': task.get('subject', 'DCF Valuation Report'),
                'body': task.get('body', ''),
                'attachments': task.get('attachments')
            })
        elif notification_type == 'webhook':
            return self._send_webhook_notification({
                'url': task.get('url'),
                'payload': content
            })
        else:
            return AgentResult(
                success=False,
                error=f"Unknown notification type: {notification_type}"
            )
    
    def _send_email(self, task: Dict[str, Any]) -> AgentResult:
        """Send an email notification"""
        to = task.get('to')
        subject = task.get('subject', 'DCF Valuation Report')
        body = task.get('body', '')
        attachments = task.get('attachments')
        
        if not to:
            return AgentResult(success=False, error="Recipient not specified")
        
        logger.info(f"Sending email to {to}")
        
        params = {
            'to': to,
            'subject': subject,
            'body': body
        }
        
        if attachments:
            params['attachments'] = attachments
        
        result = self.execute_tool('email_sender', **params)
        
        if result and result.success:
            return AgentResult(
                success=True,
                data={'sent_to': to, 'subject': subject},
                metadata={'type': 'email'}
            )
        else:
            return AgentResult(
                success=False,
                error=result.error if result else "Failed to send email"
            )
    
    def _send_webhook_notification(self, task: Dict[str, Any]) -> AgentResult:
        """Send a webhook notification"""
        url = task.get('url')
        payload = task.get('payload', {})
        
        if not url:
            return AgentResult(success=False, error="Webhook URL not specified")
        
        logger.info(f"Sending webhook to {url}")
        
        result = self.execute_tool('webhook_notifier', url=url, payload=payload)
        
        if result and result.success:
            return AgentResult(
                success=True,
                data={'url': url, 'status': 'sent'},
                metadata={'type': 'webhook'}
            )
        else:
            return AgentResult(
                success=False,
                error=result.error if result else "Webhook failed"
            )
    
    def _generate_report(self, task: Dict[str, Any]) -> AgentResult:
        """Generate a valuation report"""
        ticker = task.get('ticker')
        analysis_data = task.get('analysis_data', {})
        report_format = task.get('format', 'html')
        
        if not ticker:
            return AgentResult(success=False, error="Ticker not specified")
        
        logger.info(f"Generating {report_format} report for {ticker}")
        
        # Get the appropriate generator
        if report_format == 'pdf':
            tool_name = 'generate_pdf_report'
        else:
            tool_name = 'generate_html_report'
        
        result = self.execute_tool(
            tool_name,
            ticker=ticker,
            analysis_data=analysis_data
        )
        
        if result and result.success:
            return AgentResult(
                success=True,
                data=result.data,
                metadata={
                    'ticker': ticker,
                    'format': report_format
                }
            )
        else:
            return AgentResult(
                success=False,
                error=result.error if result else "Report generation failed"
            )
    
    def _send_approval_notification(self, task: Dict[str, Any]) -> AgentResult:
        """Send approval request notification"""
        approval_request = task.get('approval_request')
        
        if not approval_request:
            return AgentResult(success=False, error="Approval request not provided")
        
        logger.info(f"Sending approval notification for request {approval_request.get('id')}")
        
        result = self.execute_tool(
            'send_approval_notification',
            approval_request=approval_request
        )
        
        if result and result.success:
            return AgentResult(
                success=True,
                data={'notification_sent': True},
                metadata={'request_id': approval_request.get('id')}
            )
        else:
            return AgentResult(
                success=False,
                error=result.error if result else "Failed to send approval notification"
            )
    
    def _send_approval_request(self, task: Dict[str, Any]) -> AgentResult:
        """
        Send approval request to approvers
        
        This is the main entry point for approval workflow notifications
        """
        from backend.workflow.approval_nodes import get_approval_manager
        
        approval_request = task.get('approval_request')
        
        if not approval_request:
            return AgentResult(success=False, error="Approval request not provided")
        
        logger.info(f"Processing approval request {approval_request.id}")
        
        # Create notification content
        notification_content = self._format_approval_notification(approval_request)
        
        # Send to configured approvers
        approvers = task.get('approvers', [])
        
        if not approvers:
            # Default: use email
            result = self._send_email({
                'to': task.get('email', 'admin@example.com'),
                'subject': f"Approval Required: {approval_request.description}",
                'body': notification_content
            })
        else:
            # Send to all approvers
            results = []
            for approver in approvers:
                r = self._send_email({
                    'to': approver.get('email'),
                    'subject': f"Approval Required: {approval_request.description}",
                    'body': notification_content
                })
                results.append(r)
            
            # Check if any succeeded
            success_count = sum(1 for r in results if r.success)
            result = AgentResult(
                success=success_count > 0,
                data={
                    'total_approvers': len(approvers),
                    'notifications_sent': success_count
                }
            )
        
        return result
    
    def _format_approval_notification(self, request) -> str:
        """Format approval request as notification body"""
        risk_level = request.risk_level.value if hasattr(request, 'risk_level') else 'unknown'
        status = request.status.value if hasattr(request, 'status') else 'pending'
        
        body = f"""
DCF Valuation Agent - Approval Required

Request ID: {request.id}
Type: {request.request_type}
Description: {request.description}

Risk Level: {risk_level.upper()}
Status: {status}

Details:
- Ticker: {request.details.get('ticker', 'N/A')}
- Action: {request.details.get('analysis_result', {}).get('action', 'N/A')}
- Upside: {request.details.get('analysis_result', {}).get('upside_percent', 0):.1f}%
- Confidence: {request.details.get('analysis_result', {}).get('confidence', 'N/A')}

Please review and approve/reject this request.

---
This is an automated message from DCF Valuation Agent
Generated at: {datetime.now().isoformat()}
"""
        return body.strip()
    
    def send_valuation_report(
        self,
        ticker: str,
        recipients: List[str],
        analysis_result: Dict[str, Any],
        report_format: str = 'html'
    ) -> AgentResult:
        """
        Convenience method to send a complete valuation report
        
        Args:
            ticker: Stock ticker
            recipients: List of email addresses
            analysis_result: Complete analysis data
            report_format: Report format (html or pdf)
        """
        logger.info(f"Sending valuation report for {ticker}")
        
        # Generate report
        report_result = self._generate_report({
            'ticker': ticker,
            'analysis_data': analysis_result,
            'format': report_format
        })
        
        if not report_result.success:
            return report_result
        
        # Send email to all recipients
        results = []
        for recipient in recipients:
            email_result = self._send_email({
                'to': recipient,
                'subject': f"Valuation Report: {ticker}",
                'body': self._format_valuation_email(analysis_result),
                'attachments': [report_result.data.get('report_path')] if report_result.data.get('report_path') else None
            })
            results.append(email_result)
        
        success_count = sum(1 for r in results if r.success)
        
        return AgentResult(
            success=success_count > 0,
            data={
                'ticker': ticker,
                'recipients_count': len(recipients),
                'sent_count': success_count,
                'report_path': report_result.data.get('report_path') if report_result.success else None
            },
            metadata={'report_format': report_format}
        )
    
    def _format_valuation_email(self, analysis_result: Dict) -> str:
        """Format valuation result as email body"""
        ticker = analysis_result.get('ticker', 'UNKNOWN')
        action = analysis_result.get('action', 'HOLD')
        upside = analysis_result.get('upside_percent', 0)
        confidence = analysis_result.get('confidence', 'Unknown')
        fair_value = analysis_result.get('fair_value', 0)
        current_price = analysis_result.get('current_price', 0)
        
        body = f"""
Valuation Analysis Complete

Stock: {ticker}
Current Price: ${current_price:.2f}
Fair Value: ${fair_value:.2f}
Upside: {upside:.1f}%

Recommendation: {action}
Confidence: {confidence}

Valuation Methods Used:
"""
        
        methods = analysis_result.get('methods_used', [])
        for method in methods:
            body += f"  - {method}\n"
        
        if analysis_result.get('reasoning'):
            body += f"""
Analysis:
{analysis_result.get('reasoning')}
"""
        
        if analysis_result.get('warnings'):
            body += f"""
Warnings:
"""
            for warning in analysis_result.get('warnings', []):
                body += f"  - {warning}\n"
        
        body += f"""
---
Generated by DCF Valuation Agent
{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        
        return body.strip()
    
    def send_alert(
        self,
        alert_type: str,
        message: str,
        recipients: List[str],
        severity: str = 'info'
    ) -> AgentResult:
        """
        Send an alert notification
        
        Args:
            alert_type: Type of alert (error, warning, info)
            message: Alert message
            recipients: List of email addresses
            severity: Severity level (low, medium, high, critical)
        """
        logger.info(f"Sending {severity} alert: {alert_type}")
        
        results = []
        for recipient in recipients:
            result = self._send_email({
                'to': recipient,
                'subject': f"[{severity.upper()}] DCF Agent Alert: {alert_type}",
                'body': f"""
DCF Valuation Agent Alert

Type: {alert_type}
Severity: {severity.upper()}

Message:
{message}

---
Time: {datetime.now().isoformat()}
"""
            })
            results.append(result)
        
        success_count = sum(1 for r in results if r.success)
        
        return AgentResult(
            success=success_count > 0,
            data={
                'alert_type': alert_type,
                'severity': severity,
                'sent_count': success_count
            }
        )
