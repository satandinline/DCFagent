"""
Email Service for DCF Valuation Agent
Send analysis reports via QQ email (SMTP)
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional, List
from pathlib import Path

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.config import (
    EMAIL_HOST,
    EMAIL_PORT,
    EMAIL_USER,
    EMAIL_PASSWORD,
    EMAIL_TO
)

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending email reports via SMTP"""
    
    def __init__(
        self,
        host: str = None,
        port: int = None,
        user: str = None,
        password: str = None,
        to_email: str = None
    ):
        self.host = host or EMAIL_HOST
        self.port = port or EMAIL_PORT
        self.user = user or EMAIL_USER
        self.password = password or EMAIL_PASSWORD
        self.to_email = to_email or EMAIL_TO
        self.use_tls = True
    
    def send_email(
        self,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
        to_email: Optional[str] = None,
        attachments: Optional[List[Path]] = None
    ) -> dict:
        """
        Send an email with optional HTML content and attachments
        
        Args:
            subject: Email subject
            body: Plain text body
            html_body: Optional HTML body
            to_email: Override recipient email
            attachments: List of file paths to attach
            
        Returns:
            dict with success status and message
        """
        if not self.user or not self.password:
            return {
                'success': False,
                'error': 'Email credentials not configured'
            }
        
        recipient = to_email or self.to_email
        
        if not recipient:
            return {
                'success': False,
                'error': 'No recipient email specified'
            }
        
        try:
            # Create message
            msg = MIMEMultipart('mixed')
            msg['From'] = self.user
            msg['To'] = recipient
            msg['Subject'] = subject
            
            # Create body parts
            body_parts = []
            
            # Plain text part
            text_part = MIMEText(body, 'plain', 'utf-8')
            body_parts.append(text_part)
            
            # HTML part if provided
            if html_body:
                html_part = MIMEText(html_body, 'html', 'utf-8')
                body_parts.append(html_part)
            
            # Add body to message
            for part in body_parts:
                msg.attach(part)
            
            # Add attachments
            if attachments:
                for file_path in attachments:
                    if file_path and Path(file_path).exists():
                        with open(file_path, 'rb') as f:
                            part = MIMEBase('application', 'octet-stream')
                            part.set_payload(f.read())
                            encoders.encode_base64(part)
                            filename = os.path.basename(file_path)
                            part.add_header(
                                'Content-Disposition',
                                f'attachment; filename="{filename}"'
                            )
                            msg.attach(part)
            
            # Connect to server and send
            logger.info(f"Connecting to SMTP server {self.host}:{self.port}")
            
            server = smtplib.SMTP(self.host, self.port, timeout=30)
            server.ehlo()
            
            if self.use_tls:
                server.starttls()
                server.ehlo()
            
            server.login(self.user, self.password)
            server.sendmail(self.user, recipient, msg.as_string())
            server.quit()
            
            logger.info(f"Email sent successfully to {recipient}")
            return {
                'success': True,
                'message': f'Email sent to {recipient}'
            }
            
        except smtplib.SMTPAuthenticationError:
            logger.error("SMTP Authentication failed")
            return {
                'success': False,
                'error': 'SMTP Authentication failed. Check your email credentials.'
            }
        except smtplib.SMTPException as e:
            logger.error(f"SMTP error: {e}")
            return {
                'success': False,
                'error': f'SMTP error: {str(e)}'
            }
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def send_portfolio_report(
        self,
        portfolio_data: dict,
        to_email: Optional[str] = None
    ) -> dict:
        """
        Send a portfolio analysis report
        
        Args:
            portfolio_data: Portfolio analysis data
            to_email: Optional override for recipient
            
        Returns:
            dict with success status
        """
        subject = f"DCF Agent 投资组合分析报告 - {portfolio_data.get('report_date', '最新')}"
        
        # Plain text body
        body = self._generate_text_report(portfolio_data)
        
        # HTML body
        html = self._generate_html_report(portfolio_data)
        
        return self.send_email(
            subject=subject,
            body=body,
            html_body=html,
            to_email=to_email
        )
    
    def _generate_text_report(self, data: dict) -> str:
        """Generate plain text report"""
        lines = [
            "=" * 60,
            "DCF Agent 智能投资分析报告",
            "=" * 60,
            "",
            f"报告时间: {data.get('report_date', 'N/A')}",
            f"分析股票数: {data.get('stocks_analyzed', 0)}",
            "",
            "-" * 60,
            "投资组合建议",
            "-" * 60,
            ""
        ]
        
        recommendations = data.get('recommendations', [])
        if not recommendations:
            lines.append("暂无推荐")
        else:
            for rec in recommendations:
                lines.append(f"股票代码: {rec.get('ticker', 'N/A')}")
                lines.append(f"操作建议: {rec.get('action', 'N/A')}")
                lines.append(f"上涨空间: {rec.get('upside', 0):.2f}%")
                lines.append(f"置信度: {rec.get('confidence', 'N/A')}")
                lines.append(f"估值方法: {', '.join(rec.get('valuation_methods', []))}")
                lines.append(f"推荐理由: {rec.get('reason', 'N/A')}")
                lines.append("")
        
        lines.extend([
            "-" * 60,
            "详细信息",
            "-" * 60,
            ""
        ])
        
        details = data.get('details', [])
        for detail in details:
            lines.append(f"股票: {detail.get('ticker')}")
            lines.append(f"  当前价: ${detail.get('current_price', 0):.2f}")
            lines.append(f"  估值: ${detail.get('fair_value', 0):.2f}")
            lines.append(f"  上涨/下跌: {detail.get('upside', 0):.2f}%")
            lines.append(f"  行业: {detail.get('industry', 'N/A')}")
            lines.append("")
        
        lines.extend([
            "=" * 60,
            "本报告由 DCF Agent 自动生成",
            "=" * 60
        ])
        
        return "\n".join(lines)
    
    def _generate_html_report(self, data: dict) -> str:
        """Generate HTML report"""
        recommendations = data.get('recommendations', [])
        
        # Build recommendations HTML
        rec_html = ""
        for rec in recommendations:
            action_color = {
                'BUY': '#28a745',
                'HOLD': '#ffc107',
                'SELL': '#dc3545'
            }.get(rec.get('action', 'HOLD'), '#6c757d')
            
            rec_html += f"""
            <tr>
                <td><strong>{rec.get('ticker', 'N/A')}</strong></td>
                <td><span style="color: {action_color}; font-weight: bold;">{rec.get('action', 'N/A')}</span></td>
                <td>{rec.get('upside', 0):.2f}%</td>
                <td>{rec.get('confidence', 'N/A')}</td>
                <td>{', '.join(rec.get('valuation_methods', []))}</td>
                <td>{rec.get('reason', 'N/A')}</td>
            </tr>
            """
        
        if not rec_html:
            rec_html = "<tr><td colspan='6'>暂无推荐</td></tr>"
        
        # Build details HTML
        details = data.get('details', [])
        detail_html = ""
        for detail in details:
            upside = detail.get('upside', 0)
            upside_color = '#28a745' if upside > 0 else '#dc3545'
            
            detail_html += f"""
            <tr>
                <td>{detail.get('ticker', 'N/A')}</td>
                <td>${detail.get('current_price', 0):.2f}</td>
                <td>${detail.get('fair_value', 0):.2f}</td>
                <td style="color: {upside_color};">{upside:.2f}%</td>
                <td>{detail.get('industry', 'N/A')}</td>
            </tr>
            """
        
        if not detail_html:
            detail_html = "<tr><td colspan='5'>暂无数据</td></tr>"
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                h2 {{ color: #666; border-bottom: 2px solid #ddd; padding-bottom: 5px; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
                th {{ background-color: #f8f9fa; font-weight: bold; }}
                .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
                .summary {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0; }}
                .footer {{ text-align: center; color: #666; margin-top: 30px; font-size: 12px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>DCF Agent 智能投资分析报告</h1>
                <p>报告时间: {data.get('report_date', 'N/A')}</p>
            </div>
            
            <div class="summary">
                <strong>分析概览:</strong><br>
                分析股票数: {data.get('stocks_analyzed', 0)}<br>
                推荐买入: {sum(1 for r in recommendations if r.get('action') == 'BUY')}<br>
                推荐持有: {sum(1 for r in recommendations if r.get('action') == 'HOLD')}<br>
                推荐卖出: {sum(1 for r in recommendations if r.get('action') == 'SELL')}
            </div>
            
            <h2>投资组合建议</h2>
            <table>
                <thead>
                    <tr>
                        <th>股票代码</th>
                        <th>操作建议</th>
                        <th>上涨空间</th>
                        <th>置信度</th>
                        <th>估值方法</th>
                        <th>推荐理由</th>
                    </tr>
                </thead>
                <tbody>
                    {rec_html}
                </tbody>
            </table>
            
            <h2>详细分析</h2>
            <table>
                <thead>
                    <tr>
                        <th>股票</th>
                        <th>当前价</th>
                        <th>公允价值</th>
                        <th>上涨/下跌</th>
                        <th>行业</th>
                    </tr>
                </thead>
                <tbody>
                    {detail_html}
                </tbody>
            </table>
            
            <div class="footer">
                <p>本报告由 DCF Agent 自动生成</p>
                <p>免责声明: 本报告仅供参考，不构成投资建议</p>
            </div>
        </body>
        </html>
        """
        
        return html


# Singleton instance
email_service = EmailService()
