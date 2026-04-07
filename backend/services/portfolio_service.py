"""
Portfolio Service for DCF Valuation Agent
Generates investment portfolio recommendations based on valuations
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import json

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.services.db_service import db_service
from backend.services.valuation_engine import CombinedValuationResult, ValuationResult
from backend.services.industry_classifier import industry_classifier, IndustryType


@dataclass
class StockRecommendation:
    """Recommendation for a single stock"""
    ticker: str
    company_name: str
    action: str  # BUY, HOLD, SELL
    upside: float
    confidence: str  # HIGH, MEDIUM, LOW
    valuation_methods: List[str]
    primary_method: str
    fair_value: float
    current_price: Optional[float]
    industry: str
    sector: str
    reason: str
    details: Dict[str, Any] = field(default_factory=dict)
    created_at: str = ""


@dataclass
class PortfolioReport:
    """Complete portfolio analysis report"""
    report_date: str
    stocks_analyzed: int
    recommendations: List[StockRecommendation]
    summary: Dict[str, Any] = field(default_factory=dict)
    details: List[Dict[str, Any]] = field(default_factory=list)


class PortfolioService:
    """
    Service for generating and managing investment portfolio recommendations
    """
    
    # Upside thresholds for recommendations
    BUY_THRESHOLD = 20.0  # > 20% upside
    SELL_THRESHOLD = -10.0  # < -10% downside
    HOLD_THRESHOLD = 5.0   # between -10% and 20%
    
    # Confidence mapping
    CONFIDENCE_MAP = {
        'HIGH': 3,
        'MEDIUM': 2,
        'LOW': 1
    }
    
    def __init__(self):
        self.recommendations: Dict[str, StockRecommendation] = {}
    
    def generate_recommendation(
        self,
        valuation_result: CombinedValuationResult,
        industry: str = "",
        sector: str = ""
    ) -> StockRecommendation:
        """
        Generate a recommendation from valuation results
        
        Args:
            valuation_result: Combined results from valuation engine
            industry: Company industry
            sector: Company sector
            
        Returns:
            StockRecommendation object
        """
        # Determine action based on consensus
        action = valuation_result.consensus_action
        
        # Calculate weighted confidence
        method_confidences = []
        for method_name, result in valuation_result.results.items():
            if isinstance(result, ValuationResult):
                conf_level = self.CONFIDENCE_MAP.get(result.confidence, 2)
                method_confidences.append((result.confidence, conf_level))
        
        # Overall confidence is average of method confidences
        if method_confidences:
            avg_conf_level = sum(c[1] for c in method_confidences) / len(method_confidences)
            if avg_conf_level >= 2.5:
                confidence = "HIGH"
            elif avg_conf_level >= 1.5:
                confidence = "MEDIUM"
            else:
                confidence = "LOW"
        else:
            confidence = "MEDIUM"
        
        # Generate reason
        reason = self._generate_reason(
            action=action,
            upside=valuation_result.consensus_upside,
            methods=list(valuation_result.results.keys()),
            industry=industry
        )
        
        # Get primary valuation value
        primary_value = valuation_result.average_fair_value
        current_price = None
        for result in valuation_result.results.values():
            if isinstance(result, ValuationResult):
                current_price = result.current_price
                break
        
        return StockRecommendation(
            ticker=valuation_result.ticker,
            company_name=valuation_result.company_name,
            action=action,
            upside=valuation_result.consensus_upside,
            confidence=confidence,
            valuation_methods=list(valuation_result.results.keys()),
            primary_method=valuation_result.primary_method,
            fair_value=primary_value,
            current_price=current_price,
            industry=industry,
            sector=sector,
            reason=reason,
            details={
                method: result.details for method, result in valuation_result.results.items()
                if isinstance(result, ValuationResult)
            },
            created_at=datetime.now().isoformat()
        )
    
    def _generate_reason(
        self,
        action: str,
        upside: float,
        methods: List[str],
        industry: str
    ) -> str:
        """Generate human-readable reason for recommendation"""
        method_str = ', '.join(methods)
        
        if action == "BUY":
            return (f"基于{industry or '该企业'}特征，采用{method_str}估值方法，"
                    f"显示{abs(upside):.1f}%上涨空间，建议买入。")
        elif action == "SELL":
            return (f"基于{industry or '该企业'}特征，采用{method_str}估值方法，"
                    f"显示{abs(upside):.1f}%下跌风险，建议卖出。")
        else:
            return (f"基于{industry or '该企业'}特征，采用{method_str}估值方法，"
                    f"显示{upside:.1f}%上涨空间，建议持有等待机会。")
    
    def generate_portfolio_report(
        self,
        recommendations: List[StockRecommendation]
    ) -> PortfolioReport:
        """
        Generate a complete portfolio report
        
        Args:
            recommendations: List of stock recommendations
            
        Returns:
            PortfolioReport object
        """
        # Calculate summary statistics
        total_stocks = len(recommendations)
        buy_count = sum(1 for r in recommendations if r.action == "BUY")
        hold_count = sum(1 for r in recommendations if r.action == "HOLD")
        sell_count = sum(1 for r in recommendations if r.action == "SELL")
        
        # Calculate average upside
        valid_upside = [r.upside for r in recommendations if r.upside != 0]
        avg_upside = sum(valid_upside) / len(valid_upside) if valid_upside else 0
        
        # Calculate portfolio metrics
        high_conf_recommendations = [r for r in recommendations if r.confidence == "HIGH"]
        high_conf_count = len(high_conf_recommendations)
        
        summary = {
            'total_stocks': total_stocks,
            'buy_count': buy_count,
            'hold_count': hold_count,
            'sell_count': sell_count,
            'average_upside': avg_upside,
            'high_confidence_count': high_conf_count,
            'action_distribution': {
                'BUY': buy_count,
                'HOLD': hold_count,
                'SELL': sell_count
            }
        }
        
        # Generate details for each stock
        details = []
        for rec in recommendations:
            details.append({
                'ticker': rec.ticker,
                'company_name': rec.company_name,
                'action': rec.action,
                'current_price': rec.current_price,
                'fair_value': rec.fair_value,
                'upside': rec.upside,
                'confidence': rec.confidence,
                'industry': rec.industry,
                'sector': rec.sector,
                'valuation_methods': rec.valuation_methods
            })
        
        # Sort recommendations by upside (highest first)
        sorted_recommendations = sorted(
            recommendations,
            key=lambda x: x.upside if x.upside else 0,
            reverse=True
        )
        
        return PortfolioReport(
            report_date=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            stocks_analyzed=total_stocks,
            recommendations=sorted_recommendations,
            summary=summary,
            details=details
        )
    
    def save_recommendation_to_db(self, recommendation: StockRecommendation) -> bool:
        """
        Save a recommendation to the database
        
        Args:
            recommendation: StockRecommendation to save
            
        Returns:
            bool: True if saved successfully
        """
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
                    recommendation.ticker,
                    recommendation.company_name,
                    recommendation.action,
                    recommendation.upside,
                    recommendation.confidence,
                    json.dumps(recommendation.valuation_methods),
                    recommendation.reason,
                    recommendation.industry,
                    recommendation.sector,
                    json.dumps(recommendation.details)
                ))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error saving recommendation: {e}")
            return False
    
    def get_latest_recommendations(self, limit: int = 20) -> List[StockRecommendation]:
        """
        Get latest recommendations from database
        
        Args:
            limit: Maximum number to return
            
        Returns:
            List of StockRecommendation objects
        """
        try:
            conn = db_service.get_connection()
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT * FROM portfolio_recommendations 
                    ORDER BY created_at DESC 
                    LIMIT %s
                """, (limit,))
                rows = cursor.fetchall()
                
                recommendations = []
                for row in rows:
                    recommendations.append(StockRecommendation(
                        ticker=row['ticker'],
                        company_name=row['company_name'],
                        action=row['action'],
                        upside=float(row['upside']) if row['upside'] else 0,
                        confidence=row['confidence'],
                        valuation_methods=json.loads(row['valuation_methods']) if row['valuation_methods'] else [],
                        primary_method=row['valuation_methods'].split(',')[0] if row['valuation_methods'] else 'DCF',
                        fair_value=0,  # Not stored in this table
                        current_price=None,
                        industry=row.get('industry', ''),
                        sector=row.get('sector', ''),
                        reason=row['reason'],
                        details=json.loads(row['details']) if row['details'] else {},
                        created_at=str(row['created_at'])
                    ))
                
                return recommendations
                
        except Exception as e:
            print(f"Error retrieving recommendations: {e}")
            return []
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        Get summary of current portfolio recommendations
        
        Returns:
            Dict with portfolio summary
        """
        try:
            conn = db_service.get_connection()
            with conn.cursor() as cursor:
                # Get latest recommendation for each ticker
                cursor.execute("""
                    SELECT r1.* FROM portfolio_recommendations r1
                    INNER JOIN (
                        SELECT ticker, MAX(created_at) as max_date
                        FROM portfolio_recommendations
                        GROUP BY ticker
                    ) r2 ON r1.ticker = r2.ticker AND r1.created_at = r2.max_date
                """)
                rows = cursor.fetchall()
                
                if not rows:
                    return {'stocks': 0, 'recommendations': {}}
                
                stats = {
                    'BUY': 0,
                    'HOLD': 0,
                    'SELL': 0
                }
                
                recommendations = {}
                for row in rows:
                    action = row['action']
                    stats[action] = stats.get(action, 0) + 1
                    recommendations[row['ticker']] = {
                        'action': action,
                        'upside': float(row['upside']) if row['upside'] else 0,
                        'confidence': row['confidence']
                    }
                
                return {
                    'stocks': len(rows),
                    'stats': stats,
                    'recommendations': recommendations
                }
                
        except Exception as e:
            print(f"Error getting portfolio summary: {e}")
            return {'stocks': 0, 'recommendations': {}}
    
    def to_dict(self, report: PortfolioReport) -> Dict[str, Any]:
        """Convert PortfolioReport to dictionary"""
        return {
            'report_date': report.report_date,
            'stocks_analyzed': report.stocks_analyzed,
            'recommendations': [
                {
                    'ticker': r.ticker,
                    'company_name': r.company_name,
                    'action': r.action,
                    'upside': r.upside,
                    'confidence': r.confidence,
                    'valuation_methods': r.valuation_methods,
                    'primary_method': r.primary_method,
                    'fair_value': r.fair_value,
                    'current_price': r.current_price,
                    'industry': r.industry,
                    'sector': r.sector,
                    'reason': r.reason
                }
                for r in report.recommendations
            ],
            'summary': report.summary,
            'details': report.details
        }


# Singleton instance
portfolio_service = PortfolioService()
