from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from backend.models.schemas import ExtractionResponse, FinancialData
from backend.services.llm_service import LLMService
from backend.services.db_service import db_service
from backend.services.rag_service import rag_service

logger = logging.getLogger(__name__)


def _safe_float(raw: dict, key: str, default: float = 0.0) -> float:
    val = raw.get(key, default)
    try:
        return float(val) if val is not None else default
    except (TypeError, ValueError):
        return default


def _safe_int(raw: dict, key: str, default: int = 2025) -> int:
    val = raw.get(key, default)
    try:
        return int(val) if val is not None else default
    except (TypeError, ValueError):
        return default


async def extract_from_text(
    text: str, 
    save_to_db: bool = True, 
    use_optimized_prompt: bool = True, 
    prompt_type: str = 'financial_extraction',
    company_name: Optional[str] = None,
    ticker: Optional[str] = None,
    use_rag: bool = True,
    use_web_search: bool = True
) -> ExtractionResponse:
    """
    Extract financial data from text with optional RAG enhancement
    
    Args:
        text: PDF or financial report text
        save_to_db: Whether to save results to database
        use_optimized_prompt: Use optimized prompt (Iteration 2)
        prompt_type: Type of prompt template
        company_name: Company name for RAG context
        ticker: Stock ticker for RAG context
        use_rag: Enable RAG retrieval (database + web search)
        use_web_search: Allow web search if database empty
    """
    llm = LLMService()
    
    try:
        # Step 1: RAG Enhancement (if enabled)
        enhanced_text = text
        rag_context = None
        
        if use_rag and company_name:
            logger.info(f"RAG enabled for {company_name}")
            enhanced_text = await rag_service.enhance_with_rag(
                pdf_text=text,
                company_name=company_name,
                ticker=ticker,
                use_web_search=use_web_search
            )
            logger.info("Text enhanced with RAG context")
        
        # Step 2: LLM Extraction
        if use_optimized_prompt:
            raw = await llm.extract_financial_data_optimized(enhanced_text, prompt_type)
        else:
            raw = await llm.extract_financial_data(enhanced_text)

        financial_data = FinancialData(
            company_name=raw.get("company_name", "Unknown"),
            ticker=raw.get("ticker"),
            currency=raw.get("currency", "CNY"),
            fiscal_year=_safe_int(raw, "fiscal_year"),
            revenue=_safe_float(raw, "revenue"),
            revenue_growth=_safe_float(raw, "revenue_growth"),
            operating_income=_safe_float(raw, "operating_income"),
            operating_margin=_safe_float(raw, "operating_margin", 0.15),
            net_income=_safe_float(raw, "net_income"),
            depreciation_amortization=_safe_float(raw, "depreciation_amortization"),
            capital_expenditure=_safe_float(raw, "capital_expenditure"),
            change_in_working_capital=_safe_float(raw, "change_in_working_capital"),
            total_debt=_safe_float(raw, "total_debt"),
            cash_and_equivalents=_safe_float(raw, "cash_and_equivalents"),
            shares_outstanding=_safe_float(raw, "shares_outstanding", 1.0),
            tax_rate=_safe_float(raw, "tax_rate", 0.25),
            beta=_safe_float(raw, "beta", 1.0),
            risk_free_rate=_safe_float(raw, "risk_free_rate", 0.03),
            market_return=_safe_float(raw, "market_return", 0.09),
            cost_of_debt=_safe_float(raw, "cost_of_debt", 0.05),
            current_stock_price=raw.get("current_stock_price"),
        )
        
        # Save to database if requested and ticker is available
        if save_to_db and financial_data.ticker:
            try:
                await _save_extracted_data_to_db(financial_data, raw)
                logger.info(f"Saved extracted data for {financial_data.ticker} to database")
            except Exception as db_err:
                logger.warning(f"Failed to save to database: {db_err}")

        return ExtractionResponse(
            success=True,
            financial_data=financial_data,
            extracted_text=text[:3000],
        )
    except Exception as exc:
        logger.error("Extraction failed: %s", exc)
        return ExtractionResponse(
            success=False,
            error=str(exc),
        )


async def _save_extracted_data_to_db(financial_data: FinancialData, raw_data: dict):
    """Save extracted financial data to database"""
    ticker = financial_data.ticker
    if not ticker:
        return
    
    # 1. Save stock info
    db_service.insert_stock(ticker, "US")  # Default to US, could be parameterized
    
    # 2. Save asset profile if available
    if raw_data.get("sector") or raw_data.get("industry"):
        profile_data = {
            'sector': raw_data.get('sector'),
            'industry': raw_data.get('industry'),
            'full_time_employees': raw_data.get('employees'),
            'description': raw_data.get('description')
        }
        db_service.insert_asset_profile(ticker, profile_data)
    
    # 3. Save income statement
    fiscal_year = financial_data.fiscal_year
    report_date = date(fiscal_year, 12, 31)  # Assume year-end
    
    income_stmt = {
        'report_date': report_date,
        'report_type': 'annual',
        'total_revenue': financial_data.revenue if financial_data.revenue > 0 else None,
        'gross_profit': None,  # Not directly extracted
        'operating_income': financial_data.operating_income if financial_data.operating_income > 0 else None,
        'net_income': financial_data.net_income if financial_data.net_income > 0 else None,
        'ebit': None  # Could be calculated
    }
    db_service.insert_income_statement(ticker, income_stmt)
    
    # 4. Save balance sheet
    balance_sheet = {
        'report_date': report_date,
        'report_type': 'annual',
        'total_assets': None,  # Not directly extracted
        'total_liabilities': None,
        'total_equity': None,
        'cash_and_equivalents': financial_data.cash_and_equivalents if financial_data.cash_and_equivalents > 0 else None
    }
    db_service.insert_balance_sheet(ticker, balance_sheet)
    
    # 5. Save cash flow (approximate from available data)
    # FCF = Operating Income * (1 - tax_rate) + Depreciation - CapEx - Change in WC
    operating_cf = (
        financial_data.operating_income * (1 - financial_data.tax_rate) +
        financial_data.depreciation_amortization -
        financial_data.change_in_working_capital
    ) if financial_data.operating_income > 0 else None
    
    cash_flow = {
        'report_date': report_date,
        'report_type': 'annual',
        'operating_activities': operating_cf,
        'investment_activities': -financial_data.capital_expenditure if financial_data.capital_expenditure > 0 else None,
        'financing_activities': None,
        'changes_in_cash': None,
        'overall': operating_cf
    }
    db_service.insert_cash_flow(ticker, cash_flow)
