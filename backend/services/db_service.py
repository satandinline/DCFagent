"""
Database service for DCF Estimation system
Handles database operations for storing and retrieving financial data
"""
import pymysql
from pymysql import Error
from typing import List, Dict, Optional, Any
from datetime import date, datetime
import sys
import os

# Add the backend directory to the path so we can import config
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config import (
    MYSQL_HOST,
    MYSQL_USER, 
    MYSQL_PASSWORD,
    MYSQL_PORT,
    MYSQL_DATABASE
)


class DatabaseService:
    """Service class for database operations"""
    
    def __init__(self):
        self.connection = None
    
    def get_connection(self):
        """Get a database connection"""
        if self.connection is None or not self.connection.open:
            try:
                self.connection = pymysql.connect(
                    host=MYSQL_HOST,
                    user=MYSQL_USER,
                    password=MYSQL_PASSWORD,
                    database=MYSQL_DATABASE,
                    port=MYSQL_PORT,
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor
                )
            except Error as e:
                print(f"Error connecting to database: {e}")
                raise e
        return self.connection
    
    def close_connection(self):
        """Close the database connection"""
        if self.connection and self.connection.open:
            self.connection.close()
            self.connection = None
    
    def insert_stock(self, ticker: str, locale: str = 'US') -> bool:
        """Insert a stock into the database"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = "INSERT IGNORE INTO stocks (ticker, locale) VALUES (%s, %s)"
                cursor.execute(sql, (ticker, locale))
                conn.commit()
                return True
        except Error as e:
            print(f"Error inserting stock: {e}")
            conn.rollback()
            return False
    
    def insert_asset_profile(self, ticker: str, profile_data: Dict[str, Any]) -> bool:
        """Insert asset profile data"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO asset_profiles 
                    (ticker, sector, industry, full_time_employees, description) 
                    VALUES (%s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    sector = VALUES(sector),
                    industry = VALUES(industry),
                    full_time_employees = VALUES(full_time_employees),
                    description = VALUES(description),
                    updated_at = CURRENT_TIMESTAMP
                """
                cursor.execute(sql, (
                    ticker,
                    profile_data.get('sector'),
                    profile_data.get('industry'),
                    profile_data.get('full_time_employees'),
                    profile_data.get('description')
                ))
                conn.commit()
                return True
        except Error as e:
            print(f"Error inserting asset profile: {e}")
            conn.rollback()
            return False
    
    def insert_historical_price(self, ticker: str, price_data: Dict[str, Any]) -> bool:
        """Insert historical price data"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO historical_prices 
                    (ticker, price_date, data_frequency, open_price, high_price, low_price, 
                     close_price, adj_close, volume) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    open_price = VALUES(open_price),
                    high_price = VALUES(high_price),
                    low_price = VALUES(low_price),
                    close_price = VALUES(close_price),
                    adj_close = VALUES(adj_close),
                    volume = VALUES(volume)
                """
                cursor.execute(sql, (
                    ticker,
                    price_data['price_date'],
                    price_data['data_frequency'],
                    price_data.get('open_price'),
                    price_data.get('high_price'),
                    price_data.get('low_price'),
                    price_data.get('close_price'),
                    price_data.get('adj_close'),
                    price_data.get('volume')
                ))
                conn.commit()
                return True
        except Error as e:
            print(f"Error inserting historical price: {e}")
            conn.rollback()
            return False
    
    def insert_balance_sheet(self, ticker: str, balance_sheet_data: Dict[str, Any]) -> bool:
        """Insert balance sheet data"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO balance_sheets 
                    (ticker, report_date, report_type, total_assets, total_liabilities, 
                     total_equity, cash_and_equivalents) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    total_assets = VALUES(total_assets),
                    total_liabilities = VALUES(total_liabilities),
                    total_equity = VALUES(total_equity),
                    cash_and_equivalents = VALUES(cash_and_equivalents)
                """
                cursor.execute(sql, (
                    ticker,
                    balance_sheet_data['report_date'],
                    balance_sheet_data['report_type'],
                    balance_sheet_data.get('total_assets'),
                    balance_sheet_data.get('total_liabilities'),
                    balance_sheet_data.get('total_equity'),
                    balance_sheet_data.get('cash_and_equivalents')
                ))
                conn.commit()
                return True
        except Error as e:
            print(f"Error inserting balance sheet: {e}")
            conn.rollback()
            return False
    
    def insert_cash_flow(self, ticker: str, cash_flow_data: Dict[str, Any]) -> bool:
        """Insert cash flow data"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO cash_flows 
                    (ticker, report_date, report_type, operating_activities, investment_activities, 
                     financing_activities, changes_in_cash, overall) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    operating_activities = VALUES(operating_activities),
                    investment_activities = VALUES(investment_activities),
                    financing_activities = VALUES(financing_activities),
                    changes_in_cash = VALUES(changes_in_cash),
                    overall = VALUES(overall)
                """
                cursor.execute(sql, (
                    ticker,
                    cash_flow_data['report_date'],
                    cash_flow_data['report_type'],
                    cash_flow_data.get('operating_activities'),
                    cash_flow_data.get('investment_activities'),
                    cash_flow_data.get('financing_activities'),
                    cash_flow_data.get('changes_in_cash'),
                    cash_flow_data.get('overall')
                ))
                conn.commit()
                return True
        except Error as e:
            print(f"Error inserting cash flow: {e}")
            conn.rollback()
            return False
    
    def insert_income_statement(self, ticker: str, income_statement_data: Dict[str, Any]) -> bool:
        """Insert income statement data"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO income_statements 
                    (ticker, report_date, report_type, total_revenue, gross_profit, 
                     operating_income, net_income, ebit) 
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    total_revenue = VALUES(total_revenue),
                    gross_profit = VALUES(gross_profit),
                    operating_income = VALUES(operating_income),
                    net_income = VALUES(net_income),
                    ebit = VALUES(ebit)
                """
                cursor.execute(sql, (
                    ticker,
                    income_statement_data['report_date'],
                    income_statement_data['report_type'],
                    income_statement_data.get('total_revenue'),
                    income_statement_data.get('gross_profit'),
                    income_statement_data.get('operating_income'),
                    income_statement_data.get('net_income'),
                    income_statement_data.get('ebit')
                ))
                conn.commit()
                return True
        except Error as e:
            print(f"Error inserting income statement: {e}")
            conn.rollback()
            return False
    
    def get_stock_data(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Retrieve stock data by ticker"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                # Get basic stock info
                cursor.execute("SELECT * FROM stocks WHERE ticker = %s", (ticker,))
                stock = cursor.fetchone()
                
                if stock:
                    # Get asset profile
                    cursor.execute("SELECT * FROM asset_profiles WHERE ticker = %s", (ticker,))
                    stock['profile'] = cursor.fetchone()
                    
                    # Get latest financial statements
                    cursor.execute("""
                        SELECT * FROM income_statements 
                        WHERE ticker = %s AND report_type = 'annual' 
                        ORDER BY report_date DESC LIMIT 1
                    """, (ticker,))
                    stock['latest_income_statement'] = cursor.fetchone()
                    
                    cursor.execute("""
                        SELECT * FROM balance_sheets 
                        WHERE ticker = %s AND report_type = 'annual' 
                        ORDER BY report_date DESC LIMIT 1
                    """, (ticker,))
                    stock['latest_balance_sheet'] = cursor.fetchone()
                    
                    cursor.execute("""
                        SELECT * FROM cash_flows 
                        WHERE ticker = %s AND report_type = 'annual' 
                        ORDER BY report_date DESC LIMIT 1
                    """, (ticker,))
                    stock['latest_cash_flow'] = cursor.fetchone()
                    
                return stock
        except Error as e:
            print(f"Error retrieving stock data: {e}")
            return None
    
    def get_historical_prices(self, ticker: str, start_date: Optional[date] = None, 
                             end_date: Optional[date] = None, 
                             frequency: str = '1d') -> List[Dict[str, Any]]:
        """Retrieve historical prices for a stock"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                query = "SELECT * FROM historical_prices WHERE ticker = %s AND data_frequency = %s"
                params = [ticker, frequency]
                
                if start_date:
                    query += " AND price_date >= %s"
                    params.append(start_date)
                
                if end_date:
                    query += " AND price_date <= %s"
                    params.append(end_date)
                
                query += " ORDER BY price_date ASC"
                
                cursor.execute(query, params)
                return cursor.fetchall()
        except Error as e:
            print(f"Error retrieving historical prices: {e}")
            return []
    
    def get_financial_statements(self, ticker: str, report_type: str = 'annual') -> Dict[str, List[Dict[str, Any]]]:
        """Retrieve all financial statements for a stock"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                # Get income statements
                cursor.execute("""
                    SELECT * FROM income_statements 
                    WHERE ticker = %s AND report_type = %s 
                    ORDER BY report_date DESC
                """, (ticker, report_type))
                income_statements = cursor.fetchall()
                
                # Get balance sheets
                cursor.execute("""
                    SELECT * FROM balance_sheets 
                    WHERE ticker = %s AND report_type = %s 
                    ORDER BY report_date DESC
                """, (ticker, report_type))
                balance_sheets = cursor.fetchall()
                
                # Get cash flows
                cursor.execute("""
                    SELECT * FROM cash_flows 
                    WHERE ticker = %s AND report_type = %s 
                    ORDER BY report_date DESC
                """, (ticker, report_type))
                cash_flows = cursor.fetchall()
                
                return {
                    'income_statements': income_statements,
                    'balance_sheets': balance_sheets,
                    'cash_flows': cash_flows
                }
        except Error as e:
            print(f"Error retrieving financial statements: {e}")
            return {
                'income_statements': [],
                'balance_sheets': [],
                'cash_flows': []
            }
    
    def insert_valuation_result(self, ticker: str, valuation_data: Dict[str, Any]) -> bool:
        """Insert DCF valuation result"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                # 先确保 ticker 存在于 stocks 表中（避免外键约束失败）
                company_name = valuation_data.get('company_name', '')
                currency = valuation_data.get('currency', 'CNY')
                cursor.execute(
                    "INSERT IGNORE INTO stocks (ticker, company_name, locale) VALUES (%s, %s, %s)",
                    (ticker, company_name, 'CN' if currency == 'CNY' else 'US')
                )
                
                sql = """
                    INSERT INTO valuation_results 
                    (ticker, company_name, fiscal_year, currency, per_share_value,
                     enterprise_value, equity_value, wacc_used, terminal_growth_rate,
                     projection_years, current_price, upside_downside, revenue_growth_rate,
                     operating_margin, tax_rate, free_cash_flow, terminal_value,
                     pv_fcf_sum, sensitivity_data, narrative, created_by, notes)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    ticker,
                    company_name,
                    valuation_data.get('fiscal_year'),
                    currency,
                    valuation_data.get('per_share_value'),
                    valuation_data.get('enterprise_value'),
                    valuation_data.get('equity_value'),
                    valuation_data.get('wacc_used'),
                    valuation_data.get('terminal_growth_rate'),
                    valuation_data.get('projection_years'),
                    valuation_data.get('current_price'),
                    valuation_data.get('upside_downside'),
                    valuation_data.get('revenue_growth_rate'),
                    valuation_data.get('operating_margin'),
                    valuation_data.get('tax_rate'),
                    valuation_data.get('free_cash_flow'),
                    valuation_data.get('terminal_value'),
                    valuation_data.get('pv_fcf_sum'),
                    valuation_data.get('sensitivity_data'),  # JSON string
                    valuation_data.get('narrative'),
                    valuation_data.get('created_by'),
                    valuation_data.get('notes')
                ))
                conn.commit()
                return True
        except Error as e:
            print(f"Error inserting valuation result: {e}")
            conn.rollback()
            return False
    
    def get_valuation_history(self, ticker: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Retrieve valuation history for a stock"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM valuation_results 
                    WHERE ticker = %s 
                    ORDER BY valuation_date DESC 
                    LIMIT %s
                """, (ticker, limit))
                return cursor.fetchall()
        except Error as e:
            print(f"Error retrieving valuation history: {e}")
            return []
    
    def get_all_valuation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve all valuation history across all stocks"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM valuation_results 
                    ORDER BY valuation_date DESC 
                    LIMIT %s
                """, (limit,))
                return cursor.fetchall()
        except Error as e:
            print(f"Error retrieving all valuation history: {e}")
            return []
    
    def get_latest_valuation(self, ticker: str) -> Optional[Dict[str, Any]]:
        """Get the most recent valuation for a stock"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM valuation_results 
                    WHERE ticker = %s 
                    ORDER BY valuation_date DESC 
                    LIMIT 1
                """, (ticker,))
                return cursor.fetchone()
        except Error as e:
            print(f"Error retrieving latest valuation: {e}")
            return None
    
    def get_valuation_by_id(self, valuation_id: int) -> Optional[Dict[str, Any]]:
        """Get a specific valuation by ID"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM valuation_results 
                    WHERE id = %s
                """, (valuation_id,))
                return cursor.fetchone()
        except Error as e:
            print(f"Error retrieving valuation by id: {e}")
            return None
    
    def calculate_growth_trends(self, ticker: str) -> Dict[str, Any]:
        """Calculate growth trends from historical financial data"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                # Get revenue trend
                cursor.execute("""
                    SELECT report_date, total_revenue 
                    FROM income_statements 
                    WHERE ticker = %s AND report_type = 'annual' 
                    AND total_revenue IS NOT NULL AND total_revenue > 0
                    ORDER BY report_date ASC
                """, (ticker,))
                revenues = cursor.fetchall()
                
                # Get net income trend
                cursor.execute("""
                    SELECT report_date, net_income 
                    FROM income_statements 
                    WHERE ticker = %s AND report_type = 'annual' 
                    AND net_income IS NOT NULL
                    ORDER BY report_date ASC
                """, (ticker,))
                incomes = cursor.fetchall()
                
                # Get operating cash flow trend
                cursor.execute("""
                    SELECT report_date, operating_activities 
                    FROM cash_flows 
                    WHERE ticker = %s AND report_type = 'annual' 
                    AND operating_activities IS NOT NULL
                    ORDER BY report_date ASC
                """, (ticker,))
                cashflows = cursor.fetchall()
                
                trends = {
                    'revenue_trend': [],
                    'income_trend': [],
                    'cashflow_trend': [],
                    'revenue_cagr': None,
                    'income_cagr': None,
                    'avg_operating_margin': None,
                    'avg_net_margin': None
                }
                
                # Calculate revenue CAGR
                if len(revenues) >= 2:
                    for r in revenues:
                        trends['revenue_trend'].append({
                            'date': str(r['report_date']),
                            'value': float(r['total_revenue'])
                        })
                    
                    oldest = float(revenues[0]['total_revenue'])
                    newest = float(revenues[-1]['total_revenue'])
                    years = len(revenues) - 1
                    if oldest > 0 and years > 0:
                        trends['revenue_cagr'] = ((newest / oldest) ** (1/years) - 1)
                
                # Calculate income CAGR
                if len(incomes) >= 2:
                    for inc in incomes:
                        trends['income_trend'].append({
                            'date': str(inc['report_date']),
                            'value': float(inc['net_income'])
                        })
                    
                    oldest_inc = float(incomes[0]['net_income'])
                    newest_inc = float(incomes[-1]['net_income'])
                    years = len(incomes) - 1
                    if oldest_inc != 0 and years > 0:
                        if oldest_inc > 0 and newest_inc > 0:
                            trends['income_cagr'] = ((newest_inc / oldest_inc) ** (1/years) - 1)
                
                # Cash flow trend
                if cashflows:
                    for cf in cashflows:
                        trends['cashflow_trend'].append({
                            'date': str(cf['report_date']),
                            'value': float(cf['operating_activities'])
                        })
                
                # Calculate average margins
                if revenues and incomes:
                    margins_op = []
                    margins_net = []
                    for i, rev in enumerate(revenues):
                        if i < len(incomes):
                            rev_val = float(rev['total_revenue'])
                            inc_val = float(incomes[i]['net_income'])
                            if rev_val > 0:
                                # Get operating income for this year
                                cursor.execute("""
                                    SELECT operating_income FROM income_statements
                                    WHERE ticker = %s AND report_date = %s AND report_type = 'annual'
                                """, (ticker, rev['report_date']))
                                op_inc_row = cursor.fetchone()
                                if op_inc_row and op_inc_row['operating_income']:
                                    op_inc_val = float(op_inc_row['operating_income'])
                                    margins_op.append(op_inc_val / rev_val)
                                margins_net.append(inc_val / rev_val)
                    
                    if margins_op:
                        trends['avg_operating_margin'] = sum(margins_op) / len(margins_op)
                    if margins_net:
                        trends['avg_net_margin'] = sum(margins_net) / len(margins_net)
                
                return trends
                
        except Error as e:
            print(f"Error calculating growth trends: {e}")
            return {
                'revenue_trend': [],
                'income_trend': [],
                'cashflow_trend': [],
                'revenue_cagr': None,
                'income_cagr': None,
                'avg_operating_margin': None,
                'avg_net_margin': None
            }


# Global instance for easy access
db_service = DatabaseService()