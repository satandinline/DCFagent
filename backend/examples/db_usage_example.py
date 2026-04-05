"""
Example script demonstrating how to use the database service
to store financial analysis data for DCF estimation
"""
import sys
import os
from datetime import date, datetime

# Add the backend directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from services.db_service import db_service


def example_store_stock_data():
    """Example: Store stock and profile data"""
    print("=== Example: Storing Stock Data ===")
    
    # Insert a stock
    ticker = "AAPL"
    success = db_service.insert_stock(ticker, "US")
    if success:
        print(f"Stock {ticker} inserted successfully")
    
    # Insert asset profile
    profile_data = {
        'sector': 'Technology',
        'industry': 'Consumer Electronics',
        'full_time_employees': 164000,
        'description': 'Apple Inc. designs, manufactures, and markets smartphones, personal computers, tablets, wearables, and accessories worldwide.'
    }
    success = db_service.insert_asset_profile(ticker, profile_data)
    if success:
        print(f"Asset profile for {ticker} inserted successfully")


def example_store_financial_statements():
    """Example: Store financial statement data"""
    print("\n=== Example: Storing Financial Statements ===")
    
    ticker = "AAPL"
    
    # Insert income statement (annual)
    income_statement = {
        'report_date': date(2023, 9, 30),
        'report_type': 'annual',
        'total_revenue': 383285000000,
        'gross_profit': 169148000000,
        'operating_income': 114301000000,
        'net_income': 96995000000,
        'ebit': 123240000000
    }
    success = db_service.insert_income_statement(ticker, income_statement)
    if success:
        print(f"Income statement for {ticker} inserted successfully")
    
    # Insert balance sheet (annual)
    balance_sheet = {
        'report_date': date(2023, 9, 30),
        'report_type': 'annual',
        'total_assets': 352755000000,
        'total_liabilities': 290437000000,
        'total_equity': 62318000000,
        'cash_and_equivalents': 29965000000
    }
    success = db_service.insert_balance_sheet(ticker, balance_sheet)
    if success:
        print(f"Balance sheet for {ticker} inserted successfully")
    
    # Insert cash flow (annual)
    cash_flow = {
        'report_date': date(2023, 9, 30),
        'report_type': 'annual',
        'operating_activities': 110543000000,
        'investment_activities': -10959000000,
        'financing_activities': -108488000000,
        'changes_in_cash': -8904000000,
        'overall': -8904000000
    }
    success = db_service.insert_cash_flow(ticker, cash_flow)
    if success:
        print(f"Cash flow for {ticker} inserted successfully")


def example_store_historical_prices():
    """Example: Store historical price data"""
    print("\n=== Example: Storing Historical Prices ===")
    
    ticker = "AAPL"
    
    # Insert historical price
    price_data = {
        'price_date': date(2024, 1, 15),
        'data_frequency': '1d',
        'open_price': 182.16,
        'high_price': 184.26,
        'low_price': 180.93,
        'close_price': 183.63,
        'adj_close': 183.63,
        'volume': 54156300
    }
    success = db_service.insert_historical_price(ticker, price_data)
    if success:
        print(f"Historical price for {ticker} on {price_data['price_date']} inserted successfully")


def example_retrieve_data():
    """Example: Retrieve stored data"""
    print("\n=== Example: Retrieving Data ===")
    
    ticker = "AAPL"
    
    # Get stock data with related information
    stock_data = db_service.get_stock_data(ticker)
    if stock_data:
        print(f"Retrieved stock data for {ticker}:")
        print(f"  Locale: {stock_data.get('locale')}")
        if stock_data.get('profile'):
            print(f"  Sector: {stock_data['profile'].get('sector')}")
            print(f"  Industry: {stock_data['profile'].get('industry')}")
        if stock_data.get('latest_income_statement'):
            print(f"  Latest Revenue: ${stock_data['latest_income_statement'].get('total_revenue'):,.2f}")
        if stock_data.get('latest_balance_sheet'):
            print(f"  Latest Total Assets: ${stock_data['latest_balance_sheet'].get('total_assets'):,.2f}")
    
    # Get historical prices
    prices = db_service.get_historical_prices(ticker, frequency='1d')
    if prices:
        print(f"\nRetrieved {len(prices)} historical price records for {ticker}")
        if prices:
            latest_price = prices[-1]  # Last record is most recent due to ASC ordering
            print(f"  Latest Price Date: {latest_price.get('price_date')}")
            print(f"  Latest Close Price: ${latest_price.get('close_price'):,.2f}")
    
    # Get financial statements
    statements = db_service.get_financial_statements(ticker, 'annual')
    if statements['income_statements']:
        print(f"\nRetrieved {len(statements['income_statements'])} annual income statements for {ticker}")
    if statements['balance_sheets']:
        print(f"Retrieved {len(statements['balance_sheets'])} annual balance sheets for {ticker}")
    if statements['cash_flows']:
        print(f"Retrieved {len(statements['cash_flows'])} annual cash flows for {ticker}")


def main():
    """Main function to run examples"""
    try:
        # Initialize database connection
        print("Initializing database connection...")
        
        # Run examples
        example_store_stock_data()
        example_store_financial_statements()
        example_store_historical_prices()
        example_retrieve_data()
        
        print("\n=== All examples completed successfully! ===")
        
    except Exception as e:
        print(f"Error running examples: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Close database connection
        db_service.close_connection()
        print("Database connection closed.")


if __name__ == "__main__":
    main()