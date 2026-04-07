"""
Database service for DCF Estimation system
Handles database operations for storing and retrieving financial data
"""
import pymysql
from pymysql import Error
from typing import List, Dict, Optional, Any
from datetime import date, datetime
import json
import sys
import os
import logging
import time
from functools import wraps

# Add the backend directory to the path so we can import config
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from config import (
    MYSQL_HOST,
    MYSQL_USER, 
    MYSQL_PASSWORD,
    MYSQL_PORT,
    MYSQL_DATABASE
)

from backend.exceptions import (
    DatabaseConnectionError,
    DatabaseQueryError,
    DatabaseTimeoutError,
    DatabaseException
)

logger = logging.getLogger(__name__)


def with_retry(max_attempts: int = 3, delay: float = 0.5, backoff: float = 2.0):
    """
    Decorator for database operations with automatic retry on connection errors.
    
    Args:
        max_attempts: Maximum number of retry attempts
        delay: Initial delay between retries (seconds)
        backoff: Multiplier for delay after each attempt
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            current_delay = delay
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except (pymysql.OperationalError, pymysql.InterfaceError) as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            f"Database operation {func.__name__} failed after "
                            f"{max_attempts} attempts: {e}"
                        )
                        raise DatabaseConnectionError(
                            message=f"Database operation failed after {max_attempts} attempts",
                            cause=e
                        )
                    
                    logger.warning(
                        f"Database connection error on attempt {attempt}/{max_attempts} "
                        f"for {func.__name__}: {e}. Retrying in {current_delay}s..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
                    
                except Exception as e:
                    # Don't retry other exceptions
                    logger.error(f"Database operation {func.__name__} failed: {e}")
                    raise DatabaseQueryError(
                        message=f"Database operation failed: {str(e)}",
                        cause=e
                    )
            
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


class DatabaseService:
    """Service class for database operations"""
    
    def __init__(self):
        self.connection = None
    
    def get_connection(self):
        """Get a database connection with retry mechanism"""
        if self.connection is None or not self.connection.open:
            try:
                self.connection = pymysql.connect(
                    host=MYSQL_HOST,
                    user=MYSQL_USER,
                    password=MYSQL_PASSWORD,
                    database=MYSQL_DATABASE,
                    port=MYSQL_PORT,
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor,
                    connect_timeout=10,
                    read_timeout=30,
                    write_timeout=30
                )
                logger.info("Successfully connected to database")
            except Error as e:
                logger.error(f"Error connecting to database: {e}")
                raise DatabaseConnectionError(
                    message=f"Failed to connect to database: {str(e)}",
                    details={
                        "host": MYSQL_HOST,
                        "database": MYSQL_DATABASE,
                        "port": MYSQL_PORT
                    },
                    cause=e
                )
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
            logger.error(f"Error inserting stock: {e}")
            conn.rollback()
            raise DatabaseQueryError(
                message=f"Failed to insert stock {ticker}: {str(e)}",
                ticker=ticker,
                cause=e
            )
    
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
            logger.error(f"Error inserting asset profile for {ticker}: {e}")
            conn.rollback()
            raise DatabaseQueryError(
                message=f"Failed to insert asset profile: {str(e)}",
                ticker=ticker,
                cause=e
            )
    
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
            logger.error(f"Error inserting historical price for {ticker}: {e}")
            conn.rollback()
            raise DatabaseQueryError(
                message=f"Failed to insert historical price: {str(e)}",
                ticker=ticker,
                cause=e
            )
    
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
            logger.error(f"Error inserting balance sheet for {ticker}: {e}")
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
            logger.error(f"Error inserting cash flow for {ticker}: {e}")
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
            logger.error(f"Error inserting income statement for {ticker}: {e}")
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
            logger.error(f"Error retrieving stock data for {ticker}: {e}")
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
            logger.error(f"Error retrieving historical prices for {ticker}: {e}")
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
            logger.error(f"Error retrieving financial statements for {ticker}: {e}")
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
            logger.error(f"Error inserting valuation result for {ticker}: {e}")
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
            logger.error(f"Error retrieving valuation history for {ticker}: {e}")
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
            logger.error(f"Error retrieving all valuation history: {e}")
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
            logger.error(f"Error retrieving latest valuation for {ticker}: {e}")
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
            logger.error(f"Error retrieving valuation by id {valuation_id}: {e}")
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
            logger.error(f"Error calculating growth trends for {ticker}: {e}")
            return {
                'revenue_trend': [],
                'income_trend': [],
                'cashflow_trend': [],
                'revenue_cagr': None,
                'income_cagr': None,
                'avg_operating_margin': None,
                'avg_net_margin': None
            }
    
    # =========================================================================
    # Data Fetch Logs Methods
    # =========================================================================
    
    def insert_data_fetch_log(
        self,
        ticker: str,
        fetch_type: str,
        data_found: bool,
        new_data_available: bool,
        records_fetched: int = 0,
        analysis_triggered: bool = False,
        report_sent: bool = False,
        error_message: str = None,
        details: str = None,
        fetched_data_summary: str = None,
        fetched_data_snapshot: str = None
    ) -> Optional[int]:
        """Insert a data fetch log entry and return the ID"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO data_fetch_logs 
                    (ticker, fetch_type, data_found, new_data_available, records_fetched,
                     analysis_triggered, report_sent, error_message, details,
                     fetched_data_summary, fetched_data_snapshot)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(sql, (
                    ticker,
                    fetch_type,
                    data_found,
                    new_data_available,
                    records_fetched,
                    analysis_triggered,
                    report_sent,
                    error_message,
                    details,
                    fetched_data_summary,
                    fetched_data_snapshot
                ))
                conn.commit()
                return cursor.lastrowid
        except Error as e:
            logger.error(f"Error inserting data fetch log for {ticker}: {e}")
            conn.rollback()
            return None
    
    def update_data_fetch_log(
        self,
        log_id: int,
        analysis_triggered: bool = None,
        report_sent: bool = None,
        error_message: str = None,
        fetched_data_summary: str = None,
        fetched_data_snapshot: str = None,
        new_data_available: bool = None,
        records_fetched: int = None
    ) -> bool:
        """Update a data fetch log entry"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                updates = []
                params = []
                
                if analysis_triggered is not None:
                    updates.append("analysis_triggered = %s")
                    params.append(analysis_triggered)
                
                if report_sent is not None:
                    updates.append("report_sent = %s")
                    params.append(report_sent)
                
                if error_message is not None:
                    updates.append("error_message = %s")
                    params.append(error_message)
                
                if fetched_data_summary is not None:
                    updates.append("fetched_data_summary = %s")
                    params.append(fetched_data_summary)
                
                if fetched_data_snapshot is not None:
                    updates.append("fetched_data_snapshot = %s")
                    params.append(fetched_data_snapshot)
                
                if new_data_available is not None:
                    updates.append("new_data_available = %s")
                    params.append(new_data_available)
                
                if records_fetched is not None:
                    updates.append("records_fetched = %s")
                    params.append(records_fetched)
                
                if not updates:
                    return True
                
                params.append(log_id)
                sql = f"UPDATE data_fetch_logs SET {', '.join(updates)} WHERE id = %s"
                cursor.execute(sql, params)
                conn.commit()
                return True
        except Error as e:
            logger.error(f"Error updating data fetch log {log_id}: {e}")
            conn.rollback()
            return False
    
    def get_last_fetch_date(self, ticker: str) -> Optional[datetime]:
        """Get the last fetch date for a ticker"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT fetch_date FROM data_fetch_logs
                    WHERE ticker = %s AND data_found = TRUE
                    ORDER BY fetch_date DESC
                    LIMIT 1
                """, (ticker,))
                result = cursor.fetchone()
                return result['fetch_date'] if result else None
        except Error as e:
            logger.error(f"Error getting last fetch date for {ticker}: {e}")
            return None
    
    def has_new_data_since(self, ticker: str, since_date: datetime) -> bool:
        """Check if there's new data for a ticker since a given date"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                since_dt = since_date.date() if hasattr(since_date, 'date') else since_date
                
                # Check income statements for newer reports
                cursor.execute("""
                    SELECT COUNT(*) as cnt FROM income_statements
                    WHERE ticker = %s AND report_date > %s
                """, (ticker, since_dt))
                inc_count = cursor.fetchone()['cnt']
                
                # Check historical prices for newer prices (last 1-2 days)
                cursor.execute("""
                    SELECT COUNT(*) as cnt FROM historical_prices
                    WHERE ticker = %s AND price_date > %s
                """, (ticker, since_dt))
                price_count = cursor.fetchone()['cnt']
                
                return inc_count > 0 or price_count > 0
        except Error as e:
            logger.error(f"Error checking for new data for {ticker}: {e}")
            return False
    
    def get_latest_data_snapshot(self, ticker: str) -> Dict[str, Any]:
        """Get the latest data snapshot for a ticker"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                # Get latest income statement
                cursor.execute("""
                    SELECT * FROM income_statements 
                    WHERE ticker = %s AND report_type = 'annual'
                    ORDER BY report_date DESC LIMIT 1
                """, (ticker,))
                income = cursor.fetchone()
                
                # Get latest balance sheet
                cursor.execute("""
                    SELECT * FROM balance_sheets 
                    WHERE ticker = %s AND report_type = 'annual'
                    ORDER BY report_date DESC LIMIT 1
                """, (ticker,))
                balance = cursor.fetchone()
                
                # Get latest cash flow
                cursor.execute("""
                    SELECT * FROM cash_flows 
                    WHERE ticker = %s AND report_type = 'annual'
                    ORDER BY report_date DESC LIMIT 1
                """, (ticker,))
                cashflow = cursor.fetchone()
                
                # Get latest historical price
                cursor.execute("""
                    SELECT * FROM historical_prices 
                    WHERE ticker = %s
                    ORDER BY price_date DESC LIMIT 1
                """, (ticker,))
                price = cursor.fetchone()
                
                return {
                    'income_statement': income,
                    'balance_sheet': balance,
                    'cash_flow': cashflow,
                    'latest_price': price
                }
        except Error as e:
            logger.error(f"Error getting data snapshot for {ticker}: {e}")
            return {}
    
    def get_data_changes_since(self, ticker: str, since_date: datetime) -> Dict[str, Any]:
        """Get detailed changes in data since a given date"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                since_dt = since_date.date() if hasattr(since_date, 'date') else since_date
                
                # Get new income statements
                cursor.execute("""
                    SELECT * FROM income_statements 
                    WHERE ticker = %s AND report_date > %s
                    ORDER BY report_date DESC
                """, (ticker, since_dt))
                new_income = cursor.fetchall()
                
                # Get new balance sheets
                cursor.execute("""
                    SELECT * FROM balance_sheets 
                    WHERE ticker = %s AND report_date > %s
                    ORDER BY report_date DESC
                """, (ticker, since_dt))
                new_balance = cursor.fetchall()
                
                # Get new cash flows
                cursor.execute("""
                    SELECT * FROM cash_flows 
                    WHERE ticker = %s AND report_date > %s
                    ORDER BY report_date DESC
                """, (ticker, since_dt))
                new_cashflow = cursor.fetchall()
                
                # Get new historical prices
                cursor.execute("""
                    SELECT COUNT(*) as cnt, MAX(price_date) as max_date 
                    FROM historical_prices 
                    WHERE ticker = %s AND price_date > %s
                """, (ticker, since_dt))
                price_info = cursor.fetchone()
                
                return {
                    'has_changes': (len(new_income) > 0 or len(new_balance) > 0 or 
                                   len(new_cashflow) > 0 or (price_info['cnt'] or 0) > 0),
                    'new_income_statements': new_income,
                    'new_balance_sheets': new_balance,
                    'new_cash_flows': new_cashflow,
                    'new_prices_count': price_info['cnt'] or 0,
                    'new_prices_latest': price_info['max_date']
                }
        except Error as e:
            logger.error(f"Error getting data changes for {ticker}: {e}")
            return {'has_changes': False}
    
    def get_all_tickers(self) -> List[str]:
        """Get all tickers from the database"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT ticker FROM stocks ORDER BY ticker")
                results = cursor.fetchall()
                return [r['ticker'] for r in results]
        except Error as e:
            logger.error(f"Error getting tickers: {e}")
            return []
    
    def get_data_fetch_summary(self, days: int = 7) -> Dict[str, Any]:
        """Get summary of data fetch operations"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        COUNT(*) as total_fetches,
                        SUM(CASE WHEN data_found = TRUE THEN 1 ELSE 0 END) as fetches_with_data,
                        SUM(CASE WHEN new_data_available = TRUE THEN 1 ELSE 0 END) as fetches_with_new_data,
                        SUM(CASE WHEN analysis_triggered = TRUE THEN 1 ELSE 0 END) as analyses_triggered,
                        SUM(CASE WHEN report_sent = TRUE THEN 1 ELSE 0 END) as reports_sent
                    FROM data_fetch_logs
                    WHERE fetch_date >= DATE_SUB(NOW(), INTERVAL %s DAY)
                """, (days,))
                result = cursor.fetchone()
                
                cursor.execute("""
                    SELECT ticker, MAX(fetch_date) as last_fetch, 
                           SUM(CASE WHEN new_data_available = TRUE THEN 1 ELSE 0 END) as new_data_count
                    FROM data_fetch_logs
                    WHERE fetch_date >= DATE_SUB(NOW(), INTERVAL %s DAY)
                    GROUP BY ticker
                    ORDER BY last_fetch DESC
                """, (days,))
                ticker_stats = cursor.fetchall()
                
                return {
                    'period_days': days,
                    'total_fetches': result['total_fetches'] or 0,
                    'fetches_with_data': result['fetches_with_data'] or 0,
                    'fetches_with_new_data': result['fetches_with_new_data'] or 0,
                    'analyses_triggered': result['analyses_triggered'] or 0,
                    'reports_sent': result['reports_sent'] or 0,
                    'ticker_stats': [
                        {
                            'ticker': t['ticker'],
                            'last_fetch': str(t['last_fetch']) if t['last_fetch'] else None,
                            'new_data_count': t['new_data_count'] or 0
                        }
                        for t in ticker_stats
                    ]
                }
        except Error as e:
            logger.error(f"Error getting data fetch summary: {e}")
            return {}
    
    # =========================================================================
    # Scheduled Tasks Config Methods
    # =========================================================================
    
    def get_scheduled_task_config(self, task_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a scheduled task"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM scheduled_tasks_config WHERE task_name = %s
                """, (task_name,))
                return cursor.fetchone()
        except Error as e:
            logger.error(f"Error getting scheduled task config for {task_name}: {e}")
            return None
    
    def upsert_scheduled_task_config(
        self,
        task_name: str,
        enabled: bool = True,
        cron_expression: str = None,
        config: dict = None
    ) -> bool:
        """Insert or update a scheduled task configuration"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                    INSERT INTO scheduled_tasks_config (task_name, enabled, cron_expression, config)
                    VALUES (%s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                    enabled = VALUES(enabled),
                    cron_expression = VALUES(cron_expression),
                    config = VALUES(config),
                    updated_at = CURRENT_TIMESTAMP
                """
                cursor.execute(sql, (
                    task_name,
                    enabled,
                    cron_expression,
                    json.dumps(config) if config else None
                ))
                conn.commit()
                return True
        except Error as e:
            logger.error(f"Error upserting scheduled task config for {task_name}: {e}")
            conn.rollback()
            return False
    
    def update_task_run_stats(
        self,
        task_name: str,
        success: bool,
        next_run: datetime = None
    ) -> bool:
        """Update run statistics for a scheduled task"""
        conn = self.get_connection()
        try:
            with conn.cursor() as cursor:
                sql = """
                    UPDATE scheduled_tasks_config SET
                    last_run = CURRENT_TIMESTAMP,
                    run_count = run_count + 1,
                    success_count = success_count + %s,
                    failure_count = failure_count + %s,
                    next_run = %s,
                    updated_at = CURRENT_TIMESTAMP
                    WHERE task_name = %s
                """
                cursor.execute(sql, (
                    1 if success else 0,
                    0 if success else 1,
                    next_run,
                    task_name
                ))
                conn.commit()
                return True
        except Error as e:
            logger.error(f"Error updating task run stats for {task_name}: {e}")
            return False


# Global instance for easy access
db_service = DatabaseService()