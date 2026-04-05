"""
Web Search Service for DCF Valuation System
Multi-tier search strategy:
1. Yahoo Finance (Financial data - FREE)
2. DuckDuckGo (General search - FREE)
3. Google Search (Fallback - FREE)
"""
from __future__ import annotations

import logging
import asyncio
from typing import Any, Dict, List, Optional

# Try to import search libraries
try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logging.warning("yfinance not installed. Install with: pip install yfinance")

try:
    from ddgs import DDGS
    DUCKDUCKGO_AVAILABLE = True
except ImportError:
    try:
        from duckduckgo_search import DDGS
        DUCKDUCKGO_AVAILABLE = True
    except ImportError:
        DUCKDUCKGO_AVAILABLE = False
        logging.warning("ddgs not installed. Install with: pip install ddgs")

try:
    from googlesearch import search as google_search
    GOOGLE_SEARCH_AVAILABLE = True
except ImportError:
    GOOGLE_SEARCH_AVAILABLE = False
    logging.warning("googlesearch-python not installed. Install with: pip install googlesearch-python")

logger = logging.getLogger(__name__)


class WebSearchService:
    """
    Multi-tier web search service with fallback strategy:
    1. Yahoo Finance - Best for financial data (FREE)
    2. DuckDuckGo - Best for general search (FREE)
    3. Google Search - Fallback option (FREE)
    """
    
    def __init__(self):
        self.search_enabled = True
        self.yfinance_available = YFINANCE_AVAILABLE
        self.duckduckgo_available = DUCKDUCKGO_AVAILABLE
        self.google_available = GOOGLE_SEARCH_AVAILABLE
    
    async def search_company_info(self, company_name: str, ticker: Optional[str] = None) -> Dict[str, Any]:
        """
        Search for company information using multi-tier strategy
        
        Priority:
        1. Yahoo Finance (if ticker provided) - Best for financial data
        2. DuckDuckGo - Best for general information
        3. Google Search - Fallback
        
        Args:
            company_name: Name of the company
            ticker: Stock ticker symbol (optional but recommended)
            
        Returns:
            Dictionary containing company information from best available source
        """
        logger.info(f"Searching for company: {company_name} ({ticker})")
        
        result = {
            'success': False,
            'company_name': company_name,
            'ticker': ticker,
            'sources_used': [],
            'financial_data': None,
            'search_results': [],
            'summary': ''
        }
        
        # Tier 1: Yahoo Finance (if ticker available)
        if ticker and self.yfinance_available:
            logger.info("Tier 1: Trying Yahoo Finance...")
            yf_result = await self._search_yahoo_finance(ticker)
            
            if yf_result['success']:
                logger.info("✓ Yahoo Finance successful")
                result['success'] = True
                result['sources_used'].append('yahoo_finance')
                result['financial_data'] = yf_result['data']
                result['summary'] = yf_result.get('summary', '')
                
                # Still try DuckDuckGo for additional context
                if self.duckduckgo_available:
                    ddg_result = await self._search_duckduckgo(company_name, ticker)
                    if ddg_result['success']:
                        result['sources_used'].append('duckduckgo')
                        result['search_results'] = ddg_result.get('results', [])
                        result['summary'] += "\n\nAdditional Info:\n" + ddg_result.get('summary', '')
                
                return result
        
        # Tier 2: DuckDuckGo
        if self.duckduckgo_available:
            logger.info("Tier 2: Trying DuckDuckGo...")
            ddg_result = await self._search_duckduckgo(company_name, ticker)
            
            if ddg_result['success']:
                logger.info("✓ DuckDuckGo successful")
                result['success'] = True
                result['sources_used'].append('duckduckgo')
                result['search_results'] = ddg_result.get('results', [])
                result['summary'] = ddg_result.get('summary', '')
                return result
        
        # Tier 3: Google Search (fallback)
        if self.google_available:
            logger.info("Tier 3: Trying Google Search...")
            google_result = await self._search_google(company_name, ticker)
            
            if google_result['success']:
                logger.info("✓ Google Search successful")
                result['success'] = True
                result['sources_used'].append('google')
                result['search_results'] = google_result.get('results', [])
                result['summary'] = google_result.get('summary', '')
                return result
        
        # All methods failed
        logger.warning("All search methods failed, using mock data")
        result['sources_used'].append('mock')
        result['search_results'] = self._get_mock_results(company_name, ticker)
        result['summary'] = "No real data available. Using placeholder information."
        
        return result
    
    async def _search_yahoo_finance(self, ticker: str) -> Dict[str, Any]:
        """
        Tier 1: Search Yahoo Finance for financial data
        Best for: Real-time market data, financial statements
        Includes retry logic for rate limiting
        """
        max_retries = 3
        retry_delays = [3, 6, 10]  # 更长的等待时间
        
        for attempt in range(max_retries):
            try:
                loop = asyncio.get_event_loop()
                
                # Run yfinance in executor to avoid blocking
                def fetch_yf_data():
                    stock = yf.Ticker(ticker)
                    info = stock.info
                    
                    if not info or 'longName' not in info:
                        return None
                    
                    return {
                        'company_name': info.get('longName', ''),
                        'sector': info.get('sector', ''),
                        'industry': info.get('industry', ''),
                        'market_cap': info.get('marketCap', 0),
                        'current_price': info.get('currentPrice', info.get('regularMarketPreviousClose', 0)),
                        'revenue': info.get('totalRevenue', 0),
                        'operating_income': info.get('operatingIncome', 0),
                        'net_income': info.get('netIncomeToCommon', 0),
                        'profit_margin': info.get('profitMargins', 0),
                        'operating_margin': info.get('operatingMargins', 0),
                        'revenue_growth': info.get('revenueGrowth', 0),
                        'total_debt': info.get('totalDebt', 0),
                        'total_cash': info.get('totalCash', 0),
                        'shares_outstanding': info.get('sharesOutstanding', 0),
                        'beta': info.get('beta', 1.0),
                        'pe_ratio': info.get('trailingPE', 0),
                    }
                
                data = await loop.run_in_executor(None, fetch_yf_data)
                
                if not data:
                    return {'success': False, 'error': 'No data found'}
                
                # Build summary
                summary_parts = [f"Company: {data['company_name']}"]
                if data.get('sector'):
                    summary_parts.append(f"Sector: {data['sector']}")
                if data.get('market_cap'):
                    summary_parts.append(f"Market Cap: ${data['market_cap']:,.0f}")
                if data.get('revenue'):
                    summary_parts.append(f"Revenue: ${data['revenue']:,.0f}")
                if data.get('net_income'):
                    summary_parts.append(f"Net Income: ${data['net_income']:,.0f}")
                if data.get('profit_margin'):
                    summary_parts.append(f"Profit Margin: {data['profit_margin']*100:.2f}%")
                if data.get('beta'):
                    summary_parts.append(f"Beta: {data['beta']:.2f}")
                
                return {
                    'success': True,
                    'source': 'yahoo_finance',
                    'data': data,
                    'summary': '\n'.join(summary_parts)
                }
                
            except Exception as e:
                error_msg = str(e)
                if 'Too Many Requests' in error_msg or 'Rate limited' in error_msg:
                    if attempt < max_retries - 1:
                        delay = retry_delays[attempt]
                        logger.warning(f"Yahoo Finance rate limited. Waiting {delay}s... (attempt {attempt + 1}/{max_retries})")
                        await asyncio.sleep(delay)
                        continue
                    else:
                        logger.error(f"Yahoo Finance failed after {max_retries} retries")
                        return {'success': False, 'error': 'Rate limited after retries'}
                else:
                    logger.error(f"Yahoo Finance error: {e}")
                    return {'success': False, 'error': error_msg}
        
        return {'success': False, 'error': 'Max retries exceeded'}
    
    async def _search_duckduckgo(self, company_name: str, ticker: Optional[str] = None) -> Dict[str, Any]:
        """
        Tier 2: Search DuckDuckGo for general information
        Best for: Company news, industry context, general info
        """
        try:
            query = f"{company_name} {ticker} financial data revenue profit" if ticker else f"{company_name} financial data"
            logger.info(f"DuckDuckGo query: {query}")
            
            loop = asyncio.get_event_loop()
            
            def perform_ddg_search():
                with DDGS() as ddgs:
                    results = list(ddgs.text(query, max_results=5))
                return results
            
            results = await loop.run_in_executor(None, perform_ddg_search)
            
            if not results:
                return {'success': False, 'error': 'No results found'}
            
            # Format results
            formatted_results = []
            for i, res in enumerate(results[:5]):
                formatted_results.append({
                    'title': res.get('title', f'Result {i+1}'),
                    'url': res.get('href', ''),
                    'content': res.get('body', '')[:300],
                    'source': 'duckduckgo',
                    'relevance_score': 1.0 - (i * 0.15)
                })
            
            # Build summary
            summary_lines = [f"Found {len(formatted_results)} results from DuckDuckGo:"]
            for i, res in enumerate(formatted_results[:3], 1):
                summary_lines.append(f"{i}. {res['title'][:80]}...")
            
            return {
                'success': True,
                'source': 'duckduckgo',
                'results': formatted_results,
                'summary': '\n'.join(summary_lines)
            }
            
        except Exception as e:
            logger.error(f"DuckDuckGo search failed: {e}")
            return {'success': False, 'error': str(e)}
    
    async def _search_google(self, company_name: str, ticker: Optional[str] = None) -> Dict[str, Any]:
        """
        Tier 3: Google Search as fallback
        Best for: When other methods fail
        """
        try:
            query = f"{company_name} {ticker} financial data revenue profit market cap" if ticker else f"{company_name} financial data revenue profit"
            logger.info(f"Google query: {query}")
            
            loop = asyncio.get_event_loop()
            
            def perform_google_search():
                try:
                    urls = list(google_search(query, num_results=5, lang="en", safe="off"))
                    return urls
                except Exception as e:
                    logger.warning(f"Google search error: {e}")
                    return []
            
            urls = await loop.run_in_executor(None, perform_google_search)
            
            if not urls:
                logger.warning("Google search returned no results")
                return {'success': False, 'error': 'No results found'}
            
            # Format results
            from urllib.parse import urlparse
            formatted_results = []
            
            for i, url in enumerate(urls[:5]):
                try:
                    parsed = urlparse(url)
                    domain = parsed.netloc.replace('www.', '')
                    
                    # Clean up domain
                    if not domain or domain == '':
                        domain = 'unknown'
                    
                    formatted_results.append({
                        'title': f"Result {i+1} from {domain}",
                        'url': url,
                        'content': f"Source: {domain}\nURL: {url}",
                        'source': domain,
                        'relevance_score': 1.0 - (i * 0.15)
                    })
                except Exception as e:
                    logger.warning(f"Failed to process result {i}: {e}")
                    continue
            
            if not formatted_results:
                return {'success': False, 'error': 'Failed to format results'}
            
            # Build summary
            summary_lines = [f"Found {len(formatted_results)} results from Google:"]
            for i, res in enumerate(formatted_results[:3], 1):
                summary_lines.append(f"{i}. {res['title']}")
                summary_lines.append(f"   → {res['url'][:80]}...")
            
            return {
                'success': True,
                'source': 'google',
                'results': formatted_results,
                'summary': '\n'.join(summary_lines)
            }
            
        except Exception as e:
            logger.error(f"Google search failed: {e}")
            return {'success': False, 'error': str(e)}
    
    def _get_mock_results(self, company_name: str, ticker: Optional[str] = None) -> List[Dict[str, str]]:
        """Generate mock search results for demonstration"""
        return [
            {
                'title': f"{company_name} - Company Overview",
                'url': f"https://example.com/{company_name.lower().replace(' ', '-')}",
                'content': f"{company_name} is a leading company in its industry.",
                'source': 'mock',
                'relevance_score': 0.8
            }
        ]
    
    def _summarize_results(self, results: List[Dict[str, str]]) -> str:
        """Summarize search results into a concise text"""
        if not results:
            return "No additional information found."
        
        summaries = []
        for i, result in enumerate(results[:3], 1):
            summaries.append(f"{i}. {result.get('title', 'N/A')}: {result.get('content', 'N/A')[:200]}")
        
        return "\n".join(summaries)
    
    async def search_financial_metrics(self, company_name: str, ticker: Optional[str] = None) -> Dict[str, Any]:
        """
        Search specifically for financial metrics
        
        Args:
            company_name: Company name
            ticker: Stock ticker
            
        Returns:
            Financial metrics found online
        """
        logger.info(f"Searching financial metrics for {company_name}")
        
        # This would integrate with financial data APIs like:
        # - Alpha Vantage
        # - Yahoo Finance API
        # - IEX Cloud
        # - Financial Modeling Prep
        
        return {
            'success': True,
            'metrics': {
                'note': 'Financial API integration needed',
                'suggested_apis': [
                    'Alpha Vantage',
                    'Yahoo Finance',
                    'IEX Cloud',
                    'Financial Modeling Prep'
                ]
            }
        }


# Singleton instance
web_search_service = WebSearchService()
