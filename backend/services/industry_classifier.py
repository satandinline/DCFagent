"""
Industry Classifier Service for DCF Valuation Agent
Automatically identifies industry type and selects appropriate valuation models
"""
from enum import Enum
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))


class IndustryType(Enum):
    """Industry classification types"""
    MANUFACTURING_CONSUMER = "manufacturing_consumer"  # 现金流稳定企业（制造、消费）
    FINANCIAL_INSTITUTION = "financial_institution"    # 金融机构（银行、保险）
    HIGH_GROWTH_LOSS = "high_growth_loss"             # 高增长未盈利（SaaS）
    DIVERSIFIED_GROUP = "diversified_group"            # 多元化集团
    TECHNOLOGY = "technology"                           # 科技公司
    UNKNOWN = "unknown"                                 # 未知


@dataclass
class ValuationRecommendation:
    """Recommended valuation approach for an industry"""
    primary_method: str
    secondary_methods: List[str]
    confidence: str  # HIGH, MEDIUM, LOW
    reasoning: str


class IndustryClassifier:
    """
    Classifier that identifies company industry type and recommends valuation models
    
    Industry Classification Rules:
    | 行业类型              | 特征                          | 推荐估值模型                    |
    |---------------------|-------------------------------|-------------------------------|
    | 现金流稳定企业（制造、消费）| 有稳定现金流和利润              | DCF + EV/EBITDA               |
    | 金融机构（银行、保险）    | 营运资本难定义，有股息           | DDM + P/B                     |
    | 高增长未盈利（SaaS）    | 未盈利或低盈利，高增长           | P/S 或超长期DCF                |
    | 多元化集团            | 多业务板块                     | SOTP（分类加总法）              |
    """
    
    # Keywords for identifying industry types
    FINANCIAL_KEYWORDS = [
        'bank', 'banking', 'insurance', 'financial services', 'investment',
        'capital markets', 'securities', 'asset management', 'trust',
        'credit', 'lending', 'fintech', 'finance'
    ]
    
    HIGH_GROWTH_KEYWORDS = [
        'saas', 'software', 'cloud', 'technology', 'internet', 'digital',
        'platform', 'subscription', 'app'
    ]
    
    DIVERSIFIED_KEYWORDS = [
        'conglomerate', 'holdings', 'diversified', 'multi-industry',
        'group', 'industrial', 'diversified holdings'
    ]
    
    MANUFACTURING_CONSUMER_KEYWORDS = [
        'manufacturing', 'consumer', 'retail', 'food', 'beverage', 'automotive',
        'electronics', ' appliances', 'clothing', 'textile', 'packaging',
        'chemical', 'materials', 'industrial', 'machinery', 'equipment'
    ]
    
    def __init__(self):
        self.industry_keywords = {
            IndustryType.FINANCIAL_INSTITUTION: self.FINANCIAL_KEYWORDS,
            IndustryType.HIGH_GROWTH_LOSS: self.HIGH_GROWTH_KEYWORDS,
            IndustryType.DIVERSIFIED_GROUP: self.DIVERSIFIED_KEYWORDS,
            IndustryType.MANUFACTURING_CONSUMER: self.MANUFACTURING_CONSUMER_KEYWORDS,
        }
    
    def classify(
        self,
        sector: str = None,
        industry: str = None,
        company_name: str = None,
        is_profitable: bool = True,
        has_dividends: bool = False,
        revenue_growth: float = 0,
        net_income: float = 0
    ) -> Tuple[IndustryType, ValuationRecommendation]:
        """
        Classify the company and recommend valuation models
        
        Args:
            sector: Company sector (e.g., 'Technology', 'Financial Services')
            industry: Specific industry (e.g., 'Software', 'Banks')
            company_name: Company name for additional context
            is_profitable: Whether company is currently profitable
            has_dividends: Whether company pays dividends
            revenue_growth: Revenue growth rate (as decimal, e.g., 0.25 for 25%)
            net_income: Net income (can be negative)
            
        Returns:
            Tuple of (IndustryType, ValuationRecommendation)
        """
        # Combine text for searching
        search_text = ' '.join([
            sector or '',
            industry or '',
            company_name or ''
        ]).lower()
        
        # Rule 1: Check for financial institutions
        if self._matches_keywords(search_text, self.FINANCIAL_KEYWORDS):
            return self._classify_financial(has_dividends)
        
        # Rule 2: Check for high-growth/losing companies
        if self._is_high_growth_loss(search_text, is_profitable, revenue_growth, net_income):
            return self._classify_high_growth()
        
        # Rule 3: Check for diversified groups
        if self._matches_keywords(search_text, self.DIVERSIFIED_KEYWORDS):
            return self._classify_diversified()
        
        # Rule 4: Check for manufacturing/consumer
        if self._matches_keywords(search_text, self.MANUFACTURING_CONSUMER_KEYWORDS):
            return self._classify_manufacturing_consumer()
        
        # Rule 5: Technology companies (often high growth)
        if self._matches_keywords(search_text, self.HIGH_GROWTH_KEYWORDS):
            if not is_profitable or revenue_growth > 0.2:
                return self._classify_high_growth()
            else:
                # Profitable tech can use DCF
                return self._classify_manufacturing_consumer()
        
        # Default classification based on profitability
        if is_profitable:
            return self._classify_manufacturing_consumer()
        else:
            return self._classify_high_growth()
    
    def _matches_keywords(self, text: str, keywords: List[str]) -> bool:
        """Check if text contains any of the keywords"""
        for keyword in keywords:
            if keyword in text:
                return True
        return False
    
    def _is_high_growth_loss(
        self,
        text: str,
        is_profitable: bool,
        revenue_growth: float,
        net_income: float
    ) -> bool:
        """Determine if company is high-growth with losses"""
        # Non-profitable with high revenue growth
        if not is_profitable and revenue_growth > 0.15:
            return True
        
        # Significant net loss
        if net_income < 0 and abs(net_income) > 100000000:  # > 100M loss
            if revenue_growth > 0.1:
                return True
        
        return False
    
    def _classify_financial(self, has_dividends: bool) -> Tuple[IndustryType, ValuationRecommendation]:
        """Classify as financial institution"""
        if has_dividends:
            return (
                IndustryType.FINANCIAL_INSTITUTION,
                ValuationRecommendation(
                    primary_method="DDM",
                    secondary_methods=["P/B", "DCF"],
                    confidence="HIGH",
                    reasoning="金融机构特征：营运资本难以定义。DDM适合有股息支付的银行和保险公司，P/B提供相对估值参考。"
                )
            )
        else:
            return (
                IndustryType.FINANCIAL_INSTITUTION,
                ValuationRecommendation(
                    primary_method="P/B",
                    secondary_methods=["DCF", "EV/EBITDA"],
                    confidence="MEDIUM",
                    reasoning="金融机构特征：P/B适合评估银行和保险公司的账面价值，DCF和EV/EBITDA作为补充。"
                )
            )
    
    def _classify_high_growth(self) -> Tuple[IndustryType, ValuationRecommendation]:
        """Classify as high-growth unprofitable company"""
        return (
            IndustryType.HIGH_GROWTH_LOSS,
            ValuationRecommendation(
                primary_method="P/S",
                secondary_methods=["超长期DCF", "EV/Revenue"],
                confidence="MEDIUM",
                reasoning="高增长未盈利企业（如SaaS）：传统DCF不适用，P/S（市销率）更合适。可结合极长期的多阶段DCF。"
            )
        )
    
    def _classify_diversified(self) -> Tuple[IndustryType, ValuationRecommendation]:
        """Classify as diversified group"""
        return (
            IndustryType.DIVERSIFIED_GROUP,
            ValuationRecommendation(
                primary_method="SOTP",
                secondary_methods=["DCF", "EV/EBITDA"],
                confidence="MEDIUM",
                reasoning="多元化集团：各业务板块应分别估值后加总（SOTP），识别各业务板块采用合适的估值方法。"
            )
        )
    
    def _classify_manufacturing_consumer(self) -> Tuple[IndustryType, ValuationRecommendation]:
        """Classify as stable cash flow business"""
        return (
            IndustryType.MANUFACTURING_CONSUMER,
            ValuationRecommendation(
                primary_method="DCF",
                secondary_methods=["EV/EBITDA", "P/E"],
                confidence="HIGH",
                reasoning="现金流稳定企业（制造、消费）：适合使用DCF绝对估值，结合EV/EBITDA可比法进行相对估值验证。"
            )
        )
    
    def get_valuation_methods(self, industry_type: IndustryType) -> List[str]:
        """Get valuation methods for an industry type"""
        method_map = {
            IndustryType.FINANCIAL_INSTITUTION: ["DDM", "P/B", "DCF"],
            IndustryType.HIGH_GROWTH_LOSS: ["P/S", "EV/Revenue", "超长期DCF"],
            IndustryType.DIVERSIFIED_GROUP: ["SOTP", "DCF", "EV/EBITDA"],
            IndustryType.MANUFACTURING_CONSUMER: ["DCF", "EV/EBITDA", "P/E"],
            IndustryType.TECHNOLOGY: ["DCF", "P/S", "EV/Revenue"],
            IndustryType.UNKNOWN: ["DCF", "EV/EBITDA", "P/S"],
        }
        return method_map.get(industry_type, ["DCF"])


# Singleton instance
industry_classifier = IndustryClassifier()


def classify_company(company_data: Dict) -> Tuple[IndustryType, ValuationRecommendation]:
    """
    Convenience function to classify a company
    
    Args:
        company_data: Dict containing:
            - sector: Company sector
            - industry: Specific industry
            - company_name: Company name
            - is_profitable: Whether profitable
            - has_dividends: Whether pays dividends
            - revenue_growth: Revenue growth rate
            - net_income: Net income
            
    Returns:
        Tuple of (IndustryType, ValuationRecommendation)
    """
    return industry_classifier.classify(
        sector=company_data.get('sector'),
        industry=company_data.get('industry'),
        company_name=company_data.get('company_name'),
        is_profitable=company_data.get('is_profitable', True),
        has_dividends=company_data.get('has_dividends', False),
        revenue_growth=company_data.get('revenue_growth', 0),
        net_income=company_data.get('net_income', 0)
    )
