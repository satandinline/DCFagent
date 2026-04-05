"""
Integration example: How to use database service with DCF analysis
This demonstrates storing and retrieving financial data for DCF valuation
"""
import sys
import os
from datetime import date, datetime
from decimal import Decimal

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.db_service import db_service


def store_analysis_data(ticker: str, company_name: str, financial_data: dict):
    """
    Store complete financial analysis data for a company
    
    Args:
        ticker: Stock ticker symbol (e.g., 'AAPL')
        company_name: Full company name
        financial_data: Dictionary containing all financial data
    """
    print(f"\n{'='*60}")
    print(f"Storing Analysis Data for {ticker} - {company_name}")
    print(f"{'='*60}")
    
    # 1. Store stock information
    print("\n[1/6] Storing stock information...")
    success = db_service.insert_stock(ticker, "US")
    if success:
        print(f"  ✓ Stock {ticker} stored")
    
    # 2. Store asset profile
    print("\n[2/6] Storing company profile...")
    profile_data = {
        'sector': financial_data.get('sector', ''),
        'industry': financial_data.get('industry', ''),
        'full_time_employees': financial_data.get('employees'),
        'description': financial_data.get('description', '')
    }
    success = db_service.insert_asset_profile(ticker, profile_data)
    if success:
        print(f"  ✓ Company profile stored")
    
    # 3. Store income statements
    print("\n[3/6] Storing income statements...")
    for income_stmt in financial_data.get('income_statements', []):
        success = db_service.insert_income_statement(ticker, income_stmt)
        if success:
            report_date = income_stmt['report_date']
            revenue = income_stmt.get('total_revenue', 0)
            print(f"  ✓ Income statement for {report_date} (Revenue: ${revenue:,.0f})")
    
    # 4. Store balance sheets
    print("\n[4/6] Storing balance sheets...")
    for balance_sheet in financial_data.get('balance_sheets', []):
        success = db_service.insert_balance_sheet(ticker, balance_sheet)
        if success:
            report_date = balance_sheet['report_date']
            assets = balance_sheet.get('total_assets', 0)
            print(f"  ✓ Balance sheet for {report_date} (Assets: ${assets:,.0f})")
    
    # 5. Store cash flows
    print("\n[5/6] Storing cash flow statements...")
    for cash_flow in financial_data.get('cash_flows', []):
        success = db_service.insert_cash_flow(ticker, cash_flow)
        if success:
            report_date = cash_flow['report_date']
            operating_cf = cash_flow.get('operating_activities', 0)
            print(f"  ✓ Cash flow for {report_date} (Operating CF: ${operating_cf:,.0f})")
    
    # 6. Store historical prices (if available)
    if financial_data.get('historical_prices'):
        print("\n[6/6] Storing historical prices...")
        for price_data in financial_data['historical_prices']:
            success = db_service.insert_historical_price(ticker, price_data)
            if success:
                price_date = price_data['price_date']
                close_price = price_data.get('close_price', 0)
                print(f"  ✓ Price for {price_date} (Close: ${close_price:,.2f})")
    
    print(f"\n{'='*60}")
    print(f"✓ All data for {ticker} stored successfully!")
    print(f"{'='*60}\n")


def retrieve_analysis_data(ticker: str):
    """
    Retrieve all stored analysis data for DCF calculation
    
    Args:
        ticker: Stock ticker symbol
    
    Returns:
        Dictionary containing all retrieved data
    """
    print(f"\n{'='*60}")
    print(f"Retrieving Analysis Data for {ticker}")
    print(f"{'='*60}")
    
    # Get comprehensive stock data
    stock_data = db_service.get_stock_data(ticker)
    
    if not stock_data:
        print(f"✗ No data found for {ticker}")
        return None
    
    print(f"\n✓ Basic Information:")
    print(f"  Ticker: {ticker}")
    print(f"  Locale: {stock_data.get('locale')}")
    
    if stock_data.get('profile'):
        profile = stock_data['profile']
        print(f"\n✓ Company Profile:")
        print(f"  Sector: {profile.get('sector', 'N/A')}")
        print(f"  Industry: {profile.get('industry', 'N/A')}")
        if profile.get('full_time_employees'):
            print(f"  Employees: {profile['full_time_employees']:,}")
    
    # Get latest financial statements for DCF
    if stock_data.get('latest_income_statement'):
        stmt = stock_data['latest_income_statement']
        print(f"\n✓ Latest Income Statement ({stmt['report_date']}):")
        print(f"  Total Revenue: ${stmt.get('total_revenue', 0):,.0f}")
        print(f"  Operating Income: ${stmt.get('operating_income', 0):,.0f}")
        print(f"  Net Income: ${stmt.get('net_income', 0):,.0f}")
        print(f"  EBIT: ${stmt.get('ebit', 0):,.0f}")
    
    if stock_data.get('latest_balance_sheet'):
        stmt = stock_data['latest_balance_sheet']
        print(f"\n✓ Latest Balance Sheet ({stmt['report_date']}):")
        print(f"  Total Assets: ${stmt.get('total_assets', 0):,.0f}")
        print(f"  Total Liabilities: ${stmt.get('total_liabilities', 0):,.0f}")
        print(f"  Total Equity: ${stmt.get('total_equity', 0):,.0f}")
        print(f"  Cash & Equivalents: ${stmt.get('cash_and_equivalents', 0):,.0f}")
    
    if stock_data.get('latest_cash_flow'):
        stmt = stock_data['latest_cash_flow']
        print(f"\n✓ Latest Cash Flow ({stmt['report_date']}):")
        print(f"  Operating Activities: ${stmt.get('operating_activities', 0):,.0f}")
        print(f"  Investment Activities: ${stmt.get('investment_activities', 0):,.0f}")
        print(f"  Financing Activities: ${stmt.get('financing_activities', 0):,.0f}")
        print(f"  Changes in Cash: ${stmt.get('changes_in_cash', 0):,.0f}")
    
    # Get historical trends
    statements = db_service.get_financial_statements(ticker, 'annual')
    
    if statements['income_statements']:
        print(f"\n✓ Historical Data Available:")
        print(f"  Income Statements: {len(statements['income_statements'])} records")
        print(f"  Balance Sheets: {len(statements['balance_sheets'])} records")
        print(f"  Cash Flows: {len(statements['cash_flows'])} records")
        
        # Calculate revenue growth trend
        if len(statements['income_statements']) >= 2:
            revenues = [float(stmt['total_revenue']) for stmt in statements['income_statements'] if stmt.get('total_revenue')]
            if len(revenues) >= 2:
                oldest = revenues[-1]
                newest = revenues[0]
                if oldest > 0:
                    growth_rate = ((newest - oldest) / oldest) * 100
                    years = len(revenues) - 1
                    cagr = ((newest / oldest) ** (1/years) - 1) * 100 if years > 0 else 0
                    print(f"\n✓ Revenue Growth Analysis:")
                    print(f"  Period: {statements['income_statements'][-1]['report_date']} to {statements['income_statements'][0]['report_date']}")
                    print(f"  Total Growth: {growth_rate:.2f}%")
                    print(f"  CAGR: {cagr:.2f}%")
    
    # Get recent stock prices
    prices = db_service.get_historical_prices(ticker, frequency='1d')
    if prices:
        print(f"\n✓ Stock Price Data:")
        print(f"  Total Records: {len(prices)}")
        if prices:
            latest = prices[-1]
            print(f"  Latest Price: ${latest.get('close_price', 0):,.2f} ({latest.get('price_date')})")
            
            if len(prices) >= 30:
                # Calculate 30-day average
                recent_prices = [p['close_price'] for p in prices[-30:] if p.get('close_price')]
                if recent_prices:
                    avg_price = sum(recent_prices) / len(recent_prices)
                    print(f"  30-Day Average: ${avg_price:,.2f}")
    
    print(f"\n{'='*60}")
    print(f"✓ Data retrieval complete for {ticker}")
    print(f"{'='*60}\n")
    
    return stock_data


def prepare_dcf_inputs(ticker: str) -> dict:
    """
    Prepare inputs for DCF calculation from database
    
    Args:
        ticker: Stock ticker symbol
    
    Returns:
        Dictionary with DCF calculation inputs
    """
    print(f"\nPreparing DCF inputs for {ticker}...")
    
    stock_data = db_service.get_stock_data(ticker)
    if not stock_data:
        raise ValueError(f"No data found for ticker: {ticker}")
    
    # Extract key metrics for DCF
    latest_income = stock_data.get('latest_income_statement', {})
    latest_balance = stock_data.get('latest_balance_sheet', {})
    latest_cashflow = stock_data.get('latest_cash_flow', {})
    
    dcf_inputs = {
        'ticker': ticker,
        'free_cash_flow': latest_cashflow.get('operating_activities', 0),  # Simplified FCF
        'revenue': latest_income.get('total_revenue', 0),
        'operating_income': latest_income.get('operating_income', 0),
        'net_income': latest_income.get('net_income', 0),
        'ebit': latest_income.get('ebit', 0),
        'total_debt': latest_balance.get('total_liabilities', 0),
        'cash_and_equivalents': latest_balance.get('cash_and_equivalents', 0),
        'shares_outstanding': None,  # Would need additional data source
        'growth_rate': 0.05,  # Default 5% growth rate (should be calculated from historical data)
        'discount_rate': 0.10,  # Default 10% discount rate (WACC)
        'terminal_growth_rate': 0.02,  # Default 2% terminal growth
        'projection_years': 5
    }
    
    # Calculate historical growth rate if we have enough data
    statements = db_service.get_financial_statements(ticker, 'annual')
    if len(statements['income_statements']) >= 2:
        revenues = [float(stmt['total_revenue']) for stmt in statements['income_statements'] 
                   if stmt.get('total_revenue') and float(stmt['total_revenue']) > 0]
        if len(revenues) >= 2:
            oldest = revenues[-1]
            newest = revenues[0]
            years = len(revenues) - 1
            if years > 0 and oldest > 0:
                cagr = ((newest / oldest) ** (1/years) - 1)
                dcf_inputs['growth_rate'] = min(cagr, 0.15)  # Cap at 15%
                print(f"  ✓ Calculated historical growth rate: {cagr*100:.2f}%")
    
    print(f"  ✓ DCF inputs prepared")
    print(f"    - Free Cash Flow: ${dcf_inputs['free_cash_flow']:,.0f}")
    print(f"    - Revenue: ${dcf_inputs['revenue']:,.0f}")
    print(f"    - Growth Rate: {dcf_inputs['growth_rate']*100:.2f}%")
    print(f"    - Discount Rate: {dcf_inputs['discount_rate']*100:.2f}%")
    
    return dcf_inputs


def main():
    """Main function demonstrating full workflow"""
    try:
        print("="*60)
        print("DCF Database Integration Example")
        print("="*60)
        
        # Example 1: Store sample financial data
        sample_data = {
            'sector': 'Technology',
            'industry': 'Consumer Electronics',
            'employees': 164000,
            'description': 'Apple Inc. designs, manufactures, and markets smartphones worldwide.',
            'income_statements': [
                {
                    'report_date': date(2023, 9, 30),
                    'report_type': 'annual',
                    'total_revenue': 383285000000,
                    'gross_profit': 169148000000,
                    'operating_income': 114301000000,
                    'net_income': 96995000000,
                    'ebit': 123240000000
                },
                {
                    'report_date': date(2022, 9, 24),
                    'report_type': 'annual',
                    'total_revenue': 394328000000,
                    'gross_profit': 170782000000,
                    'operating_income': 119437000000,
                    'net_income': 99803000000,
                    'ebit': 130541000000
                }
            ],
            'balance_sheets': [
                {
                    'report_date': date(2023, 9, 30),
                    'report_type': 'annual',
                    'total_assets': 352755000000,
                    'total_liabilities': 290437000000,
                    'total_equity': 62318000000,
                    'cash_and_equivalents': 29965000000
                }
            ],
            'cash_flows': [
                {
                    'report_date': date(2023, 9, 30),
                    'report_type': 'annual',
                    'operating_activities': 110543000000,
                    'investment_activities': -10959000000,
                    'financing_activities': -108488000000,
                    'changes_in_cash': -8904000000,
                    'overall': -8904000000
                }
            ],
            'historical_prices': [
                {
                    'price_date': date(2024, 1, 15),
                    'data_frequency': '1d',
                    'open_price': 182.16,
                    'high_price': 184.26,
                    'low_price': 180.93,
                    'close_price': 183.63,
                    'adj_close': 183.63,
                    'volume': 54156300
                }
            ]
        }
        
        # Store the data
        store_analysis_data("AAPL", "Apple Inc.", sample_data)
        
        # Retrieve and display the data
        retrieve_analysis_data("AAPL")
        
        # Prepare DCF inputs
        dcf_inputs = prepare_dcf_inputs("AAPL")
        
        print("\n" + "="*60)
        print("✓ Integration example completed successfully!")
        print("="*60)
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        db_service.close_connection()
        print("\nDatabase connection closed.")


if __name__ == "__main__":
    main()
