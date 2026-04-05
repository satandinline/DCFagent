from __future__ import annotations

import json
from datetime import datetime
from typing import Optional, Dict, Any

from backend.models.schemas import (
    DCFParameters,
    DCFResult,
    FCFProjection,
    FinancialData,
    SensitivityMatrix,
)
from backend.services.db_service import db_service


def calculate_wacc(financial_data: FinancialData, params: DCFParameters) -> float:
    if params.discount_rate_override is not None:
        return params.discount_rate_override

    cost_of_equity = (
        financial_data.risk_free_rate
        + financial_data.beta * (financial_data.market_return - financial_data.risk_free_rate)
    )

    # Calculate market cap and capital weights
    stock_price = financial_data.current_stock_price or 0
    market_cap = financial_data.shares_outstanding * stock_price if stock_price > 0 else 0
    
    # If we can't calculate market cap, use reasonable defaults
    if market_cap <= 0 and financial_data.total_debt > 0:
        # Estimate equity as 2x debt for typical companies
        market_cap = financial_data.total_debt * 2
    elif market_cap <= 0:
        # Default to 70/30 equity/debt split
        market_cap = 1.0  # Placeholder
    
    total_capital = market_cap + financial_data.total_debt
    
    if total_capital > 0:
        equity_weight = market_cap / total_capital
        debt_weight = financial_data.total_debt / total_capital
    else:
        equity_weight = 0.7
        debt_weight = 0.3

    wacc = (
        equity_weight * cost_of_equity
        + debt_weight * financial_data.cost_of_debt * (1.0 - financial_data.tax_rate)
    )
    
    # Ensure WACC is in reasonable range (6% - 15%)
    wacc = max(wacc, 0.06)
    wacc = min(wacc, 0.15)
    
    return wacc


def project_fcf(
    financial_data: FinancialData,
    params: DCFParameters,
    wacc: float,
) -> list[FCFProjection]:
    base_revenue = financial_data.revenue if financial_data.revenue > 0 else 1.0

    projections: list[FCFProjection] = []
    revenue = base_revenue

    for t in range(1, params.projection_years + 1):
        revenue *= 1.0 + params.revenue_growth_rate

        operating_income = revenue * params.operating_margin
        nopat = operating_income * (1.0 - params.tax_rate)
        da = revenue * params.da_ratio
        capex = revenue * params.capex_ratio
        nwc_change = revenue * params.nwc_ratio

        fcf = nopat + da - capex - nwc_change

        discount_factor = 1.0 / ((1.0 + wacc) ** t)
        pv = fcf * discount_factor

        projections.append(
            FCFProjection(
                year=t,
                revenue=round(revenue, 2),
                operating_income=round(operating_income, 2),
                nopat=round(nopat, 2),
                depreciation_amortization=round(da, 2),
                capital_expenditure=round(capex, 2),
                change_in_nwc=round(nwc_change, 2),
                free_cash_flow=round(fcf, 2),
                discount_factor=round(discount_factor, 6),
                present_value=round(pv, 2),
            )
        )

    return projections


def calculate_terminal_value(last_fcf: float, wacc: float, terminal_growth: float) -> float:
    if wacc <= terminal_growth:
        return 0.0
    return last_fcf * (1.0 + terminal_growth) / (wacc - terminal_growth)


def run_dcf(financial_data: FinancialData, params: DCFParameters) -> DCFResult:
    wacc = params.wacc if params.wacc > 0 else calculate_wacc(financial_data, params)

    projections = project_fcf(financial_data, params, wacc)

    pv_fcf_sum = sum(p.present_value for p in projections)

    last_fcf = projections[-1].free_cash_flow if projections else 0.0
    terminal_value = calculate_terminal_value(last_fcf, wacc, params.terminal_growth_rate)

    discount_factor_tv = 1.0 / ((1.0 + wacc) ** params.projection_years)
    pv_terminal_value = terminal_value * discount_factor_tv

    enterprise_value = pv_fcf_sum + pv_terminal_value
    equity_value = enterprise_value - financial_data.total_debt + financial_data.cash_and_equivalents
    shares = financial_data.shares_outstanding if financial_data.shares_outstanding > 0 else 1.0
    per_share_value = equity_value / shares

    upside_downside = None
    current_price = financial_data.current_stock_price
    if current_price and current_price > 0:
        upside_downside = (per_share_value - current_price) / current_price

    return DCFResult(
        projections=projections,
        terminal_value=round(terminal_value, 2),
        pv_terminal_value=round(pv_terminal_value, 2),
        pv_fcf_sum=round(pv_fcf_sum, 2),
        enterprise_value=round(enterprise_value, 2),
        equity_value=round(equity_value, 2),
        per_share_value=round(per_share_value, 2),
        current_price=current_price,
        upside_downside=round(upside_downside, 4) if upside_downside is not None else None,
        wacc_used=round(wacc, 6),
        terminal_growth_used=params.terminal_growth_rate,
    )


def sensitivity_analysis(
    financial_data: FinancialData,
    params: DCFParameters,
) -> SensitivityMatrix:
    base_wacc = params.wacc if params.wacc > 0 else calculate_wacc(financial_data, params)

    wacc_range = [
        round(base_wacc + offset, 4)
        for offset in [-0.02, -0.015, -0.01, -0.005, 0.0, 0.005, 0.01, 0.015, 0.02]
    ]
    growth_range = [
        round(params.terminal_growth_rate + offset, 4)
        for offset in [-0.015, -0.01, -0.005, 0.0, 0.005, 0.01, 0.015]
    ]

    values: list[list[float]] = []
    for w in wacc_range:
        row: list[float] = []
        for g in growth_range:
            if w <= g or w <= 0:
                row.append(0.0)
                continue
            tweaked = params.model_copy(update={"terminal_growth_rate": g, "wacc": w})
            projections = project_fcf(financial_data, tweaked, w)
            pv_fcfs = sum(p.present_value for p in projections)
            last_fcf = projections[-1].free_cash_flow if projections else 0.0
            tv = calculate_terminal_value(last_fcf, w, g)
            df_tv = 1.0 / ((1.0 + w) ** tweaked.projection_years)
            pv_tv = tv * df_tv
            ev = pv_fcfs + pv_tv
            eq = ev - financial_data.total_debt + financial_data.cash_and_equivalents
            shares = financial_data.shares_outstanding if financial_data.shares_outstanding > 0 else 1.0
            row.append(round(eq / shares, 2))
        values.append(row)

    return SensitivityMatrix(
        wacc_range=wacc_range,
        growth_range=growth_range,
        values=values,
    )


def save_valuation_to_db(
    financial_data: FinancialData,
    params: DCFParameters,
    dcf_result: DCFResult,
    sensitivity_matrix: Optional[SensitivityMatrix] = None,
    narrative: Optional[str] = None,
    created_by: Optional[str] = None,
    notes: Optional[str] = None
) -> bool:
    """Save DCF valuation result to database"""
    if not financial_data.ticker:
        return False
    
    try:
        # Calculate FCF for storage
        fcf = dcf_result.projections[-1].free_cash_flow if dcf_result.projections else 0
        
        valuation_data = {
            'company_name': financial_data.company_name,
            'fiscal_year': financial_data.fiscal_year,
            'currency': financial_data.currency,
            'per_share_value': dcf_result.per_share_value,
            'enterprise_value': dcf_result.enterprise_value,
            'equity_value': dcf_result.equity_value,
            'wacc_used': dcf_result.wacc_used,
            'terminal_growth_rate': dcf_result.terminal_growth_used,
            'projection_years': params.projection_years,
            'current_price': financial_data.current_stock_price,
            'upside_downside': dcf_result.upside_downside,
            'revenue_growth_rate': params.revenue_growth_rate,
            'operating_margin': params.operating_margin,
            'tax_rate': params.tax_rate,
            'free_cash_flow': fcf,
            'terminal_value': dcf_result.terminal_value,
            'pv_fcf_sum': dcf_result.pv_fcf_sum,
            'sensitivity_data': json.dumps(sensitivity_matrix.model_dump()) if sensitivity_matrix else None,
            'narrative': narrative,
            'created_by': created_by,
            'notes': notes
        }
        
        success = db_service.insert_valuation_result(financial_data.ticker, valuation_data)
        return success
    except Exception as e:
        print(f"Error saving valuation to database: {e}")
        return False


def load_financial_data_from_db(ticker: str) -> Optional[FinancialData]:
    """Load financial data from database for a given ticker"""
    try:
        stock_data = db_service.get_stock_data(ticker)
        if not stock_data:
            return None
        
        latest_income = stock_data.get('latest_income_statement') or {}
        latest_balance = stock_data.get('latest_balance_sheet') or {}
        latest_cashflow = stock_data.get('latest_cash_flow') or {}
        profile = stock_data.get('profile') or {}
        
        if not latest_income or not latest_income.get('total_revenue'):
            return None
        
        # Construct FinancialData from database records
        fiscal_year = 2023
        if latest_income.get('report_date'):
            try:
                fiscal_year = latest_income['report_date'].year
            except:
                pass
        
        revenue = float(latest_income.get('total_revenue', 0)) if latest_income.get('total_revenue') else 0
        operating_income = float(latest_income.get('operating_income', 0)) if latest_income.get('operating_income') else 0
        
        # Calculate operating margin
        op_margin = 0.15
        if revenue > 0 and operating_income > 0:
            op_margin = operating_income / revenue
        
        financial_data = FinancialData(
            company_name=profile.get('industry', '').split()[0] if profile.get('industry') else ticker,
            ticker=ticker,
            currency='USD',
            fiscal_year=fiscal_year,
            revenue=revenue,
            revenue_growth=0,
            operating_income=operating_income,
            operating_margin=op_margin,
            net_income=float(latest_income.get('net_income', 0)) if latest_income.get('net_income') else 0,
            depreciation_amortization=0,
            capital_expenditure=0,
            change_in_working_capital=0,
            total_debt=float(latest_balance.get('total_liabilities', 0)) if latest_balance.get('total_liabilities') else 0,
            cash_and_equivalents=float(latest_balance.get('cash_and_equivalents', 0)) if latest_balance.get('cash_and_equivalents') else 0,
            shares_outstanding=1.0,
            tax_rate=0.25,
            beta=1.0,
            risk_free_rate=0.03,
            market_return=0.09,
            cost_of_debt=0.05,
            current_stock_price=None
        )
        
        return financial_data
    except Exception as e:
        print(f"Error loading financial data from database: {e}")
        import traceback
        traceback.print_exc()
        return None


def get_trend_analysis(ticker: str) -> Dict[str, Any]:
    """Get trend analysis from historical data"""
    try:
        trends = db_service.calculate_growth_trends(ticker)
        
        # Add valuation history
        valuation_history = db_service.get_valuation_history(ticker, limit=5)
        
        return {
            'ticker': ticker,
            'trends': trends,
            'valuation_history': [
                {
                    'date': str(v['valuation_date']),
                    'per_share_value': float(v['per_share_value']) if v.get('per_share_value') else None,
                    'enterprise_value': float(v['enterprise_value']) if v.get('enterprise_value') else None,
                    'wacc_used': float(v['wacc_used']) if v.get('wacc_used') else None,
                    'upside_downside': float(v['upside_downside']) if v.get('upside_downside') else None
                }
                for v in valuation_history
            ]
        }
    except Exception as e:
        print(f"Error getting trend analysis: {e}")
        return {'ticker': ticker, 'trends': {}, 'valuation_history': []}
