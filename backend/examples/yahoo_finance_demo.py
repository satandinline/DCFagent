"""
Yahoo Finance Integration for DCF Valuation System
FREE financial data API - No API key required!
"""
import asyncio
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    print("⚠️  yfinance not installed. Install with: pip install yfinance")


class YahooFinanceService:
    """Free Yahoo Finance data service"""
    
    def __init__(self):
        self.available = YFINANCE_AVAILABLE
    
    async def get_company_info(self, ticker: str) -> Dict[str, Any]:
        """
        Get comprehensive company information from Yahoo Finance
        
        Args:
            ticker: Stock ticker symbol (e.g., 'AAPL', 'MSFT')
            
        Returns:
            Dictionary with company information
        """
        if not self.available:
            return {'error': 'yfinance not installed'}
        
        try:
            print(f"📊 Fetching data for {ticker} from Yahoo Finance...")
            
            stock = yf.Ticker(ticker)
            
            # Get basic info
            info = stock.info
            
            if not info or 'longName' not in info:
                return {
                    'success': False,
                    'error': f'Could not find data for ticker: {ticker}'
                }
            
            # Extract key metrics
            result = {
                'success': True,
                'ticker': ticker,
                'company_name': info.get('longName', ''),
                'sector': info.get('sector', ''),
                'industry': info.get('industry', ''),
                'country': info.get('country', ''),
                
                # Market data
                'market_cap': info.get('marketCap', 0),
                'current_price': info.get('currentPrice', info.get('regularMarketPreviousClose', 0)),
                '52_week_high': info.get('fiftyTwoWeekHigh', 0),
                '52_week_low': info.get('fiftyTwoWeekLow', 0),
                
                # Financial metrics
                'revenue': info.get('totalRevenue', 0),
                'gross_profit': info.get('grossProfits', 0),
                'operating_income': info.get('operatingIncome', 0),
                'net_income': info.get('netIncomeToCommon', 0),
                
                # Margins
                'profit_margin': info.get('profitMargins', 0),
                'operating_margin': info.get('operatingMargins', 0),
                'gross_margin': info.get('grossMargins', 0),
                
                # Growth rates
                'revenue_growth': info.get('revenueGrowth', 0),
                'earnings_growth': info.get('earningsGrowth', 0),
                
                # Balance sheet
                'total_debt': info.get('totalDebt', 0),
                'total_cash': info.get('totalCash', 0),
                'shares_outstanding': info.get('sharesOutstanding', 0),
                
                # Valuation ratios
                'pe_ratio': info.get('trailingPE', 0),
                'pb_ratio': info.get('priceToBook', 0),
                'ps_ratio': info.get('priceToSalesTrailing12Months', 0),
                
                # Dividend
                'dividend_yield': info.get('dividendYield', 0),
                
                # Beta (for WACC calculation)
                'beta': info.get('beta', 1.0),
            }
            
            print(f"✓ Successfully fetched data for {result['company_name']}")
            return result
            
        except Exception as e:
            print(f"✗ Error fetching data: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_financial_statements(self, ticker: str) -> Dict[str, Any]:
        """
        Get detailed financial statements
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Financial statements data
        """
        if not self.available:
            return {'error': 'yfinance not installed'}
        
        try:
            stock = yf.Ticker(ticker)
            
            result = {
                'success': True,
                'ticker': ticker,
                'income_statement': None,
                'balance_sheet': None,
                'cash_flow': None,
            }
            
            # Get financial statements
            try:
                result['income_statement'] = stock.financials.to_dict()
            except:
                pass
            
            try:
                result['balance_sheet'] = stock.balance_sheet.to_dict()
            except:
                pass
            
            try:
                result['cash_flow'] = stock.cashflow.to_dict()
            except:
                pass
            
            return result
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    async def get_historical_prices(self, ticker: str, period: str = "1y") -> Dict[str, Any]:
        """
        Get historical price data
        
        Args:
            ticker: Stock ticker symbol
            period: Time period (1d, 5d, 1mo, 3mo, 6mo, 1y, 2y, 5y, 10y, ytd, max)
            
        Returns:
            Historical price data
        """
        if not self.available:
            return {'error': 'yfinance not installed'}
        
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period=period)
            
            return {
                'success': True,
                'ticker': ticker,
                'period': period,
                'data_points': len(hist),
                'prices': hist.to_dict(),
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


async def demo_yahoo_finance():
    """Demonstrate Yahoo Finance integration"""
    print("="*80)
    print("Yahoo Finance Integration Demo (FREE - No API Key)")
    print("="*80)
    
    service = YahooFinanceService()
    
    if not service.available:
        print("\n⚠️  yfinance not installed. Please run: pip install yfinance")
        return
    
    # Test 1: Get company info for Apple
    print("\n📈 Test 1: Apple Inc. (AAPL)")
    print("-"*80)
    
    info = await service.get_company_info("AAPL")
    
    if info['success']:
        print(f"Company: {info['company_name']}")
        print(f"Sector: {info['sector']}")
        print(f"Market Cap: ${info['market_cap']:,.0f}" if info['market_cap'] else "N/A")
        print(f"Current Price: ${info['current_price']:.2f}" if info['current_price'] else "N/A")
        print(f"Revenue: ${info['revenue']:,.0f}" if info['revenue'] else "N/A")
        print(f"Net Income: ${info['net_income']:,.0f}" if info['net_income'] else "N/A")
        print(f"Profit Margin: {info['profit_margin']*100:.2f}%" if info['profit_margin'] else "N/A")
        print(f"Beta: {info['beta']:.2f}")
        print(f"P/E Ratio: {info['pe_ratio']:.2f}" if info['pe_ratio'] else "N/A")
    else:
        print(f"Error: {info.get('error')}")
    
    # Test 2: Get company info for Microsoft
    print("\n" + "="*80)
    print("📈 Test 2: Microsoft (MSFT)")
    print("-"*80)
    
    info2 = await service.get_company_info("MSFT")
    
    if info2['success']:
        print(f"Company: {info2['company_name']}")
        print(f"Market Cap: ${info2['market_cap']:,.0f}" if info2['market_cap'] else "N/A")
        print(f"Revenue: ${info2['revenue']:,.0f}" if info2['revenue'] else "N/A")
        print(f"Beta: {info2['beta']:.2f}")
    
    # Test 3: Show how to use in DCF
    print("\n" + "="*80)
    print("💡 How to Use in DCF Valuation")
    print("-"*80)
    print("""
# Example: Auto-populate DCF parameters from Yahoo Finance

from services.yahoo_finance_service import YahooFinanceService
from services.dcf_service import run_dcf
from models.schemas import FinancialData, DCFParameters

yf_service = YahooFinanceService()

# 1. Get real market data
data = await yf_service.get_company_info("AAPL")

# 2. Create FinancialData object with real values
financial_data = FinancialData(
    company_name=data['company_name'],
    ticker="AAPL",
    revenue=data['revenue'],
    operating_income=data['operating_income'],
    net_income=data['net_income'],
    total_debt=data['total_debt'],
    cash_and_equivalents=data['total_cash'],
    shares_outstanding=data['shares_outstanding'],
    beta=data['beta'],  # Real beta from market!
    current_stock_price=data['current_price'],
)

# 3. Run DCF with real data
params = DCFParameters(...)
result = run_dcf(financial_data, params)

print(f"Fair Value: ${result.per_share_value:.2f}")
print(f"Current Price: ${data['current_price']:.2f}")
print(f"Upside: {(result.per_share_value - data['current_price']) / data['current_price'] * 100:.1f}%")
    """)
    
    print("\n" + "="*80)
    print("✅ Yahoo Finance is:")
    print("  ✓ Completely FREE")
    print("  ✓ No API key required")
    print("  ✓ No registration needed")
    print("  ✓ Real-time market data")
    print("  ✓ Comprehensive financial statements")
    print("  ✓ Very reliable and stable")
    print("="*80)


if __name__ == '__main__':
    asyncio.run(demo_yahoo_finance())
