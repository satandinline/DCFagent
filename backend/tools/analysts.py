"""
Analyst Tools for DCF Valuation Agent
Tools for financial analysis, valuation, and industry classification
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
import logging
import time
import json

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from backend.tools.base import (
    BaseTool, ToolCategory, ToolResult,
    ToolParameter, ToolCapability
)
from backend.models.schemas import FinancialData, DCFParameters

logger = logging.getLogger(__name__)


# =============================================================================
# DCF Valuation Tool
# =============================================================================

class DCFValuationTool(BaseTool):
    """
    Tool for performing Discounted Cash Flow (DCF) valuation
    """
    
    @property
    def name(self) -> str:
        return "dcf_valuation"
    
    @property
    def description(self) -> str:
        return "执行DCF（现金流折现）估值分析，计算企业内在价值"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.ANALYST
    
    @property
    def capabilities(self) -> List[str]:
        return [ToolCapability.DCF_VALUATION]
    
    def __init__(self):
        super().__init__()
        self._parameters = [
            ToolParameter(
                name="revenue",
                type="float",
                description="当前年收入（单位：元）",
                required=True
            ),
            ToolParameter(
                name="revenue_growth_rate",
                type="float",
                description="收入增长率（如0.1表示10%）",
                required=False,
                default=0.08
            ),
            ToolParameter(
                name="operating_margin",
                type="float",
                description="营业利润率（如0.15表示15%）",
                required=False,
                default=0.15
            ),
            ToolParameter(
                name="wacc",
                type="float",
                description="加权平均资本成本（如0.1表示10%）",
                required=False,
                default=0.1
            ),
            ToolParameter(
                name="terminal_growth_rate",
                type="float",
                description="永续增长率（如0.025表示2.5%）",
                required=False,
                default=0.025
            ),
            ToolParameter(
                name="projection_years",
                type="integer",
                description="预测年数",
                required=False,
                default=5
            ),
            ToolParameter(
                name="shares_outstanding",
                type="float",
                description="流通股数",
                required=False,
                default=1.0
            ),
            ToolParameter(
                name="total_debt",
                type="float",
                description="总债务",
                required=False,
                default=0.0
            ),
            ToolParameter(
                name="cash",
                type="float",
                description="现金及现金等价物",
                required=False,
                default=0.0
            ),
            ToolParameter(
                name="ticker",
                type="string",
                description="股票代码",
                required=False,
                default=""
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        try:
            from backend.services.dcf_service import run_dcf, sensitivity_analysis
            
            # Build FinancialData
            financial_data = FinancialData(
                ticker=kwargs.get('ticker', ''),
                revenue=kwargs.get('revenue', 0),
                revenue_growth=kwargs.get('revenue_growth_rate', 0.08),
                operating_margin=kwargs.get('operating_margin', 0.15),
                shares_outstanding=kwargs.get('shares_outstanding', 1.0),
                total_debt=kwargs.get('total_debt', 0),
                cash_and_equivalents=kwargs.get('cash', 0)
            )
            
            # Build DCFParameters
            params = DCFParameters(
                projection_years=kwargs.get('projection_years', 5),
                revenue_growth_rate=kwargs.get('revenue_growth_rate', 0.08),
                terminal_growth_rate=kwargs.get('terminal_growth_rate', 0.025),
                operating_margin=kwargs.get('operating_margin', 0.15),
                wacc=kwargs.get('wacc', 0.1)
            )
            
            # Run DCF
            dcf_result = run_dcf(financial_data, params)
            
            # Run sensitivity analysis
            sensitivity = sensitivity_analysis(financial_data, params)
            
            execution_time = time.time() - start_time
            self._track_execution(execution_time)
            
            return ToolResult(
                success=True,
                data={
                    'per_share_value': dcf_result.per_share_value,
                    'enterprise_value': dcf_result.enterprise_value,
                    'equity_value': dcf_result.equity_value,
                    'wacc': dcf_result.wacc_used,
                    'terminal_growth': dcf_result.terminal_growth_used,
                    'upside': dcf_result.upside_downside,
                    'projections': [
                        {
                            'year': p.year,
                            'revenue': p.revenue,
                            'operating_income': p.operating_income,
                            'free_cash_flow': p.free_cash_flow,
                            'present_value': p.present_value
                        }
                        for p in dcf_result.projections
                    ],
                    'sensitivity': {
                        'wacc_range': sensitivity.wacc_range,
                        'growth_range': sensitivity.growth_range,
                        'values': sensitivity.values
                    }
                },
                metadata={
                    'ticker': kwargs.get('ticker', ''),
                    'wacc': params.wacc,
                    'projection_years': params.projection_years
                },
                execution_time=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            logger.error(f"DCF valuation error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )


# =============================================================================
# Industry Classification Tool
# =============================================================================

class IndustryClassificationTool(BaseTool):
    """
    Tool for classifying company industry and selecting valuation methods
    """
    
    @property
    def name(self) -> str:
        return "industry_classification"
    
    @property
    def description(self) -> str:
        return "根据公司信息自动识别行业类型并推荐合适的估值方法"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.ANALYST
    
    @property
    def capabilities(self) -> List[str]:
        return [ToolCapability.INDUSTRY_CLASSIFICATION]
    
    def __init__(self):
        super().__init__()
        self._parameters = [
            ToolParameter(
                name="sector",
                type="string",
                description="行业板块（如Technology、Financial Services）",
                required=False,
                default=""
            ),
            ToolParameter(
                name="industry",
                type="string",
                description="具体行业（如Software、Banking）",
                required=False,
                default=""
            ),
            ToolParameter(
                name="company_name",
                type="string",
                description="公司名称",
                required=False,
                default=""
            ),
            ToolParameter(
                name="is_profitable",
                type="boolean",
                description="公司是否盈利",
                required=False,
                default=True
            ),
            ToolParameter(
                name="has_dividends",
                type="boolean",
                description="公司是否支付股息",
                required=False,
                default=False
            ),
            ToolParameter(
                name="revenue_growth",
                type="float",
                description="收入增长率",
                required=False,
                default=0.0
            ),
            ToolParameter(
                name="net_income",
                type="float",
                description="净利润（可负数表示亏损）",
                required=False,
                default=0.0
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        try:
            from backend.services.industry_classifier import industry_classifier
            
            industry_type, recommendation = industry_classifier.classify(
                sector=kwargs.get('sector'),
                industry=kwargs.get('industry'),
                company_name=kwargs.get('company_name'),
                is_profitable=kwargs.get('is_profitable', True),
                has_dividends=kwargs.get('has_dividends', False),
                revenue_growth=kwargs.get('revenue_growth', 0),
                net_income=kwargs.get('net_income', 0)
            )
            
            execution_time = time.time() - start_time
            self._track_execution(execution_time)
            
            return ToolResult(
                success=True,
                data={
                    'industry_type': industry_type.value,
                    'industry_type_name': industry_type.name,
                    'primary_method': recommendation.primary_method,
                    'secondary_methods': recommendation.secondary_methods,
                    'confidence': recommendation.confidence,
                    'reasoning': recommendation.reasoning
                },
                metadata={
                    'sector': kwargs.get('sector', ''),
                    'industry': kwargs.get('industry', ''),
                    'is_profitable': kwargs.get('is_profitable', True)
                },
                execution_time=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            logger.error(f"Industry classification error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )


# =============================================================================
# Comparable Company Analysis Tool
# =============================================================================

class ComparableCompanyAnalysisTool(BaseTool):
    """
    Tool for performing comparable company analysis (relative valuation)
    """
    
    @property
    def name(self) -> str:
        return "comparable_analysis"
    
    @property
    def description(self) -> str:
        return "使用可比公司法进行相对估值，分析同行业公司的估值指标"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.ANALYST
    
    @property
    def capabilities(self) -> List[str]:
        return [ToolCapability.DCF_VALUATION]
    
    def __init__(self):
        super().__init__()
        self._parameters = [
            ToolParameter(
                name="ticker",
                type="string",
                description="要分析的公司股票代码",
                required=True
            ),
            ToolParameter(
                name="method",
                type="string",
                description="估值方法：pe、pb、ps、ev_ebitda",
                required=False,
                default="pe"
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        ticker = kwargs.get('ticker', '').upper()
        method = kwargs.get('method', 'pe')
        
        try:
            import yfinance as yf
            
            stock = yf.Ticker(ticker)
            info = stock.info
            
            if not info:
                return ToolResult(
                    success=False,
                    error=f"No data found for {ticker}",
                    tool_name=self.name
                )
            
            # Get sector peers
            sector = info.get('sector', '')
            industry = info.get('industry', '')
            
            # Calculate valuation based on method
            if method == 'pe':
                target_ratio = info.get('trailingPE', 0)
                peer_avg_pe = self._estimate_peer_pe(sector, method)
                value = self._calculate_value_from_multiple(info, 'trailingPE', target_ratio)
            elif method == 'pb':
                target_ratio = info.get('priceToBook', 0)
                value = self._calculate_value_from_multiple(info, 'priceToBook', target_ratio)
            elif method == 'ps':
                target_ratio = info.get('priceToSalesTrailing12Months', 0)
                value = self._calculate_value_from_multiple(info, 'priceToSalesTrailing12Months', target_ratio)
            elif method == 'ev_ebitda':
                target_ratio = info.get('enterpriseToEbitda', 0)
                value = self._calculate_value_from_multiple(info, 'enterpriseToEbitda', target_ratio)
            else:
                target_ratio = info.get('trailingPE', 0)
                value = 0
            
            current_price = info.get('currentPrice', info.get('regularMarketPreviousClose', 0))
            
            execution_time = time.time() - start_time
            self._track_execution(execution_time)
            
            return ToolResult(
                success=True,
                data={
                    'ticker': ticker,
                    'company_name': info.get('longName', ''),
                    'sector': sector,
                    'industry': industry,
                    'method': method,
                    'current_price': current_price,
                    'target_multiple': target_ratio,
                    'estimated_fair_value': value,
                    'upside_percent': ((value - current_price) / current_price * 100) if current_price > 0 else 0
                },
                metadata={
                    'ticker': ticker,
                    'method': method
                },
                execution_time=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            logger.error(f"Comparable analysis error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )
    
    def _estimate_peer_pe(self, sector: str, method: str) -> float:
        """Estimate peer average multiple"""
        # Simplified - in production would fetch peer data
        sector_pe = {
            'Technology': 30,
            'Financial Services': 12,
            'Healthcare': 20,
            'Consumer Cyclical': 15,
            'Energy': 10,
            'Basic Materials': 12,
            'Industrials': 18,
            'Consumer Defensive': 22,
            'Utilities': 16,
            'Real Estate': 14
        }
        return sector_pe.get(sector, 15)
    
    def _calculate_value_from_multiple(self, info: Dict, ratio_key: str, target_multiple: float) -> float:
        """Calculate per-share value from multiple"""
        if ratio_key == 'trailingPE':
            eps = info.get('trailingEps', 0)
            return eps * target_multiple if eps else 0
        elif ratio_key == 'priceToBook':
            bvps = info.get('bookValue', 0)
            return bvps * target_multiple if bvps else 0
        elif ratio_key == 'priceToSalesTrailing12Months':
            ps = info.get('priceToSalesTrailing12Months', 0)
            return ps if ps else 0
        elif ratio_key == 'enterpriseToEbitda':
            return target_multiple if target_multiple else 0
        return 0


# =============================================================================
# Trend Analysis Tool
# =============================================================================

class TrendAnalysisTool(BaseTool):
    """
    Tool for analyzing financial trends over time
    """
    
    @property
    def name(self) -> str:
        return "trend_analysis"
    
    @property
    def description(self) -> str:
        return "分析财务数据趋势，包括收入增长、利润率变化、CAGR计算等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.ANALYST
    
    @property
    def capabilities(self) -> List[str]:
        return [ToolCapability.TREND_ANALYSIS]
    
    def __init__(self):
        super().__init__()
        self._parameters = [
            ToolParameter(
                name="ticker",
                type="string",
                description="股票代码",
                required=True
            ),
            ToolParameter(
                name="metric",
                type="string",
                description="分析指标：revenue、net_income、operating_income、cashflow",
                required=False,
                default="revenue"
            ),
            ToolParameter(
                name="periods",
                type="integer",
                description="分析周期数（年报数量）",
                required=False,
                default=5
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        ticker = kwargs.get('ticker', '').upper()
        metric = kwargs.get('metric', 'revenue')
        periods = kwargs.get('periods', 5)
        
        try:
            from backend.services.dcf_service import get_trend_analysis
            
            trends = get_trend_analysis(ticker)
            
            execution_time = time.time() - start_time
            self._track_execution(execution_time)
            
            return ToolResult(
                success=True,
                data=trends,
                metadata={
                    'ticker': ticker,
                    'metric': metric,
                    'periods': periods
                },
                execution_time=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            logger.error(f"Trend analysis error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )


# =============================================================================
# Sensitivity Analysis Tool
# =============================================================================

class SensitivityAnalysisTool(BaseTool):
    """
    Tool for performing sensitivity analysis on valuation
    """
    
    @property
    def name(self) -> str:
        return "sensitivity_analysis"
    
    @property
    def description(self) -> str:
        return "执行敏感性分析，分析WACC和永续增长率变化对估值的影响"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.ANALYST
    
    @property
    def capabilities(self) -> List[str]:
        return [ToolCapability.SENSITIVITY_ANALYSIS]
    
    def __init__(self):
        super().__init__()
        self._parameters = [
            ToolParameter(
                name="revenue",
                type="float",
                description="当前年收入",
                required=True
            ),
            ToolParameter(
                name="wacc_base",
                type="float",
                description="基础WACC（如0.1表示10%）",
                required=False,
                default=0.1
            ),
            ToolParameter(
                name="terminal_growth_base",
                type="float",
                description="基础永续增长率（如0.025表示2.5%）",
                required=False,
                default=0.025
            ),
            ToolParameter(
                name="wacc_range",
                type="array",
                description="WACC范围，如[0.08, 0.1, 0.12]",
                required=False,
                default=[0.08, 0.09, 0.1, 0.11, 0.12]
            ),
            ToolParameter(
                name="growth_range",
                type="array",
                description="永续增长率范围",
                required=False,
                default=[0.02, 0.025, 0.03]
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        try:
            from backend.services.dcf_service import sensitivity_analysis
            from backend.models.schemas import FinancialData, DCFParameters
            
            financial_data = FinancialData(
                revenue=kwargs.get('revenue', 0),
                operating_margin=0.15,
                shares_outstanding=1.0
            )
            
            params = DCFParameters(
                wacc=kwargs.get('wacc_base', 0.1),
                terminal_growth_rate=kwargs.get('terminal_growth_base', 0.025)
            )
            
            result = sensitivity_analysis(financial_data, params)
            
            execution_time = time.time() - start_time
            self._track_execution(execution_time)
            
            return ToolResult(
                success=True,
                data={
                    'wacc_range': result.wacc_range,
                    'growth_range': result.growth_range,
                    'sensitivity_matrix': result.values,
                    'base_wacc': kwargs.get('wacc_base', 0.1),
                    'base_growth': kwargs.get('terminal_growth_base', 0.025)
                },
                execution_time=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            logger.error(f"Sensitivity analysis error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )


# =============================================================================
# Register analyst tools
# =============================================================================

def register_analyst_tools():
    """Register all analyst tools to the global registry"""
    from backend.tools.registry import tool_registry
    
    tools = [
        DCFValuationTool(),
        IndustryClassificationTool(),
        ComparableCompanyAnalysisTool(),
        TrendAnalysisTool(),
        SensitivityAnalysisTool()
    ]
    
    for tool in tools:
        tool_registry.register(tool)
    
    return tools
