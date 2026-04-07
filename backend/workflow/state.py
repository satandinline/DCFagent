"""
LangGraph Workflow State Definitions for DCF Valuation Agent
Defines the state structure used throughout the workflow
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from enum import Enum


class IndustryType(Enum):
    """Industry classification types"""
    MANUFACTURING_CONSUMER = "manufacturing_consumer"
    FINANCIAL_INSTITUTION = "financial_institution"
    HIGH_GROWTH_LOSS = "high_growth_loss"
    DIVERSIFIED_GROUP = "diversified_group"
    TECHNOLOGY = "technology"
    UNKNOWN = "unknown"


class ValuationMethod(Enum):
    """Valuation methods"""
    DCF = "dcf"
    DDM = "ddm"
    PS = "ps"
    PB = "pb"
    EV_EBITDA = "ev_ebitda"
    SOTP = "sotp"


class Action(Enum):
    """Investment actions"""
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"


@dataclass
class TickerData:
    """Data for a single ticker/stock"""
    ticker: str
    locale: str = "US"
    company_name: str = ""
    sector: str = ""
    industry: str = ""
    is_profitable: bool = True
    has_dividends: bool = False
    revenue_growth: float = 0.0
    net_income: float = 0.0
    
    # Financial data from Yahoo Finance
    market_cap: float = 0.0
    current_price: float = 0.0
    revenue: float = 0.0
    operating_income: float = 0.0
    total_debt: float = 0.0
    total_cash: float = 0.0
    shares_outstanding: float = 1.0
    beta: float = 1.0
    dividend_yield: float = 0.0
    
    # Classification results
    industry_type: Optional[IndustryType] = None
    recommended_methods: List[str] = field(default_factory=list)
    
    # Valuation results
    valuation_results: Dict[str, float] = field(default_factory=dict)
    fair_value: float = 0.0
    upside: float = 0.0
    action: Action = Action.HOLD
    confidence: str = "MEDIUM"
    
    # Status
    status: str = "pending"  # pending, fetching_data, classifying, valuing, completed, failed
    error: Optional[str] = None
    processed_at: Optional[str] = None


@dataclass
class WorkflowState:
    """
    Main state object passed through the LangGraph workflow
    
    This state is updated at each step of the workflow, allowing
    for flexible branching and loops based on actual data.
    """
    # Workflow metadata
    workflow_id: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    current_step: str = "init"
    
    # Configuration
    config: Dict[str, Any] = field(default_factory=dict)
    
    # Tickers to process
    tickers: List[str] = field(default_factory=list)
    current_ticker_index: int = 0
    
    # Per-ticker data
    ticker_data: Dict[str, TickerData] = field(default_factory=dict)
    
    # Results
    completed_tickers: List[str] = field(default_factory=list)
    failed_tickers: List[str] = field(default_factory=list)
    
    # Portfolio aggregation
    recommendations: List[Dict[str, Any]] = field(default_factory=list)
    portfolio_summary: Dict[str, Any] = field(default_factory=dict)
    
    # Communication
    email_sent: bool = False
    email_result: Optional[Dict[str, Any]] = None
    
    # Workflow decisions
    next_node: str = "idle"
    should_send_email: bool = True
    should_continue: bool = True
    
    # Error tracking
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    # Human-in-the-loop (for future use)
    requires_approval: bool = False
    approved: bool = False
    
    def get_current_ticker(self) -> Optional[str]:
        """Get the currently processing ticker"""
        if self.current_ticker_index < len(self.tickers):
            return self.tickers[self.current_ticker_index]
        return None
    
    def get_current_ticker_data(self) -> Optional[TickerData]:
        """Get data for current ticker"""
        ticker = self.get_current_ticker()
        if ticker:
            return self.ticker_data.get(ticker)
        return None
    
    def advance_to_next_ticker(self) -> bool:
        """Move to next ticker, returns False if no more tickers"""
        self.current_ticker_index += 1
        return self.current_ticker_index < len(self.tickers)
    
    def add_error(self, error: str):
        """Add an error message"""
        self.errors.append(f"[{datetime.now().isoformat()}] {error}")
    
    def add_warning(self, warning: str):
        """Add a warning message"""
        self.warnings.append(f"[{datetime.now().isoformat()}] {warning}")
    
    def to_summary(self) -> Dict[str, Any]:
        """Generate a summary of the workflow execution"""
        return {
            'workflow_id': self.workflow_id,
            'started_at': self.started_at,
            'completed_at': self.completed_at,
            'total_tickers': len(self.tickers),
            'completed': len(self.completed_tickers),
            'failed': len(self.failed_tickers),
            'email_sent': self.email_sent,
            'recommendations_count': len(self.recommendations),
            'errors': self.errors,
            'warnings': self.warnings
        }
