from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class FinancialData(BaseModel):
    company_name: str = ""
    ticker: Optional[str] = None
    currency: str = "CNY"
    fiscal_year: int = 2025
    revenue: float = 0
    revenue_growth: float = 0
    operating_income: float = 0
    operating_margin: float = 0.15
    net_income: float = 0
    depreciation_amortization: float = 0
    capital_expenditure: float = 0
    change_in_working_capital: float = 0
    total_debt: float = 0
    cash_and_equivalents: float = 0
    shares_outstanding: float = 0
    tax_rate: float = 0.25
    beta: float = 1.0
    risk_free_rate: float = 0.03
    market_return: float = 0.09
    cost_of_debt: float = 0.05
    current_stock_price: Optional[float] = None


class DCFParameters(BaseModel):
    projection_years: int = Field(default=5)
    revenue_growth_rate: float = Field(default=0.08)
    terminal_growth_rate: float = Field(default=0.025)
    operating_margin: float = Field(default=0.15)
    tax_rate: float = Field(default=0.25)
    capex_ratio: float = Field(default=0.05)
    da_ratio: float = Field(default=0.04)
    nwc_ratio: float = Field(default=0.02)
    wacc: float = Field(default=0.1)
    discount_rate_override: Optional[float] = None


class FCFProjection(BaseModel):
    year: int
    revenue: float
    operating_income: float
    nopat: float
    depreciation_amortization: float
    capital_expenditure: float
    change_in_nwc: float
    free_cash_flow: float
    discount_factor: float
    present_value: float


class DCFResult(BaseModel):
    projections: list[FCFProjection]
    terminal_value: float
    pv_terminal_value: float
    pv_fcf_sum: float
    enterprise_value: float
    equity_value: float
    per_share_value: float
    current_price: Optional[float] = None
    upside_downside: Optional[float] = None
    wacc_used: float
    terminal_growth_used: float


class SensitivityMatrix(BaseModel):
    wacc_range: list[float]
    growth_range: list[float]
    values: list[list[float]]


class ExtractionResponse(BaseModel):
    success: bool = True
    financial_data: Optional[FinancialData] = None
    extracted_text: Optional[str] = None
    error: Optional[str] = None


class NarrativeRequest(BaseModel):
    financial_data: FinancialData
    dcf_result: DCFResult
    sensitivity_matrix: Optional[SensitivityMatrix] = None
    language: Optional[str] = None


class NarrativeResponse(BaseModel):
    success: bool = True
    narrative: Optional[str] = None
    error: Optional[str] = None


class CalculateRequest(BaseModel):
    financial_data: FinancialData
    parameters: DCFParameters
