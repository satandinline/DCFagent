"""
Database initialization script for DCF Estimation system
Creates MySQL database and tables for storing historical financial data
"""
import pymysql
from pymysql import Error
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


def create_connection():
    """Create a database connection"""
    try:
        connection = pymysql.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            port=MYSQL_PORT,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None


def create_database(connection):
    """Create the database if it doesn't exist"""
    try:
        cursor = connection.cursor()
        cursor.execute(f"CREATE DATABASE IF NOT EXISTS {MYSQL_DATABASE} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        cursor.close()
        print(f"Database '{MYSQL_DATABASE}' created or already exists")
    except Error as e:
        print(f"Error creating database: {e}")


def get_db_connection():
    """Get connection to the specific database"""
    try:
        connection = pymysql.connect(
            host=MYSQL_HOST,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DATABASE,
            port=MYSQL_PORT,
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
        return connection
    except Error as e:
        print(f"Error connecting to database {MYSQL_DATABASE}: {e}")
        return None


def create_tables(connection):
    """Create all required tables"""
    try:
        cursor = connection.cursor()
        
        # 1. Stocks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stocks (
                ticker VARCHAR(10) PRIMARY KEY,
                locale VARCHAR(2) DEFAULT 'US',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # 2. Asset Profile table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS asset_profiles (
                ticker VARCHAR(10) PRIMARY KEY,
                sector VARCHAR(100),
                industry VARCHAR(100),
                full_time_employees INT,
                description TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (ticker) REFERENCES stocks(ticker) ON DELETE CASCADE
            )
        """)
        
        # 3. Historical Prices table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS historical_prices (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(10),
                price_date DATE NOT NULL,
                data_frequency VARCHAR(3) NOT NULL,
                open_price DECIMAL(15, 4),
                high_price DECIMAL(15, 4),
                low_price DECIMAL(15, 4),
                close_price DECIMAL(15, 4),
                adj_close DECIMAL(15, 4),
                volume BIGINT,
                UNIQUE KEY unique_ticker_date_freq (ticker, price_date, data_frequency),
                FOREIGN KEY (ticker) REFERENCES stocks(ticker) ON DELETE CASCADE
            )
        """)
        
        # 4. Balance Sheet table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS balance_sheets (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(10),
                report_date DATE NOT NULL,
                report_type ENUM('annual', 'quarterly') NOT NULL,
                total_assets DECIMAL(20, 4),
                total_liabilities DECIMAL(20, 4),
                total_equity DECIMAL(20, 4),
                cash_and_equivalents DECIMAL(20, 4),
                UNIQUE KEY unique_ticker_report (ticker, report_date, report_type),
                FOREIGN KEY (ticker) REFERENCES stocks(ticker) ON DELETE CASCADE
            )
        """)
        
        # 5. Cash Flow table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS cash_flows (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(10),
                report_date DATE NOT NULL,
                report_type ENUM('annual', 'quarterly') NOT NULL,
                operating_activities DECIMAL(20, 4),
                investment_activities DECIMAL(20, 4),
                financing_activities DECIMAL(20, 4),
                changes_in_cash DECIMAL(20, 4),
                overall DECIMAL(20, 4),
                UNIQUE KEY unique_ticker_report (ticker, report_date, report_type),
                FOREIGN KEY (ticker) REFERENCES stocks(ticker) ON DELETE CASCADE
            )
        """)
        
        # 6. Income Statement table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS income_statements (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(10),
                report_date DATE NOT NULL,
                report_type ENUM('annual', 'quarterly') NOT NULL,
                total_revenue DECIMAL(20, 4),
                gross_profit DECIMAL(20, 4),
                operating_income DECIMAL(20, 4),
                net_income DECIMAL(20, 4),
                ebit DECIMAL(20, 4),
                UNIQUE KEY unique_ticker_report (ticker, report_date, report_type),
                FOREIGN KEY (ticker) REFERENCES stocks(ticker) ON DELETE CASCADE
            )
        """)
        
        # 7. Valuation Results table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS valuation_results (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(10),
                valuation_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                company_name VARCHAR(200),
                fiscal_year INT,
                currency VARCHAR(10) DEFAULT 'CNY',
                per_share_value DECIMAL(20, 4),
                enterprise_value DECIMAL(20, 4),
                equity_value DECIMAL(20, 4),
                wacc_used DECIMAL(10, 6),
                terminal_growth_rate DECIMAL(10, 6),
                projection_years INT,
                current_price DECIMAL(20, 4),
                upside_downside DECIMAL(10, 4),
                revenue_growth_rate DECIMAL(10, 6),
                operating_margin DECIMAL(10, 6),
                tax_rate DECIMAL(10, 6),
                free_cash_flow DECIMAL(20, 4),
                terminal_value DECIMAL(20, 4),
                pv_fcf_sum DECIMAL(20, 4),
                sensitivity_data TEXT,
                narrative TEXT,
                created_by VARCHAR(100),
                notes TEXT,
                FOREIGN KEY (ticker) REFERENCES stocks(ticker) ON DELETE CASCADE,
                INDEX idx_valuation_date (valuation_date),
                INDEX idx_ticker_date (ticker, valuation_date)
            )
        """)
        
        # 8. Agent Configs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_configs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(10),
                enabled BOOLEAN DEFAULT TRUE,
                custom_interval_hours INT,
                last_run TIMESTAMP NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                FOREIGN KEY (ticker) REFERENCES stocks(ticker) ON DELETE CASCADE
            )
        """)
        
        # 9. Portfolio Recommendations table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS portfolio_recommendations (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(10),
                company_name VARCHAR(200),
                action ENUM('BUY', 'HOLD', 'SELL') NOT NULL,
                upside DECIMAL(10, 4),
                confidence ENUM('HIGH', 'MEDIUM', 'LOW') DEFAULT 'MEDIUM',
                valuation_methods TEXT,
                reason TEXT,
                industry VARCHAR(100),
                sector VARCHAR(100),
                details TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_ticker_action (ticker, action),
                INDEX idx_created_at (created_at)
            )
        """)
        
        # 10. Agent Logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS agent_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                action VARCHAR(50) NOT NULL,
                ticker VARCHAR(10),
                status ENUM('SUCCESS', 'FAILED', 'RUNNING') DEFAULT 'SUCCESS',
                message TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_action_ticker (action, ticker),
                INDEX idx_created_at (created_at)
            )
        """)
        
        # 11. Data Fetch Logs table - Track data fetch operations
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS data_fetch_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                ticker VARCHAR(10),
                fetch_type ENUM('scheduled', 'manual', 'incremental') NOT NULL,
                fetch_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                data_found BOOLEAN DEFAULT FALSE,
                new_data_available BOOLEAN DEFAULT FALSE,
                records_fetched INT DEFAULT 0,
                analysis_triggered BOOLEAN DEFAULT FALSE,
                report_sent BOOLEAN DEFAULT FALSE,
                error_message TEXT,
                details TEXT,
                fetched_data_summary TEXT,
                fetched_data_snapshot TEXT,
                INDEX idx_ticker_fetch (ticker, fetch_date),
                INDEX idx_fetch_type_date (fetch_type, fetch_date),
                INDEX idx_new_data (new_data_available, fetch_date)
            )
        """)
        
        # 12. Scheduled Tasks Config table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks_config (
                id INT AUTO_INCREMENT PRIMARY KEY,
                task_name VARCHAR(50) UNIQUE NOT NULL,
                enabled BOOLEAN DEFAULT TRUE,
                cron_expression VARCHAR(100),
                last_run TIMESTAMP NULL,
                next_run TIMESTAMP NULL,
                run_count INT DEFAULT 0,
                success_count INT DEFAULT 0,
                failure_count INT DEFAULT 0,
                config JSON,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            )
        """)
        
        connection.commit()
        cursor.close()
        print("All tables created successfully")
        
    except Error as e:
        print(f"Error creating tables: {e}")
        connection.rollback()


def main():
    """Main function to initialize the database"""
    print("Starting database initialization...")
    
    # Create connection to MySQL server
    conn = create_connection()
    if not conn:
        print("Failed to connect to MySQL server")
        return False
    
    try:
        # Create database
        create_database(conn)
        
        # Close initial connection
        conn.close()
        
        # Connect to the specific database
        db_conn = get_db_connection()
        if not db_conn:
            print(f"Failed to connect to database {MYSQL_DATABASE}")
            return False
        
        # Create tables
        create_tables(db_conn)
        
        # Close database connection
        db_conn.close()
        
        print("Database initialization completed successfully!")
        return True
        
    except Exception as e:
        print(f"Error during database initialization: {e}")
        if 'conn' in locals():
            conn.close()
        if 'db_conn' in locals():
            db_conn.close()
        return False


if __name__ == "__main__":
    success = main()
    if success:
        print("Database setup completed successfully!")
    else:
        print("Database setup failed!")
        sys.exit(1)