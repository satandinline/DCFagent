from __future__ import annotations

from models.schemas import (
    DCFParameters,
    DCFResult,
    FCFProjection,
    FinancialData,
    SensitivityMatrix,
)


def calculate_wacc(financial_data: FinancialData, params: DCFParameters) -> float:
    if params.discount_rate_override is not None:
        return params.discount_rate_override

    cost_of_equity = (
        financial_data.risk_free_rate
        + financial_data.beta * (financial_data.market_return - financial_data.risk_free_rate)
    )

    market_cap = financial_data.shares_outstanding * (financial_data.current_stock_price or 0)
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
    return max(wacc, 0.01)


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
