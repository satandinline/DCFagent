"""
RAG (Retrieval-Augmented Generation) Service for DCF Valuation
Combines database retrieval with web search for comprehensive analysis
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .db_service import db_service
from .web_search_service import web_search_service

logger = logging.getLogger(__name__)


class RAGService:
    """
    RAG Service that combines:
    1. Database retrieval (first priority)
    2. Web search (fallback/enhancement)
    3. LLM analysis (final synthesis)
    """
    
    def __init__(self):
        self.db_service = db_service
        self.web_search = web_search_service
    
    async def retrieve_company_context(
        self, 
        company_name: str, 
        ticker: Optional[str] = None,
        use_web_search: bool = True
    ) -> Dict[str, Any]:
        """
        Retrieve comprehensive company context using RAG approach
        
        Flow:
        1. Search database for existing information
        2. If insufficient, perform web search
        3. Combine and return enriched context
        
        Args:
            company_name: Name of the company
            ticker: Stock ticker symbol
            use_web_search: Whether to use web search as fallback
            
        Returns:
            Comprehensive company context dictionary
        """
        logger.info(f"RAG retrieval for: {company_name} ({ticker})")
        
        result = {
            'company_name': company_name,
            'ticker': ticker,
            'sources': [],
            'context': '',
            'financial_data': None,
            'valuation_history': [],
            'web_search_used': False
        }
        
        # Step 1: Database Retrieval (Primary Source)
        logger.info("Step 1: Searching database...")
        db_context = await self._retrieve_from_database(company_name, ticker)
        
        if db_context['has_data']:
            logger.info("✓ Found data in database")
            result['sources'].append('database')
            result['financial_data'] = db_context.get('financial_data')
            result['valuation_history'] = db_context.get('valuation_history', [])
            result['context'] = db_context.get('summary', '')
        else:
            logger.info("✗ No data found in database")
        
        # Step 2: Web Search (Fallback/Enhancement)
        if use_web_search and not db_context['has_data']:
            logger.info("Step 2: Performing web search (database empty)...")
            web_result = await self.web_search.search_company_info(company_name, ticker)
            
            if web_result['success']:
                logger.info("✓ Web search successful")
                result['sources'].append('web_search')
                result['web_search_used'] = True
                result['context'] += "\n\nWeb Search Results:\n" + web_result.get('summary', '')
                result['search_results'] = web_result.get('search_results', [])
        
        # Step 3: Enrich with trends if available
        if ticker and db_context['has_data']:
            logger.info("Step 3: Calculating trends...")
            try:
                trends = self.db_service.calculate_growth_trends(ticker)
                if trends:
                    result['trends'] = trends
                    result['context'] += f"\n\nGrowth Trends:\n{str(trends)}"
            except Exception as e:
                logger.warning(f"Could not calculate trends: {e}")
        
        # Build final context summary
        result['context_summary'] = self._build_context_summary(result)
        
        logger.info(f"RAG retrieval complete. Sources: {result['sources']}")
        return result
    
    async def _retrieve_from_database(
        self, 
        company_name: str, 
        ticker: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve all available information from database
        
        Returns:
            Dictionary with database findings
        """
        result = {
            'has_data': False,
            'financial_data': None,
            'valuation_history': [],
            'summary': ''
        }
        
        try:
            # Try to get stock data by ticker
            if ticker:
                stock_data = self.db_service.get_stock_data(ticker)
                if stock_data:
                    result['has_data'] = True
                    result['summary'] += f"Company: {stock_data.get('company_name', company_name)}\n"
                    result['summary'] += f"Ticker: {ticker}\n"
                    result['summary'] += f"Country: {stock_data.get('country_code', 'N/A')}\n\n"
            
            # Get latest financial statements
            if ticker:
                stock_data = self.db_service.get_stock_data(ticker)
                if stock_data and stock_data.get('latest_income_statement'):
                    latest_income = stock_data['latest_income_statement']
                    result['has_data'] = True
                    result['financial_data'] = latest_income
                    result['summary'] += f"Latest Revenue: ${latest_income.get('total_revenue', 0):,.0f}\n"
                    result['summary'] += f"Operating Income: ${latest_income.get('operating_income', 0):,.0f}\n"
                    result['summary'] += f"Net Income: ${latest_income.get('net_income', 0):,.0f}\n\n"
            
            # Get valuation history
            if ticker:
                valuations = self.db_service.get_valuation_history(ticker, limit=5)
                if valuations:
                    result['has_data'] = True
                    result['valuation_history'] = valuations
                    result['summary'] += f"Valuation History: {len(valuations)} records\n"
                    for v in valuations[:3]:
                        result['summary'] += f"  - {v.get('valuation_date')}: ${v.get('per_share_value', 0):,.2f}/share\n"
            
        except Exception as e:
            logger.error(f"Database retrieval error: {e}")
        
        return result
    
    def _build_context_summary(self, result: Dict[str, Any]) -> str:
        """Build a concise summary of all retrieved context"""
        summary_parts = []
        
        if 'database' in result['sources']:
            summary_parts.append("📊 Database: Historical financial data available")
        
        if 'web_search' in result['sources']:
            summary_parts.append("🌐 Web Search: Additional market information retrieved")
        
        if result.get('trends'):
            summary_parts.append("📈 Trends: Growth analysis calculated")
        
        if result.get('valuation_history'):
            count = len(result['valuation_history'])
            summary_parts.append(f"💰 Valuation History: {count} previous analyses")
        
        return " | ".join(summary_parts) if summary_parts else "No additional context available"
    
    async def enhance_with_rag(
        self,
        pdf_text: str,
        company_name: str,
        ticker: Optional[str] = None,
        use_web_search: bool = True
    ) -> str:
        """
        Enhance PDF text with RAG-retrieved context
        
        This method should be called before LLM extraction to provide
        richer context for better analysis.
        
        Args:
            pdf_text: Original PDF text
            company_name: Company name
            ticker: Stock ticker
            use_web_search: Enable web search fallback
            
        Returns:
            Enhanced text with RAG context appended
        """
        logger.info(f"Enhancing analysis with RAG for {company_name}")
        
        # Retrieve context
        context = await self.retrieve_company_context(company_name, ticker, use_web_search)
        
        # Build enhancement prompt
        enhancement = f"""

=== ADDITIONAL CONTEXT (RAG-ENHANCED) ===

Company: {company_name}
Ticker: {ticker or 'N/A'}

Context Sources: {', '.join(context['sources']) if context['sources'] else 'None'}
{context.get('context_summary', '')}

Historical Context:
{context.get('context', 'No historical data available')}

Please use this additional context along with the PDF content to provide a more accurate and comprehensive DCF valuation analysis.
========================================
"""
        
        enhanced_text = pdf_text + enhancement
        logger.info(f"Text enhanced: {len(pdf_text)} → {len(enhanced_text)} chars")
        
        return enhanced_text


# Singleton instance
rag_service = RAGService()
