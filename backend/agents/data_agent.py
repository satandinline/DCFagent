"""
Data Agent for DCF Valuation System

Specialized agent for data acquisition and preprocessing
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
import logging
import json

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from backend.agents.base_agent import BaseAgent, AgentResult, AgentCapability
from backend.tools.registry import tool_registry

logger = logging.getLogger(__name__)


class DataAgent(BaseAgent):
    """
    Data Agent - Specialized for fetching and preprocessing financial data
    
    Capabilities:
    - Fetch stock data from Yahoo Finance
    - Search for company information
    - Parse financial documents (PDF, Excel, etc.)
    - Get company news and sentiment
    - Calculate financial ratios
    
    Tools used:
    - yahoo_finance_fetcher
    - web_search
    - company_news_fetcher
    - financial_ratios_calculator
    - pdf_parser, excel_parser, etc.
    """
    
    name = "data_agent"
    role = "Data Acquisition Specialist"
    description = "Fetches and preprocesses financial data for valuation"
    
    def _initialize_capabilities(self):
        """Initialize Data Agent capabilities"""
        self._capabilities = {
            AgentCapability.DATA_FETCH,
            AgentCapability.DATA_PARSE,
        }
    
    def _initialize_tools(self):
        """Initialize Data Agent tools"""
        self._tools = [
            'yahoo_finance_fetcher',
            'web_search',
            'company_news_fetcher',
            'financial_ratios_calculator',
            'pdf_parser',
            'excel_parser',
            'json_parser',
            'universal_file_parser',
        ]
    
    def _get_supported_task_types(self) -> List[str]:
        """Get list of supported task types"""
        return [
            'fetch_data',
            'fetch_stock_data',
            'fetch_financial_ratios',
            'fetch_news',
            'search_company',
            'parse_file',
            'calculate_ratios',
        ]
    
    def _execute_task(self, task: Dict[str, Any]) -> AgentResult:
        """
        Execute data-related task
        
        Task types:
        - fetch_stock_data: Fetch price and financial data
        - fetch_news: Fetch company news
        - search_company: Search for company information
        - parse_file: Parse a financial document
        """
        task_type = task.get('type')
        
        if task_type == 'fetch_stock_data':
            return self._fetch_stock_data(task)
        elif task_type == 'fetch_financial_ratios':
            return self._fetch_financial_ratios(task)
        elif task_type == 'fetch_news':
            return self._fetch_news(task)
        elif task_type == 'search_company':
            return self._search_company(task)
        elif task_type == 'parse_file':
            return self._parse_file(task)
        elif task_type == 'calculate_ratios':
            return self._calculate_ratios(task)
        elif task_type == 'fetch_data':
            # Generic fetch - determine what to fetch based on context
            return self._fetch_all_data(task)
        else:
            return AgentResult(
                success=False,
                error=f"Unknown task type: {task_type}"
            )
    
    def _fetch_stock_data(self, task: Dict[str, Any]) -> AgentResult:
        """Fetch stock data from Yahoo Finance"""
        ticker = task.get('ticker')
        
        if not ticker:
            return AgentResult(success=False, error="Ticker not provided")
        
        logger.info(f"Fetching stock data for {ticker}")
        
        # Execute Yahoo Finance tool
        result = self.execute_tool(
            'yahoo_finance_fetcher',
            ticker=ticker,
            include_financials=task.get('include_financials', True),
            include_prices=task.get('include_prices', True)
        )
        
        if result and result.success:
            # Post-process data
            data = self._preprocess_stock_data(result.data)
            return AgentResult(
                success=True,
                data=data,
                metadata={'ticker': ticker, 'source': 'yahoo_finance'}
            )
        else:
            return AgentResult(
                success=False,
                error=result.error if result else "Failed to fetch stock data"
            )
    
    def _preprocess_stock_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Preprocess stock data for downstream analysis
        
        - Validates data quality
        - Adds computed fields
        - Standardizes field names
        """
        if not data:
            return {}
        
        processed = data.copy()
        
        # Add data quality indicators
        processed['data_quality'] = self._assess_data_quality(data)
        
        # Add derived fields
        if 'market_cap' in data and 'share_price' in data:
            try:
                shares = data['market_cap'] / data['share_price']
                processed['shares_outstanding'] = shares
            except:
                pass
        
        # Standardize field names
        field_mappings = {
            'current_price': 'share_price',
            'price': 'share_price',
            'market_cap': 'market_capitalization'
        }
        
        for old_name, new_name in field_mappings.items():
            if old_name in processed and new_name not in processed:
                processed[new_name] = processed[old_name]
        
        return processed
    
    def _assess_data_quality(self, data: Dict[str, Any]) -> str:
        """Assess quality of fetched data"""
        required_fields = ['ticker', 'company_name', 'share_price']
        missing_fields = [f for f in required_fields if f not in data or data[f] is None]
        
        if len(missing_fields) > 1:
            return 'low'
        elif missing_fields:
            return 'medium'
        else:
            return 'high'
    
    def _fetch_financial_ratios(self, task: Dict[str, Any]) -> AgentResult:
        """Fetch and calculate financial ratios"""
        ticker = task.get('ticker')
        
        if not ticker:
            return AgentResult(success=False, error="Ticker not provided")
        
        logger.info(f"Fetching financial ratios for {ticker}")
        
        result = self.execute_tool(
            'financial_ratios_calculator',
            ticker=ticker
        )
        
        if result and result.success:
            return AgentResult(
                success=True,
                data=result.data,
                metadata={'ticker': ticker}
            )
        else:
            return AgentResult(
                success=False,
                error=result.error if result else "Failed to fetch ratios"
            )
    
    def _fetch_news(self, task: Dict[str, Any]) -> AgentResult:
        """Fetch company news"""
        ticker = task.get('ticker')
        limit = task.get('limit', 10)
        
        logger.info(f"Fetching news for {ticker}")
        
        result = self.execute_tool(
            'company_news_fetcher',
            ticker=ticker,
            limit=limit
        )
        
        if result and result.success:
            return AgentResult(
                success=True,
                data=result.data,
                metadata={'ticker': ticker, 'count': len(result.data) if result.data else 0}
            )
        else:
            return AgentResult(
                success=False,
                error=result.error if result else "Failed to fetch news"
            )
    
    def _search_company(self, task: Dict[str, Any]) -> AgentResult:
        """Search for company information"""
        query = task.get('query')
        
        if not query:
            return AgentResult(success=False, error="Search query not provided")
        
        logger.info(f"Searching for company: {query}")
        
        result = self.execute_tool(
            'web_search',
            query=query,
            num_results=task.get('num_results', 5)
        )
        
        if result and result.success:
            return AgentResult(
                success=True,
                data=result.data,
                metadata={'query': query}
            )
        else:
            return AgentResult(
                success=False,
                error=result.error if result else "Search failed"
            )
    
    def _parse_file(self, task: Dict[str, Any]) -> AgentResult:
        """Parse a financial document"""
        file_path = task.get('file_path')
        file_type = task.get('file_type')
        
        if not file_path:
            return AgentResult(success=False, error="File path not provided")
        
        logger.info(f"Parsing file: {file_path}")
        
        # Determine parser to use
        if not file_type:
            file_type = self._detect_file_type(file_path)
        
        parser_map = {
            'pdf': 'pdf_parser',
            'excel': 'excel_parser',
            'csv': 'csv_parser',
            'json': 'json_parser',
            'xml': 'xml_parser',
        }
        
        parser = parser_map.get(file_type, 'universal_file_parser')
        
        result = self.execute_tool(
            parser,
            file_path=file_path
        )
        
        if result and result.success:
            return AgentResult(
                success=True,
                data=result.data,
                metadata={'file_path': file_path, 'file_type': file_type}
            )
        else:
            return AgentResult(
                success=False,
                error=result.error if result else "Failed to parse file"
            )
    
    def _detect_file_type(self, file_path: str) -> str:
        """Detect file type from extension"""
        import os
        ext = os.path.splitext(file_path)[1].lower().lstrip('.')
        type_map = {
            'xlsx': 'excel',
            'xls': 'excel',
            'csv': 'csv',
            'pdf': 'pdf',
            'json': 'json',
            'xml': 'xml'
        }
        return type_map.get(ext, 'unknown')
    
    def _calculate_ratios(self, task: Dict[str, Any]) -> AgentResult:
        """Calculate financial ratios from raw data"""
        financial_data = task.get('financial_data')
        
        if not financial_data:
            return AgentResult(success=False, error="Financial data not provided")
        
        logger.info("Calculating financial ratios")
        
        ratios = {}
        
        # Extract key metrics
        revenue = financial_data.get('revenue', 0)
        net_income = financial_data.get('net_income', 0)
        ebitda = financial_data.get('ebitda', 0)
        market_cap = financial_data.get('market_cap', 0)
        share_price = financial_data.get('share_price', 0)
        shares_outstanding = financial_data.get('shares_outstanding', 0)
        
        # Calculate ratios
        if revenue > 0:
            ratios['profit_margin'] = net_income / revenue
            ratios['revenue'] = revenue
        
        if net_income > 0:
            ratios['net_income'] = net_income
        
        if ebitda > 0:
            ratios['ebitda'] = ebitda
        
        if market_cap > 0 and revenue > 0:
            ratios['ev_revenue'] = market_cap / revenue
        
        if market_cap > 0 and ebitda > 0:
            ratios['ev_ebitda'] = market_cap / ebitda
        
        if share_price > 0 and net_income > 0 and shares_outstanding > 0:
            eps = net_income / shares_outstanding
            ratios['pe_ratio'] = share_price / eps if eps > 0 else None
            ratios['eps'] = eps
        
        return AgentResult(
            success=True,
            data=ratios,
            metadata={'calculated': list(ratios.keys())}
        )
    
    def _fetch_all_data(self, task: Dict[str, Any]) -> AgentResult:
        """
        Fetch all available data for a company
        
        This is a convenience method that aggregates multiple data sources
        """
        ticker = task.get('ticker')
        
        if not ticker:
            return AgentResult(success=False, error="Ticker not provided")
        
        logger.info(f"Fetching all data for {ticker}")
        
        results = {
            'ticker': ticker,
            'data_sources': {}
        }
        
        # Fetch stock data
        stock_result = self._fetch_stock_data({'ticker': ticker})
        if stock_result.success:
            results['stock_data'] = stock_result.data
            results['data_sources']['stock'] = 'success'
        else:
            results['data_sources']['stock'] = 'failed'
        
        # Fetch ratios
        ratios_result = self._fetch_financial_ratios({'ticker': ticker})
        if ratios_result.success:
            results['financial_ratios'] = ratios_result.data
            results['data_sources']['ratios'] = 'success'
        else:
            results['data_sources']['ratios'] = 'failed'
        
        # Fetch news
        news_result = self._fetch_news({'ticker': ticker, 'limit': 5})
        if news_result.success:
            results['news'] = news_result.data
            results['data_sources']['news'] = 'success'
        else:
            results['data_sources']['news'] = 'failed'
        
        # Determine overall success
        success_count = sum(1 for v in results['data_sources'].values() if v == 'success')
        overall_success = success_count > 0
        
        return AgentResult(
            success=overall_success,
            data=results,
            metadata={
                'ticker': ticker,
                'data_sources_count': success_count,
                'total_sources': 3
            }
        )
