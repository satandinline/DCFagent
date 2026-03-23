from __future__ import annotations

import logging

from models.schemas import ExtractionResponse, FinancialData
from services.llm_service import LLMService

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


async def extract_from_text(text: str) -> ExtractionResponse:
    llm = LLMService()
    try:
        raw = await llm.extract_financial_data(text)

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
