"""
Valuation Engine for DCF Valuation Agent
Provides multiple valuation methods beyond basic DCF
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
import math

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.models.schemas import FinancialData, DCFParameters, DCFResult
from backend.services.dcf_service import run_dcf, sensitivity_analysis, calculate_wacc


class ValuationMethod(Enum):
    """Available valuation methods"""
    DCF = "dcf"
    DDM = "ddm"                    # Dividend Discount Model
    PS = "ps"                      # Price to Sales
    PB = "pb"                      # Price to Book
    EV_EBITDA = "ev_ebitda"        # EV/EBITDA Multiple
    SOTP = "sotp"                  # Sum of the Parts


@dataclass
class ValuationResult:
    """Result from a valuation method"""
    method: str
    fair_value: float
    current_price: Optional[float] = None
    upside_percent: Optional[float] = None
    confidence: str = "MEDIUM"
    details: Dict[str, Any] = field(default_factory=dict)
    recommendation: str = ""


@dataclass
class CombinedValuationResult:
    """Combined results from multiple valuation methods"""
    ticker: str
    company_name: str
    primary_method: str
    results: Dict[str, ValuationResult] = field(default_factory=dict)
    weighted_fair_value: Optional[float] = None
    average_fair_value: Optional[float] = None
    consensus_action: str = "HOLD"  # BUY, HOLD, SELL
    consensus_upside: float = 0


class BaseValuator(ABC):
    """Abstract base class for valuation methods"""
    
    @abstractmethod
    def evaluate(self, data: FinancialData, params: DCFParameters = None) -> ValuationResult:
        """Run valuation and return result"""
        pass
    
    @property
    @abstractmethod
    def method_name(self) -> str:
        """Return the method name"""
        pass


class DCFValuator(BaseValuator):
    """Discounted Cash Flow valuation"""
    
    @property
    def method_name(self) -> str:
        return "DCF"
    
    def evaluate(self, data: FinancialData, params: DCFParameters = None) -> ValuationResult:
        """Run DCF valuation"""
        if params is None:
            params = DCFParameters()
        
        try:
            dcf_result = run_dcf(data, params)
            
            # Calculate upside
            upside = None
            if dcf_result.current_price and dcf_result.current_price > 0:
                upside = (dcf_result.per_share_value - dcf_result.current_price) / dcf_result.current_price * 100
            
            return ValuationResult(
                method=self.method_name,
                fair_value=dcf_result.per_share_value,
                current_price=dcf_result.current_price,
                upside_percent=upside,
                confidence="HIGH",
                details={
                    'enterprise_value': dcf_result.enterprise_value,
                    'equity_value': dcf_result.equity_value,
                    'wacc': dcf_result.wacc_used,
                    'terminal_growth': dcf_result.terminal_growth_used,
                    'pv_fcf_sum': dcf_result.pv_fcf_sum,
                    'terminal_value': dcf_result.terminal_value
                },
                recommendation=f"基于DCF估值，每股价值 ${dcf_result.per_share_value:.2f}"
            )
        except Exception as e:
            return ValuationResult(
                method=self.method_name,
                fair_value=0,
                confidence="LOW",
                details={'error': str(e)},
                recommendation=f"DCF估值失败: {str(e)}"
            )


class DDMValuator(BaseValuator):
    """
    Dividend Discount Model - for financial institutions
    
    V = D / (r - g)
    where:
        D = Current dividend
        r = Required rate of return (cost of equity)
        g = Dividend growth rate
    """
    
    @property
    def method_name(self) -> str:
        return "DDM"
    
    def evaluate(self, data: FinancialData, params: DCFParameters = None) -> ValuationResult:
        """Run DDM valuation"""
        try:
            # For DDM, we need dividend info - estimate from net income if available
            # Assume 30% payout ratio as default
            net_income = data.net_income if data.net_income > 0 else data.revenue * 0.1
            payout_ratio = 0.3  # 30% payout
            dividend_per_share = (net_income * payout_ratio) / data.shares_outstanding if data.shares_outstanding > 0 else 0
            
            # Cost of equity (CAPM)
            cost_of_equity = (
                data.risk_free_rate 
                + data.beta * (data.market_return - data.risk_free_rate)
            )
            
            # Assume dividend growth = ROE * retention ratio
            # Simplified: use terminal growth rate as proxy
            terminal_growth = 0.025  # 2.5%
            
            if cost_of_equity <= terminal_growth:
                return ValuationResult(
                    method=self.method_name,
                    fair_value=0,
                    confidence="LOW",
                    details={'error': 'Cost of equity <= growth rate'},
                    recommendation="DDM不适用：收益率过低"
                )
            
            # Gordon Growth Model
            if dividend_per_share > 0:
                fair_value = dividend_per_share / (cost_of_equity - terminal_growth)
            else:
                fair_value = 0
            
            # Calculate upside
            upside = None
            if data.current_stock_price and data.current_stock_price > 0:
                upside = (fair_value - data.current_stock_price) / data.current_stock_price * 100
            
            return ValuationResult(
                method=self.method_name,
                fair_value=fair_value,
                current_price=data.current_stock_price,
                upside_percent=upside,
                confidence="MEDIUM",
                details={
                    'dividend_per_share': dividend_per_share,
                    'cost_of_equity': cost_of_equity,
                    'terminal_growth': terminal_growth,
                    'payout_ratio': payout_ratio
                },
                recommendation=f"基于DDM估值，每股价值 ${fair_value:.2f}"
            )
        except Exception as e:
            return ValuationResult(
                method=self.method_name,
                fair_value=0,
                confidence="LOW",
                details={'error': str(e)},
                recommendation=f"DDM估值失败: {str(e)}"
            )


class PSValuator(BaseValuator):
    """
    Price to Sales / EV to Revenue - for high growth unprofitable companies
    
    V = Revenue * PS_Multiple
    """
    
    # Industry PS multiples
    PS_MULTIPLES = {
        'saas': 8.0,      # SaaS typically 8-12x
        'tech': 5.0,      # Tech 5-8x
        'retail': 1.0,    # Retail 0.5-2x
        'manufacturing': 1.5,  # Manufacturing 1-2x
        'default': 3.0
    }
    
    @property
    def method_name(self) -> str:
        return "P/S"
    
    def evaluate(self, data: FinancialData, params: DCFParameters = None) -> ValuationResult:
        """Run P/S valuation"""
        try:
            # Determine PS multiple based on characteristics
            if data.revenue_growth > 0.3:
                ps_multiple = self.PS_MULTIPLES['saas']
            elif data.revenue_growth > 0.15:
                ps_multiple = self.PS_MULTIPLES['tech']
            else:
                ps_multiple = self.PS_MULTIPLES['default']
            
            # Calculate revenue per share
            revenue_per_share = data.revenue / data.shares_outstanding if data.shares_outstanding > 0 else 0
            
            # Fair value
            fair_value = revenue_per_share * ps_multiple
            
            # Calculate upside
            upside = None
            if data.current_stock_price and data.current_stock_price > 0:
                upside = (fair_value - data.current_stock_price) / data.current_stock_price * 100
            
            return ValuationResult(
                method=self.method_name,
                fair_value=fair_value,
                current_price=data.current_stock_price,
                upside_percent=upside,
                confidence="MEDIUM",
                details={
                    'revenue_per_share': revenue_per_share,
                    'ps_multiple': ps_multiple,
                    'revenue': data.revenue,
                    'revenue_growth': data.revenue_growth
                },
                recommendation=f"基于P/S估值，每股价值 ${fair_value:.2f} (使用{ps_multiple}x倍数)"
            )
        except Exception as e:
            return ValuationResult(
                method=self.method_name,
                fair_value=0,
                confidence="LOW",
                details={'error': str(e)},
                recommendation=f"P/S估值失败: {str(e)}"
            )


class PBValuator(BaseValuator):
    """
    Price to Book - for financial institutions
    
    V = Book Value per Share * P/B Multiple
    """
    
    # Industry P/B multiples
    PB_MULTIPLES = {
        'bank': 1.0,        # Banks typically 0.8-1.5x
        'insurance': 1.2,   # Insurance 1-1.5x
        'default': 1.0
    }
    
    @property
    def method_name(self) -> str:
        return "P/B"
    
    def evaluate(self, data: FinancialData, params: DCFParameters = None) -> ValuationResult:
        """Run P/B valuation"""
        try:
            # Book value = Total equity
            # Simplified: use (total_debt - cash) as proxy for equity structure
            # More accurate: equity = assets - liabilities
            # Here we estimate equity as a portion of total_debt
            
            # Estimate book value per share
            total_equity = data.cash_and_equivalents  # Simplified - should use actual equity
            if data.total_debt > 0:
                total_equity = data.total_debt * 0.5  # Rough estimate
            
            book_value_per_share = total_equity / data.shares_outstanding if data.shares_outstanding > 0 else 0
            
            # Determine P/B multiple
            pb_multiple = self.PB_MULTIPLES['default']
            
            # Fair value
            fair_value = book_value_per_share * pb_multiple
            
            # Calculate upside
            upside = None
            if data.current_stock_price and data.current_stock_price > 0:
                upside = (fair_value - data.current_stock_price) / data.current_stock_price * 100
            
            return ValuationResult(
                method=self.method_name,
                fair_value=fair_value,
                current_price=data.current_stock_price,
                upside_percent=upside,
                confidence="MEDIUM",
                details={
                    'book_value_per_share': book_value_per_share,
                    'pb_multiple': pb_multiple,
                    'total_equity': total_equity
                },
                recommendation=f"基于P/B估值，每股价值 ${fair_value:.2f} (使用{pb_multiple}x倍数)"
            )
        except Exception as e:
            return ValuationResult(
                method=self.method_name,
                fair_value=0,
                confidence="LOW",
                details={'error': str(e)},
                recommendation=f"P/B估值失败: {str(e)}"
            )


class EVEBITDAValuator(BaseValuator):
    """
    EV/EBITDA Multiple - for stable cash flow businesses
    
    EV = EBITDA * Multiple
    Equity Value = EV - Net Debt
    """
    
    # Industry EV/EBITDA multiples
    EBITDA_MULTIPLES = {
        'manufacturing': 8.0,
        'consumer': 10.0,
        'tech': 15.0,
        'retail': 7.0,
        'default': 10.0
    }
    
    @property
    def method_name(self) -> str:
        return "EV/EBITDA"
    
    def evaluate(self, data: FinancialData, params: DCFParameters = None) -> ValuationResult:
        """Run EV/EBITDA valuation"""
        try:
            # Calculate EBITDA
            operating_income = data.operating_income if data.operating_income > 0 else data.revenue * 0.15
            da = data.depreciation_amortization if data.depreciation_amortization > 0 else data.revenue * 0.04
            ebitda = operating_income + da
            
            # Determine multiple based on sector/industry
            ebitda_multiple = self.EBITDA_MULTIPLES['default']
            
            # Calculate enterprise value
            enterprise_value = ebitda * ebitda_multiple
            
            # Calculate equity value
            net_debt = data.total_debt - data.cash_and_equivalents
            equity_value = enterprise_value - net_debt
            
            # Per share value
            fair_value = equity_value / data.shares_outstanding if data.shares_outstanding > 0 else 0
            
            # Calculate upside
            upside = None
            if data.current_stock_price and data.current_stock_price > 0:
                upside = (fair_value - data.current_stock_price) / data.current_stock_price * 100
            
            return ValuationResult(
                method=self.method_name,
                fair_value=fair_value,
                current_price=data.current_stock_price,
                upside_percent=upside,
                confidence="MEDIUM",
                details={
                    'ebitda': ebitda,
                    'ebitda_multiple': ebitda_multiple,
                    'enterprise_value': enterprise_value,
                    'net_debt': net_debt,
                    'equity_value': equity_value
                },
                recommendation=f"基于EV/EBITDA估值，每股价值 ${fair_value:.2f} (使用{ebitda_multiple}x倍数)"
            )
        except Exception as e:
            return ValuationResult(
                method=self.method_name,
                fair_value=0,
                confidence="LOW",
                details={'error': str(e)},
                recommendation=f"EV/EBITDA估值失败: {str(e)}"
            )


class SOTPValuator(BaseValuator):
    """
    Sum of the Parts - for diversified groups
    
    Value = Sum of (Each Business Segment Value)
    """
    
    @property
    def method_name(self) -> str:
        return "SOTP"
    
    def evaluate(self, data: FinancialData, params: DCFParameters = None) -> ValuationResult:
        """Run SOTP valuation (simplified single-segment version)"""
        try:
            # For simplified SOTP, we treat the whole company as one segment
            # In reality, would need segment data
            
            # Use DCF as base for each segment
            if params is None:
                params = DCFParameters()
            
            dcf_result = run_dcf(data, params)
            
            # Discount for complexity (10-20%)
            complexity_discount = 0.85
            
            fair_value = dcf_result.per_share_value * complexity_discount
            
            # Calculate upside
            upside = None
            if data.current_stock_price and data.current_stock_price > 0:
                upside = (fair_value - data.current_stock_price) / data.current_stock_price * 100
            
            return ValuationResult(
                method=self.method_name,
                fair_value=fair_value,
                current_price=data.current_stock_price,
                upside_percent=upside,
                confidence="MEDIUM",
                details={
                    'dcf_value': dcf_result.per_share_value,
                    'complexity_discount': complexity_discount,
                    'note': 'SOTP需要各业务板块分别估值，此处使用简化版本'
                },
                recommendation=f"基于SOTP估值，每股价值 ${fair_value:.2f}（已应用15%复杂性折价）"
            )
        except Exception as e:
            return ValuationResult(
                method=self.method_name,
                fair_value=0,
                confidence="LOW",
                details={'error': str(e)},
                recommendation=f"SOTP估值失败: {str(e)}"
            )


class ValuationEngine:
    """
    Main valuation engine that coordinates multiple valuation methods
    """
    
    def __init__(self):
        self.valuators: Dict[ValuationMethod, BaseValuator] = {
            ValuationMethod.DCF: DCFValuator(),
            ValuationMethod.DDM: DDMValuator(),
            ValuationMethod.PS: PSValuator(),
            ValuationMethod.PB: PBValuator(),
            ValuationMethod.EV_EBITDA: EVEBITDAValuator(),
            ValuationMethod.SOTP: SOTPValuator(),
        }
    
    def evaluate(
        self,
        data: FinancialData,
        methods: List[ValuationMethod] = None,
        params: DCFParameters = None
    ) -> CombinedValuationResult:
        """
        Run multiple valuations and combine results
        
        Args:
            data: Financial data
            methods: List of methods to use (default: all)
            params: DCF parameters
            
        Returns:
            CombinedValuationResult with all method results
        """
        if methods is None:
            methods = [
                ValuationMethod.DCF,
                ValuationMethod.EV_EBITDA,
            ]
        
        results: Dict[str, ValuationResult] = {}
        valid_values = []
        
        for method in methods:
            valuator = self.valuators.get(method)
            if valuator:
                result = valuator.evaluate(data, params)
                results[method.value] = result
                
                if result.fair_value > 0:
                    valid_values.append(result.fair_value)
        
        # Calculate consensus
        average_fair_value = sum(valid_values) / len(valid_values) if valid_values else 0
        
        # Determine action based on average upside
        consensus_action = "HOLD"
        consensus_upside = 0
        
        if valid_values and data.current_stock_price and data.current_stock_price > 0:
            avg_upside = ((average_fair_value - data.current_stock_price) / data.current_stock_price) * 100
            consensus_upside = avg_upside
            
            if avg_upside > 20:
                consensus_action = "BUY"
            elif avg_upside < -10:
                consensus_action = "SELL"
        
        return CombinedValuationResult(
            ticker=data.ticker or "UNKNOWN",
            company_name=data.company_name,
            primary_method=methods[0].value if methods else "DCF",
            results=results,
            average_fair_value=average_fair_value,
            consensus_action=consensus_action,
            consensus_upside=consensus_upside
        )
    
    def evaluate_with_dcf(
        self,
        data: FinancialData,
        params: DCFParameters = None
    ) -> CombinedValuationResult:
        """Convenience method for DCF-based evaluation"""
        return self.evaluate(data, [ValuationMethod.DCF, ValuationMethod.EV_EBITDA], params)
    
    def evaluate_financial(
        self,
        data: FinancialData,
        params: DCFParameters = None
    ) -> CombinedValuationResult:
        """Convenience method for financial institutions"""
        return self.evaluate(data, [ValuationMethod.DDM, ValuationMethod.PB], params)
    
    def evaluate_high_growth(
        self,
        data: FinancialData,
        params: DCFParameters = None
    ) -> CombinedValuationResult:
        """Convenience method for high-growth unprofitable companies"""
        return self.evaluate(data, [ValuationMethod.PS, ValuationMethod.DCF], params)
    
    def evaluate_diversified(
        self,
        data: FinancialData,
        params: DCFParameters = None
    ) -> CombinedValuationResult:
        """Convenience method for diversified groups"""
        return self.evaluate(data, [ValuationMethod.SOTP, ValuationMethod.DCF, ValuationMethod.EV_EBITDA], params)


# Singleton instance
valuation_engine = ValuationEngine()
