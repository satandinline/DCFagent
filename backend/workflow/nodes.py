"""
LangGraph Workflow Nodes for DCF Valuation Agent
Defines all the node functions that perform actual work in the workflow
"""
from __future__ import annotations
import asyncio
import logging
from typing import Dict, Any, Callable, Optional
from datetime import datetime
import json

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from backend.workflow.state import WorkflowState, TickerData, IndustryType, Action
from backend.services.db_service import db_service
from backend.services.industry_classifier import industry_classifier
from backend.services.valuation_engine import valuation_engine, ValuationMethod
from backend.services.email_service import email_service

logger = logging.getLogger(__name__)


# =============================================================================
# NODE FUNCTIONS - Each node performs a specific task in the workflow
# =============================================================================


def init_workflow(state: WorkflowState) -> WorkflowState:
    """
    Initialize the workflow - called at the start
    Sets up metadata and prepares state for processing
    """
    state.started_at = datetime.now().isoformat()
    state.workflow_id = f"workflow_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    state.current_step = "initialized"
    
    logger.info(f"Workflow initialized: {state.workflow_id}")
    logger.info(f"Tickers to process: {state.tickers}")
    
    # If no tickers provided, fetch from database
    if not state.tickers:
        state.tickers = _get_tickers_from_db()
        if not state.tickers:
            state.add_error("No tickers found in database. Please add stocks first.")
            state.should_continue = False
        else:
            logger.info(f"Fetched {len(state.tickers)} tickers from database")
    
    return state


def fetch_ticker_data(state: WorkflowState) -> WorkflowState:
    """
    Fetch financial data from Yahoo Finance for current ticker
    This is a key node that retrieves real-time market data
    """
    state.current_step = "fetching_data"
    
    ticker = state.get_current_ticker()
    if not ticker:
        state.add_error("No ticker to process")
        state.should_continue = False
        return state
    
    # Initialize ticker data if not exists
    if ticker not in state.ticker_data:
        state.ticker_data[ticker] = TickerData(ticker=ticker)
    
    ticker_data = state.ticker_data[ticker]
    ticker_data.status = "fetching_data"
    
    logger.info(f"Fetching data for {ticker}...")
    
    try:
        # Use synchronous approach with new event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            from backend.services.web_search_service import web_search_service
            
            result = loop.run_until_complete(
                web_search_service._search_yahoo_finance(ticker)
            )
            
            if result.get('success') and result.get('data'):
                data = result['data']
                
                # Update ticker data with fetched values
                ticker_data.company_name = data.get('company_name', ticker)
                ticker_data.sector = data.get('sector', '')
                ticker_data.industry = data.get('industry', '')
                ticker_data.market_cap = float(data.get('market_cap', 0) or 0)
                ticker_data.current_price = float(data.get('current_price', 0) or 0)
                ticker_data.revenue = float(data.get('revenue', 0) or 0)
                ticker_data.operating_income = float(data.get('operating_income', 0) or 0)
                ticker_data.total_debt = float(data.get('total_debt', 0) or 0)
                ticker_data.total_cash = float(data.get('total_cash', 0) or 0)
                ticker_data.shares_outstanding = float(data.get('shares_outstanding', 1) or 1)
                ticker_data.beta = float(data.get('beta', 1.0) or 1.0)
                ticker_data.dividend_yield = float(data.get('dividend_yield', 0) or 0)
                
                # Calculate derived fields
                ticker_data.revenue_growth = float(data.get('revenue_growth', 0) or 0)
                ticker_data.net_income = float(data.get('net_income', 0) or 0)
                ticker_data.is_profitable = ticker_data.net_income > 0
                ticker_data.has_dividends = ticker_data.dividend_yield > 0
                
                ticker_data.status = "data_fetched"
                logger.info(f"Successfully fetched data for {ticker}")
                
            else:
                ticker_data.status = "failed"
                ticker_data.error = result.get('error', 'Unknown error fetching data')
                state.add_error(f"Failed to fetch data for {ticker}: {ticker_data.error}")
                state.failed_tickers.append(ticker)
                
        finally:
            loop.close()
            
    except Exception as e:
        ticker_data.status = "failed"
        ticker_data.error = str(e)
        state.add_error(f"Exception fetching {ticker}: {str(e)}")
        state.failed_tickers.append(ticker)
        logger.error(f"Error fetching data for {ticker}: {e}")
    
    return state


def classify_industry(state: WorkflowState) -> WorkflowState:
    """
    Classify the company industry type and determine recommended valuation methods
    This node uses LLM-like logic to make decisions based on company characteristics
    """
    state.current_step = "classifying"
    
    ticker = state.get_current_ticker()
    ticker_data = state.ticker_data.get(ticker)
    
    if not ticker_data or ticker_data.status == "failed":
        state.add_warning(f"Skipping classification for failed ticker: {ticker}")
        state.next_node = "handle_failure"
        return state
    
    logger.info(f"Classifying industry for {ticker}...")
    
    try:
        # Use the industry classifier
        industry_type, valuation_rec = industry_classifier.classify(
            sector=ticker_data.sector,
            industry=ticker_data.industry,
            company_name=ticker_data.company_name,
            is_profitable=ticker_data.is_profitable,
            has_dividends=ticker_data.has_dividends,
            revenue_growth=ticker_data.revenue_growth,
            net_income=ticker_data.net_income
        )
        
        # Update ticker data with classification
        ticker_data.industry_type = IndustryType(industry_type.value)
        ticker_data.recommended_methods = [valuation_rec.primary_method] + valuation_rec.secondary_methods
        
        ticker_data.status = "classified"
        logger.info(f"{ticker}: Classified as {industry_type.value}")
        logger.info(f"Recommended methods: {ticker_data.recommended_methods}")
        
    except Exception as e:
        ticker_data.status = "failed"
        ticker_data.error = f"Classification error: {str(e)}"
        state.add_error(f"Classification failed for {ticker}: {str(e)}")
        state.failed_tickers.append(ticker)
        logger.error(f"Error classifying {ticker}: {e}")
    
    return state


def run_valuations(state: WorkflowState) -> WorkflowState:
    """
    Run valuation calculations based on recommended methods
    Can run multiple valuation methods in parallel
    """
    state.current_step = "valuating"
    
    ticker = state.get_current_ticker()
    ticker_data = state.ticker_data.get(ticker)
    
    if not ticker_data or ticker_data.status == "failed":
        state.add_warning(f"Skipping valuation for failed ticker: {ticker}")
        state.next_node = "handle_failure"
        return state
    
    logger.info(f"Running valuations for {ticker}...")
    
    try:
        # Create FinancialData from ticker_data
        from backend.models.schemas import FinancialData, DCFParameters
        
        financial_data = FinancialData(
            company_name=ticker_data.company_name,
            ticker=ticker,
            currency='USD',
            fiscal_year=datetime.now().year,
            revenue=ticker_data.revenue,
            revenue_growth=ticker_data.revenue_growth,
            operating_income=ticker_data.operating_income,
            operating_margin=0.15,  # Default
            net_income=ticker_data.net_income,
            total_debt=ticker_data.total_debt,
            cash_and_equivalents=ticker_data.total_cash,
            shares_outstanding=ticker_data.shares_outstanding,
            beta=ticker_data.beta,
            current_stock_price=ticker_data.current_price if ticker_data.current_price > 0 else None
        )
        
        # Map recommended methods to ValuationMethod enum
        method_map = {
            'DCF': ValuationMethod.DCF,
            'DDM': ValuationMethod.DDM,
            'P/S': ValuationMethod.PS,
            'P/B': ValuationMethod.PB,
            'EV/EBITDA': ValuationMethod.EV_EBITDA,
            'SOTP': ValuationMethod.SOTP,
        }
        
        # Run each recommended valuation method
        results = {}
        valid_values = []
        
        for method_name in ticker_data.recommended_methods:
            method_enum = method_map.get(method_name)
            if method_enum:
                try:
                    result = valuation_engine.evaluate(
                        financial_data,
                        methods=[method_enum]
                    )
                    
                    # Extract the valuation value from results
                    result_key = method_enum.value
                    if result.results and result_key in result.results:
                        val_result = result.results[result_key]
                        fair_value = val_result.fair_value
                        results[method_name] = fair_value
                        
                        if fair_value > 0:
                            valid_values.append(fair_value)
                        
                        logger.info(f"{ticker} - {method_name}: ${fair_value:.2f}")
                        
                except Exception as e:
                    logger.warning(f"Valuation method {method_name} failed: {e}")
        
        # Store results
        ticker_data.valuation_results = results
        
        if valid_values:
            ticker_data.fair_value = sum(valid_values) / len(valid_values)
            
            # Calculate upside
            if ticker_data.current_price > 0:
                ticker_data.upside = ((ticker_data.fair_value - ticker_data.current_price) 
                                     / ticker_data.current_price * 100)
                
                # Determine action
                if ticker_data.upside > 20:
                    ticker_data.action = Action.BUY
                elif ticker_data.upside < -10:
                    ticker_data.action = Action.SELL
                else:
                    ticker_data.action = Action.HOLD
            else:
                # No current price, default to HOLD
                ticker_data.action = Action.HOLD
        else:
            ticker_data.fair_value = 0
            ticker_data.action = Action.HOLD
        
        ticker_data.status = "valued"
        logger.info(f"{ticker}: Fair Value = ${ticker_data.fair_value:.2f}, "
                    f"Upside = {ticker_data.upside:.1f}%, Action = {ticker_data.action.value}")
        
    except Exception as e:
        ticker_data.status = "failed"
        ticker_data.error = f"Valuation error: {str(e)}"
        state.add_error(f"Valuation failed for {ticker}: {str(e)}")
        state.failed_tickers.append(ticker)
        logger.error(f"Error running valuations for {ticker}: {e}")
    
    return state


def aggregate_results(state: WorkflowState) -> WorkflowState:
    """
    Aggregate results from all tickers into portfolio recommendations
    Called after all tickers are processed
    """
    state.current_step = "aggregating"
    
    logger.info("Aggregating results into portfolio recommendations...")
    
    # Count actions
    buy_count = 0
    hold_count = 0
    sell_count = 0
    
    for ticker, data in state.ticker_data.items():
        if data.status == "valued":
            # Add to completed
            if ticker not in state.completed_tickers:
                state.completed_tickers.append(ticker)
            
            # Create recommendation dict
            recommendation = {
                'ticker': ticker,
                'company_name': data.company_name,
                'action': data.action.value,
                'upside': data.upside,
                'fair_value': data.fair_value,
                'current_price': data.current_price,
                'confidence': data.confidence,
                'industry': data.industry,
                'sector': data.sector,
                'valuation_methods': data.recommended_methods,
                'valuation_results': data.valuation_results,
                'industry_type': data.industry_type.value if data.industry_type else 'unknown',
                'reason': _generate_reason(data),
                'processed_at': datetime.now().isoformat()
            }
            
            state.recommendations.append(recommendation)
            
            # Count actions
            if data.action == Action.BUY:
                buy_count += 1
            elif data.action == Action.SELL:
                sell_count += 1
            else:
                hold_count += 1
    
    # Sort by upside (highest first)
    state.recommendations.sort(key=lambda x: x.get('upside', 0), reverse=True)
    
    # Create summary
    state.portfolio_summary = {
        'total_stocks': len(state.tickers),
        'completed': len(state.completed_tickers),
        'failed': len(state.failed_tickers),
        'action_distribution': {
            'BUY': buy_count,
            'HOLD': hold_count,
            'SELL': sell_count
        },
        'average_upside': sum(r.get('upside', 0) for r in state.recommendations) / len(state.recommendations) 
                          if state.recommendations else 0
    }
    
    state.current_step = "aggregated"
    logger.info(f"Portfolio summary: BUY={buy_count}, HOLD={hold_count}, SELL={sell_count}")
    
    return state


def send_report(state: WorkflowState) -> WorkflowState:
    """
    Send portfolio report via email
    This is an optional node that only runs if should_send_email is True
    """
    state.current_step = "sending_email"
    
    if not state.should_send_email:
        logger.info("Email sending skipped (disabled in config)")
        state.email_sent = False
        return state
    
    logger.info("Sending portfolio report email...")
    
    try:
        # Prepare email content
        portfolio_data = {
            'report_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'stocks_analyzed': len(state.completed_tickers),
            'recommendations': state.recommendations,
            'summary': state.portfolio_summary,
            'details': state.recommendations  # Same as recommendations for email
        }
        
        result = email_service.send_portfolio_report(portfolio_data)
        
        state.email_result = result
        state.email_sent = result.get('success', False)
        
        if state.email_sent:
            logger.info("Portfolio report sent successfully")
        else:
            state.add_warning(f"Failed to send email: {result.get('error', 'Unknown error')}")
            logger.warning(f"Email failed: {result.get('error')}")
            
    except Exception as e:
        state.email_sent = False
        state.email_result = {'success': False, 'error': str(e)}
        state.add_warning(f"Email exception: {str(e)}")
        logger.error(f"Error sending email: {e}")
    
    return state


def save_to_database(state: WorkflowState) -> WorkflowState:
    """
    Save all results to database for persistence
    """
    state.current_step = "saving"
    
    logger.info("Saving results to database...")
    
    try:
        for ticker, data in state.ticker_data.items():
            if data.status == "valued":
                # Save to portfolio_recommendations
                _save_recommendation(data)
                
                # Save to valuation_results
                _save_valuation_result(data)
        
        state.current_step = "saved"
        logger.info("Results saved to database")
        
    except Exception as e:
        state.add_warning(f"Database save error: {str(e)}")
        logger.error(f"Error saving to database: {e}")
    
    return state


def finish_workflow(state: WorkflowState) -> WorkflowState:
    """
    Finalize the workflow execution
    """
    state.current_step = "completed"
    state.completed_at = datetime.now().isoformat()
    state.should_continue = False
    
    logger.info(f"Workflow {state.workflow_id} completed at {state.completed_at}")
    
    return state


def handle_failure(state: WorkflowState) -> WorkflowState:
    """
    Handle failures for a ticker and continue to next
    """
    state.current_step = "handling_failure"
    
    ticker = state.get_current_ticker()
    if ticker and ticker in state.ticker_data:
        data = state.ticker_data[ticker]
        if data.status == "failed":
            state.failed_tickers.append(ticker)
    
    logger.warning(f"Handling failure for {ticker}")
    
    return state


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def _get_tickers_from_db() -> List[str]:
    """Get all tickers from the database"""
    try:
        conn = db_service.get_connection()
        with conn.cursor() as cursor:
            cursor.execute("SELECT ticker FROM stocks ORDER BY created_at DESC")
            rows = cursor.fetchall()
            return [row['ticker'] for row in rows]
    except Exception as e:
        logger.error(f"Error getting tickers from database: {e}")
        return []


def _generate_reason(data: TickerData) -> str:
    """Generate human-readable reason for recommendation"""
    methods_str = ', '.join(data.recommended_methods[:2])
    industry = data.industry or '该企业'
    
    if data.action == Action.BUY:
        return (f"基于{industry}特征，采用{methods_str}估值方法，"
                f"显示{abs(data.upside):.1f}%上涨空间，建议买入。")
    elif data.action == Action.SELL:
        return (f"基于{industry}特征，采用{methods_str}估值方法，"
                f"显示{abs(data.upside):.1f}%下跌风险，建议卖出。")
    else:
        return (f"基于{industry}特征，采用{methods_str}估值方法，"
                f"显示{data.upside:.1f}%上涨空间，建议持有。")


def _save_recommendation(data: TickerData):
    """Save recommendation to database"""
    try:
        conn = db_service.get_connection()
        with conn.cursor() as cursor:
            sql = """
                INSERT INTO portfolio_recommendations 
                (ticker, company_name, action, upside, confidence, 
                 valuation_methods, reason, industry, sector, details)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                data.ticker,
                data.company_name,
                data.action.value,
                data.upside,
                data.confidence,
                json.dumps(data.recommended_methods),
                _generate_reason(data),
                data.industry,
                data.sector,
                json.dumps(data.valuation_results)
            ))
            conn.commit()
    except Exception as e:
        logger.error(f"Error saving recommendation for {data.ticker}: {e}")


def _save_valuation_result(data: TickerData):
    """Save valuation result to database"""
    try:
        valuation_data = {
            'company_name': data.company_name,
            'fiscal_year': datetime.now().year,
            'currency': 'USD',
            'per_share_value': data.fair_value,
            'enterprise_value': 0,
            'equity_value': 0,
            'wacc_used': 0.1,
            'terminal_growth_rate': 0.025,
            'projection_years': 5,
            'current_price': data.current_price,
            'upside_downside': data.upside,
            'revenue_growth_rate': data.revenue_growth,
            'operating_margin': 0.15,
            'tax_rate': 0.25,
            'free_cash_flow': 0,
            'terminal_value': 0,
            'pv_fcf_sum': 0,
            'sensitivity_data': json.dumps({}),
            'narrative': f"LangGraph自动分析 - {data.action.value}",
            'created_by': 'LangGraph_Workflow',
            'notes': f"行业: {data.industry_type.value if data.industry_type else 'unknown'}"
        }
        db_service.insert_valuation_result(data.ticker, valuation_data)
    except Exception as e:
        logger.error(f"Error saving valuation result for {data.ticker}: {e}")


# =============================================================================
# NODE REGISTRY - Maps node names to functions
# =============================================================================

NODES: Dict[str, Callable] = {
    'init': init_workflow,
    'fetch_data': fetch_ticker_data,
    'classify': classify_industry,
    'value': run_valuations,
    'aggregate': aggregate_results,
    'save': save_to_database,
    'send_email': send_report,
    'finish': finish_workflow,
    'handle_failure': handle_failure,
}
