"""
Communicator Tools for DCF Valuation Agent
Tools for sending emails, notifications, and reports
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
import logging
import time
from pathlib import Path

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from backend.tools.base import (
    BaseTool, ToolCategory, ToolResult,
    ToolParameter, ToolCapability
)

logger = logging.getLogger(__name__)


# =============================================================================
# Email Tool
# =============================================================================

class EmailTool(BaseTool):
    """
    Tool for sending emails via SMTP
    Supports QQ email and other SMTP servers
    """
    
    @property
    def name(self) -> str:
        return "send_email"
    
    @property
    def description(self) -> str:
        return "通过SMTP发送电子邮件，支持附件和HTML格式"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.COMMUNICATOR
    
    @property
    def capabilities(self) -> List[str]:
        return [ToolCapability.SEND_EMAIL]
    
    def __init__(self):
        super().__init__()
        self._parameters = [
            ToolParameter(
                name="to_email",
                type="string",
                description="收件人邮箱地址",
                required=True
            ),
            ToolParameter(
                name="subject",
                type="string",
                description="邮件主题",
                required=True
            ),
            ToolParameter(
                name="body",
                type="string",
                description="邮件正文（纯文本）",
                required=True
            ),
            ToolParameter(
                name="html_body",
                type="string",
                description="HTML格式的邮件正文（可选）",
                required=False,
                default=None
            ),
            ToolParameter(
                name="attachments",
                type="array",
                description="附件文件路径列表",
                required=False,
                default=None
            ),
            ToolParameter(
                name="from_email",
                type="string",
                description="发件人邮箱（默认使用配置的邮箱）",
                required=False,
                default=None
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        to_email = kwargs.get('to_email')
        subject = kwargs.get('subject')
        body = kwargs.get('body')
        html_body = kwargs.get('html_body')
        attachments = kwargs.get('attachments')
        from_email = kwargs.get('from_email')
        
        if not to_email or not subject or not body:
            return ToolResult(
                success=False,
                error="Missing required parameters: to_email, subject, body",
                tool_name=self.name
            )
        
        try:
            from backend.services.email_service import email_service
            
            result = email_service.send_email(
                subject=subject,
                body=body,
                html_body=html_body,
                to_email=to_email,
                attachments=[Path(a) for a in attachments] if attachments else None
            )
            
            execution_time = time.time() - start_time
            self._track_execution(execution_time)
            
            return ToolResult(
                success=result.get('success', False),
                data=result,
                error=result.get('error'),
                metadata={
                    'to_email': to_email,
                    'subject': subject,
                    'has_attachment': attachments is not None
                },
                execution_time=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            logger.error(f"Email error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )


# =============================================================================
# Portfolio Report Email Tool
# =============================================================================

class PortfolioReportEmailTool(BaseTool):
    """
    Tool for sending formatted portfolio analysis reports via email
    """
    
    @property
    def name(self) -> str:
        return "send_portfolio_report"
    
    @property
    def description(self) -> str:
        return "发送格式化投资组合分析报告邮件，包含推荐和建议"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.COMMUNICATOR
    
    @property
    def capabilities(self) -> List[str]:
        return [ToolCapability.SEND_EMAIL, ToolCapability.SEND_NOTIFICATION]
    
    def __init__(self):
        super().__init__()
        self._parameters = [
            ToolParameter(
                name="to_email",
                type="string",
                description="收件人邮箱",
                required=False,
                default=None
            ),
            ToolParameter(
                name="report_data",
                type="object",
                description="报告数据，包含recommendations、summary等",
                required=True
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        to_email = kwargs.get('to_email')
        report_data = kwargs.get('report_data')
        
        if not report_data:
            return ToolResult(
                success=False,
                error="report_data is required",
                tool_name=self.name
            )
        
        try:
            from backend.services.email_service import email_service
            
            result = email_service.send_portfolio_report(
                portfolio_data=report_data,
                to_email=to_email
            )
            
            execution_time = time.time() - start_time
            self._track_execution(execution_time)
            
            return ToolResult(
                success=result.get('success', False),
                data=result,
                error=result.get('error'),
                metadata={
                    'to_email': to_email,
                    'stocks_count': len(report_data.get('recommendations', []))
                },
                execution_time=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            logger.error(f"Portfolio report email error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )


# =============================================================================
# Notification Tool
# =============================================================================

class NotificationTool(BaseTool):
    """
    Tool for sending notifications (logging-based for now)
    Can be extended to support SMS, Slack, etc.
    """
    
    @property
    def name(self) -> str:
        return "send_notification"
    
    @property
    def description(self) -> str:
        return "发送系统通知，可用于提醒分析完成、异常警报等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.COMMUNICATOR
    
    @property
    def capabilities(self) -> List[str]:
        return [ToolCapability.SEND_NOTIFICATION]
    
    def __init__(self):
        super().__init__()
        self._parameters = [
            ToolParameter(
                name="title",
                type="string",
                description="通知标题",
                required=True
            ),
            ToolParameter(
                name="message",
                type="string",
                description="通知内容",
                required=True
            ),
            ToolParameter(
                name="level",
                type="string",
                description="通知级别：info、warning、error、success",
                required=False,
                default="info"
            ),
            ToolParameter(
                name="channel",
                type="string",
                description="通知渠道：log、email、sms、slack",
                required=False,
                default="log"
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        title = kwargs.get('title')
        message = kwargs.get('message')
        level = kwargs.get('level', 'info')
        channel = kwargs.get('channel', 'log')
        
        if not title or not message:
            return ToolResult(
                success=False,
                error="title and message are required",
                tool_name=self.name
            )
        
        try:
            notification = f"[{level.upper()}] {title}: {message}"
            
            if channel == 'log':
                if level == 'error':
                    logger.error(notification)
                elif level == 'warning':
                    logger.warning(notification)
                elif level == 'success':
                    logger.info(f"SUCCESS: {notification}")
                else:
                    logger.info(notification)
            
            execution_time = time.time() - start_time
            self._track_execution(execution_time)
            
            return ToolResult(
                success=True,
                data={
                    'notification': notification,
                    'channel': channel,
                    'level': level
                },
                metadata={
                    'title': title
                },
                execution_time=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            logger.error(f"Notification error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )


# =============================================================================
# Register communicator tools
# =============================================================================

def register_communicator_tools():
    """Register all communicator tools to the global registry"""
    from backend.tools.registry import tool_registry
    
    tools = [
        EmailTool(),
        PortfolioReportEmailTool(),
        NotificationTool()
    ]
    
    for tool in tools:
        tool_registry.register(tool)
    
    return tools
