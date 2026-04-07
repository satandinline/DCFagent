"""
Data Fetcher Tools for DCF Valuation Agent
Tools for fetching financial data from various sources
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
import logging
import time
import asyncio

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from backend.tools.base import (
    BaseTool, ToolCategory, ToolResult, FileType,
    ToolParameter, ToolCapability
)

logger = logging.getLogger(__name__)


# =============================================================================
# Yahoo Finance Data Fetcher Tool
# =============================================================================

class YahooFinanceFetcherTool(BaseTool):
    """
    Tool for fetching financial data from Yahoo Finance
    Free, no API key required
    """
    
    @property
    def name(self) -> str:
        return "yahoo_finance_fetcher"
    
    @property
    def description(self) -> str:
        return "从Yahoo Finance获取股票数据，包括股价、财务报表、市盈率、现金流等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DATA_FETCHER
    
    @property
    def capabilities(self) -> List[str]:
        return [
            ToolCapability.FETCH_STOCK_DATA,
            ToolCapability.FETCH_FINANCIAL_STATEMENTS,
            ToolCapability.FETCH_PRICE_HISTORY
        ]
    
    def __init__(self):
        super().__init__()
        self._parameters = [
            ToolParameter(
                name="ticker",
                type="string",
                description="股票代码，如AAPL、MSFT",
                required=True
            ),
            ToolParameter(
                name="data_type",
                type="string",
                description="数据类型：info（基本信息）、financials（财务报表）、history（历史股价）",
                required=False,
                default="info"
            ),
            ToolParameter(
                name="period",
                type="string",
                description="历史数据周期：1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max",
                required=False,
                default="1y"
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        ticker = kwargs.get('ticker', '').upper()
        data_type = kwargs.get('data_type', 'info')
        period = kwargs.get('period', '1y')
        
        if not ticker:
            return ToolResult(
                success=False,
                error="Ticker is required",
                tool_name=self.name
            )
        
        try:
            import yfinance as yf
            
            stock = yf.Ticker(ticker)
            
            if data_type == 'info':
                data = self._get_company_info(stock, ticker)
            elif data_type == 'financials':
                data = self._get_financials(stock, ticker)
            elif data_type == 'history':
                data = self._get_price_history(stock, ticker, period)
            else:
                data = self._get_company_info(stock, ticker)
            
            execution_time = time.time() - start_time
            self._track_execution(execution_time)
            
            return ToolResult(
                success=True,
                data=data,
                metadata={
                    'ticker': ticker,
                    'data_type': data_type,
                    'period': period
                },
                execution_time=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            logger.error(f"Yahoo Finance fetch error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )
    
    def _get_company_info(self, stock, ticker: str) -> Dict[str, Any]:
        """Get company basic info"""
        info = stock.info
        
        if not info or 'longName' not in info:
            return {'error': f'No data found for ticker: {ticker}'}
        
        return {
            'company_name': info.get('longName', ''),
            'ticker': ticker,
            'sector': info.get('sector', ''),
            'industry': info.get('industry', ''),
            'market_cap': info.get('marketCap', 0),
            'current_price': info.get('currentPrice', info.get('regularMarketPreviousClose', 0)),
            '52_week_high': info.get('fiftyTwoWeekHigh', 0),
            '52_week_low': info.get('fiftyTwoWeekLow', 0),
            'revenue': info.get('totalRevenue', 0),
            'gross_profit': info.get('grossProfits', 0),
            'operating_income': info.get('operatingIncome', 0),
            'net_income': info.get('netIncomeToCommon', 0),
            'profit_margin': info.get('profitMargins', 0),
            'operating_margin': info.get('operatingMargins', 0),
            'gross_margin': info.get('grossMargins', 0),
            'revenue_growth': info.get('revenueGrowth', 0),
            'earnings_growth': info.get('earningsGrowth', 0),
            'total_debt': info.get('totalDebt', 0),
            'total_cash': info.get('totalCash', 0),
            'shares_outstanding': info.get('sharesOutstanding', 0),
            'pe_ratio': info.get('trailingPE', 0),
            'pb_ratio': info.get('priceToBook', 0),
            'ps_ratio': info.get('priceToSalesTrailing12Months', 0),
            'dividend_yield': info.get('dividendYield', 0),
            'beta': info.get('beta', 1.0),
            'ev': info.get('enterpriseValue', 0),
            'ebitda': info.get('ebitda', 0)
        }
    
    def _get_financials(self, stock, ticker: str) -> Dict[str, Any]:
        """Get financial statements"""
        result = {
            'ticker': ticker,
            'income_statement': None,
            'balance_sheet': None,
            'cash_flow': None
        }
        
        try:
            if hasattr(stock, 'financials') and stock.financials is not None:
                result['income_statement'] = stock.financials.to_dict()
        except:
            pass
        
        try:
            if hasattr(stock, 'balance_sheet') and stock.balance_sheet is not None:
                result['balance_sheet'] = stock.balance_sheet.to_dict()
        except:
            pass
        
        try:
            if hasattr(stock, 'cashflow') and stock.cashflow is not None:
                result['cash_flow'] = stock.cashflow.to_dict()
        except:
            pass
        
        return result
    
    def _get_price_history(self, stock, ticker: str, period: str) -> Dict[str, Any]:
        """Get historical price data"""
        try:
            hist = stock.history(period=period)
            
            return {
                'ticker': ticker,
                'period': period,
                'start_date': str(hist.index[0]) if len(hist) > 0 else None,
                'end_date': str(hist.index[-1]) if len(hist) > 0 else None,
                'data_points': len(hist),
                'open': hist['Open'].tolist() if 'Open' in hist.columns else [],
                'high': hist['High'].tolist() if 'High' in hist.columns else [],
                'low': hist['Low'].tolist() if 'Low' in hist.columns else [],
                'close': hist['Close'].tolist() if 'Close' in hist.columns else [],
                'volume': hist['Volume'].tolist() if 'Volume' in hist.columns else []
            }
        except Exception as e:
            return {'error': str(e)}


# =============================================================================
# Web Search Tool
# =============================================================================

class WebSearchTool(BaseTool):
    """
    Tool for web searching using DuckDuckGo
    Free, no API key required
    """
    
    @property
    def name(self) -> str:
        return "web_search"
    
    @property
    def description(self) -> str:
        return "使用DuckDuckGo进行网络搜索，获取公司新闻、行业动态等信息"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DATA_FETCHER
    
    @property
    def capabilities(self) -> List[str]:
        return [ToolCapability.WEB_SEARCH]
    
    def __init__(self):
        super().__init__()
        self._parameters = [
            ToolParameter(
                name="query",
                type="string",
                description="搜索查询内容",
                required=True
            ),
            ToolParameter(
                name="max_results",
                type="integer",
                description="最大返回结果数",
                required=False,
                default=10
            ),
            ToolParameter(
                name="source",
                type="string",
                description="搜索引擎：duckduckgo, google",
                required=False,
                default="duckduckgo"
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        query = kwargs.get('query')
        max_results = kwargs.get('max_results', 10)
        source = kwargs.get('source', 'duckduckgo')
        
        if not query:
            return ToolResult(
                success=False,
                error="Query is required",
                tool_name=self.name
            )
        
        try:
            if source == 'duckduckgo':
                data = self._search_duckduckgo(query, max_results)
            elif source == 'google':
                data = self._search_google(query, max_results)
            else:
                data = self._search_duckduckgo(query, max_results)
            
            execution_time = time.time() - start_time
            self._track_execution(execution_time)
            
            return ToolResult(
                success=True,
                data=data,
                metadata={
                    'query': query,
                    'max_results': max_results,
                    'source': source,
                    'results_count': len(data.get('results', []))
                },
                execution_time=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            logger.error(f"Web search error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )
    
    def _search_duckduckgo(self, query: str, max_results: int) -> Dict[str, Any]:
        """Search using DuckDuckGo"""
        try:
            from ddgs import DDGS
            
            results = []
            with DDGS() as ddgs:
                for i, res in enumerate(ddgs.text(query, max_results=max_results)):
                    if i >= max_results:
                        break
                    results.append({
                        'title': res.get('title', ''),
                        'url': res.get('href', ''),
                        'snippet': res.get('body', '')[:300],
                        'source': 'duckduckgo'
                    })
            
            return {
                'query': query,
                'results': results,
                'total_results': len(results)
            }
            
        except ImportError:
            return {'error': 'DuckDuckGo library not installed. Install with: pip install ddgs'}
        except Exception as e:
            return {'error': str(e)}
    
    def _search_google(self, query: str, max_results: int) -> Dict[str, Any]:
        """Search using Google"""
        try:
            from googlesearch import search as google_search
            
            urls = list(google_search(query, num_results=max_results, lang="en"))
            
            results = []
            for url in urls:
                results.append({
                    'title': f"Result from {url}",
                    'url': url,
                    'snippet': '',
                    'source': 'google'
                })
            
            return {
                'query': query,
                'results': results,
                'total_results': len(results)
            }
            
        except ImportError:
            return {'error': 'Google search library not installed. Install with: pip install googlesearch-python'}
        except Exception as e:
            return {'error': str(e)}


# =============================================================================
# Company News Tool
# =============================================================================

class CompanyNewsTool(BaseTool):
    """
    Tool for fetching company news and recent events
    """
    
    @property
    def name(self) -> str:
        return "company_news"
    
    @property
    def description(self) -> str:
        return "获取公司最新新闻和动态，包括财务新闻、并购、业绩发布等"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DATA_FETCHER
    
    @property
    def capabilities(self) -> List[str]:
        return [ToolCapability.WEB_SEARCH]
    
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
                name="max_results",
                type="integer",
                description="最大返回新闻数",
                required=False,
                default=10
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        ticker = kwargs.get('ticker', '').upper()
        max_results = kwargs.get('max_results', 10)
        
        try:
            import yfinance as yf
            
            stock = yf.Ticker(ticker)
            news = stock.news
            
            if not news:
                return ToolResult(
                    success=True,
                    data={'ticker': ticker, 'news': []},
                    metadata={'ticker': ticker, 'news_count': 0},
                    execution_time=time.time() - start_time,
                    tool_name=self.name
                )
            
            formatted_news = []
            for item in news[:max_results]:
                formatted_news.append({
                    'title': item.get('title', ''),
                    'publisher': item.get('publisher', ''),
                    'link': item.get('link', ''),
                    'published': item.get('publishedDate', ''),
                    'summary': item.get('summary', '')[:300]
                })
            
            execution_time = time.time() - start_time
            self._track_execution(execution_time)
            
            return ToolResult(
                success=True,
                data={
                    'ticker': ticker,
                    'news': formatted_news
                },
                metadata={
                    'ticker': ticker,
                    'news_count': len(formatted_news)
                },
                execution_time=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            logger.error(f"Company news error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )


# =============================================================================
# Financial Ratios Tool
# =============================================================================

class FinancialRatiosTool(BaseTool):
    """
    Tool for calculating and fetching financial ratios
    """
    
    @property
    def name(self) -> str:
        return "financial_ratios"
    
    @property
    def description(self) -> str:
        return "计算财务比率，包括盈利能力、偿债能力、运营效率等指标"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.DATA_FETCHER
    
    @property
    def capabilities(self) -> List[str]:
        return [ToolCapability.FETCH_FINANCIAL_STATEMENTS]
    
    def __init__(self):
        super().__init__()
        self._parameters = [
            ToolParameter(
                name="ticker",
                type="string",
                description="股票代码",
                required=True
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        ticker = kwargs.get('ticker', '').upper()
        
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
            
            # Calculate ratios
            ratios = self._calculate_ratios(info)
            
            execution_time = time.time() - start_time
            self._track_execution(execution_time)
            
            return ToolResult(
                success=True,
                data=ratios,
                metadata={'ticker': ticker},
                execution_time=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            logger.error(f"Financial ratios error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )
    
    def _calculate_ratios(self, info: Dict) -> Dict[str, Any]:
        """Calculate financial ratios from info"""
        return {
            'ticker': info.get('symbol', ''),
            'profitability_ratios': {
                'gross_margin': info.get('grossMargins', 0),
                'operating_margin': info.get('operatingMargins', 0),
                'net_margin': info.get('profitMargins', 0),
                'roe': info.get('returnOnEquity', 0),
                'roa': info.get('returnOnAssets', 0),
                'roic': info.get('returnOnInvestedCapital', 0)
            },
            'liquidity_ratios': {
                'current_ratio': info.get('currentRatio', 0),
                'quick_ratio': info.get('quickRatio', 0)
            },
            'leverage_ratios': {
                'debt_to_equity': info.get('debtToEquity', 0),
                'debt_to_assets': info.get('totalDebt', 0) / info.get('totalAssets', 1) if info.get('totalAssets') else 0,
                'interest_coverage': info.get('interestCoverage', 0)
            },
            'valuation_ratios': {
                'pe_ratio': info.get('trailingPE', 0),
                'forward_pe': info.get('forwardPE', 0),
                'peg_ratio': info.get('pegRatio', 0),
                'ps_ratio': info.get('priceToSalesTrailing12Months', 0),
                'pb_ratio': info.get('priceToBook', 0),
                'ev_ebitda': info.get('enterpriseToEbitda', 0),
                'ev_revenue': info.get('enterpriseToRevenue', 0)
            },
            'dividend_ratios': {
                'dividend_yield': info.get('dividendYield', 0),
                'payout_ratio': info.get('payoutRatio', 0),
                'dividend_rate': info.get('dividendRate', 0)
            },
            'growth_ratios': {
                'revenue_growth': info.get('revenueGrowth', 0),
                'earnings_growth': info.get('earningsGrowth', 0),
                'book_value_growth': info.get('bookValueChange', 0)
            },
            'per_share_ratios': {
                'eps': info.get('trailingEps', 0),
                'forward_eps': info.get('forwardEps', 0),
                'book_value': info.get('bookValue', 0),
                'cash_per_share': info.get('totalCashPerShare', 0)
            }
        }


# =============================================================================
# Register data fetcher tools
# =============================================================================

def register_data_fetcher_tools():
    """Register all data fetcher tools to the global registry"""
    from backend.tools.registry import tool_registry
    
    tools = [
        YahooFinanceFetcherTool(),
        WebSearchTool(),
        CompanyNewsTool(),
        FinancialRatiosTool()
    ]
    
    for tool in tools:
        tool_registry.register(tool)
    
    return tools
