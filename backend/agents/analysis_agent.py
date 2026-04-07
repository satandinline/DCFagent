"""
Analysis Agent for DCF Valuation System

Specialized agent for financial analysis and valuation
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
import logging
import json

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from backend.agents.base_agent import BaseAgent, AgentResult, AgentCapability
from backend.tools.registry import tool_registry

logger = logging.getLogger(__name__)


class AnalysisAgent(BaseAgent):
    """
    Analysis Agent - Specialized for financial valuation and analysis
    
    Capabilities:
    - Industry classification (using LLM or rules)
    - DCF valuation
    - DDM valuation (for financial institutions)
    - Comparable company analysis
    - Valuation recommendation
    - Investment decision making
    
    Tools used:
    - industry_classification
    - dcf_valuation
    - ddm_valuation
    - comparable_analysis
    - sensitivity_analysis
    - llm_reasoner (optional, for enhanced analysis)
    """
    
    name = "analysis_agent"
    role = "Financial Analysis Specialist"
    description = "Performs DCF valuation and investment analysis"
    
    def _initialize_capabilities(self):
        """Initialize Analysis Agent capabilities"""
        self._capabilities = {
            AgentCapability.FINANCIAL_ANALYSIS,
            AgentCapability.VALUATION,
            AgentCapability.INDUSTRY_ANALYSIS,
            AgentCapability.LLM_REASONING,
        }
    
    def _initialize_tools(self):
        """Initialize Analysis Agent tools"""
        self._tools = [
            'industry_classification',
            'dcf_valuation',
            'ddm_valuation',
            'ps_valuation',
            'comparable_analysis',
            'sensitivity_analysis',
            'trend_analysis',
            'llm_reasoner',
        ]
    
    def _get_supported_task_types(self) -> List[str]:
        """Get list of supported task types"""
        return [
            'dcf_valuation',
            'ddm_valuation',
            'industry_classification',
            'comparable_analysis',
            'sensitivity_analysis',
            'recommend_valuation',
            'analyze_failure',
        ]
    
    def _execute_task(self, task: Dict[str, Any]) -> AgentResult:
        """
        Execute analysis-related task
        """
        task_type = task.get('type')
        
        if task_type == 'dcf_valuation':
            return self._perform_dcf_valuation(task)
        elif task_type == 'ddm_valuation':
            return self._perform_ddm_valuation(task)
        elif task_type == 'industry_classification':
            return self._classify_industry(task)
        elif task_type == 'comparable_analysis':
            return self._perform_comparable_analysis(task)
        elif task_type == 'sensitivity_analysis':
            return self._perform_sensitivity_analysis(task)
        elif task_type == 'recommend_valuation':
            return self._recommend_valuation_method(task)
        elif task_type == 'analyze_failure':
            return self._analyze_failure(task)
        else:
            return AgentResult(
                success=False,
                error=f"Unknown task type: {task_type}"
            )
    
    def _perform_dcf_valuation(self, task: Dict[str, Any]) -> AgentResult:
        """Perform DCF valuation"""
        ticker = task.get('ticker')
        financial_data = task.get('financial_data')
        
        if not ticker:
            return AgentResult(success=False, error="Ticker not provided")
        
        logger.info(f"Performing DCF valuation for {ticker}")
        
        # Use the DCF tool
        params = {
            'ticker': ticker,
        }
        
        if financial_data:
            params['financial_data'] = financial_data
        else:
            # Need to fetch data first - use DataAgent
            from backend.agents.data_agent import DataAgent
            data_agent = DataAgent()
            data_result = data_agent.run({'type': 'fetch_stock_data', 'ticker': ticker})
            
            if not data_result.success:
                return AgentResult(
                    success=False,
                    error=f"Failed to fetch data for {ticker}"
                )
            
            params['financial_data'] = data_result.data
        
        # Execute DCF valuation
        result = self.execute_tool('dcf_valuation', **params)
        
        if result and result.success:
            # Enhance with LLM reasoning if available
            enhanced_data = self._enhance_with_llm(result.data, ticker)
            
            return AgentResult(
                success=True,
                data=enhanced_data,
                metadata={
                    'ticker': ticker,
                    'method': 'DCF',
                    'fair_value': enhanced_data.get('per_share_value')
                }
            )
        else:
            return AgentResult(
                success=False,
                error=result.error if result else "DCF valuation failed"
            )
    
    def _enhance_with_llm(self, valuation_data: Dict, ticker: str) -> Dict[str, Any]:
        """Enhance valuation data with LLM reasoning"""
        try:
            llm_result = self.execute_tool(
                'llm_reasoner',
                task_type='explain_result',
                context={
                    'ticker': ticker,
                    **valuation_data
                }
            )
            
            if llm_result and llm_result.success:
                valuation_data['llm_explanation'] = llm_result.data
        except Exception as e:
            logger.warning(f"LLM enhancement failed: {e}")
        
        return valuation_data
    
    def _perform_ddm_valuation(self, task: Dict[str, Any]) -> AgentResult:
        """Perform DDM (Dividend Discount Model) valuation for financial institutions"""
        ticker = task.get('ticker')
        
        if not ticker:
            return AgentResult(success=False, error="Ticker not provided")
        
        logger.info(f"Performing DDM valuation for {ticker}")
        
        result = self.execute_tool('ddm_valuation', ticker=ticker)
        
        if result and result.success:
            return AgentResult(
                success=True,
                data=result.data,
                metadata={'ticker': ticker, 'method': 'DDM'}
            )
        else:
            return AgentResult(
                success=False,
                error=result.error if result else "DDM valuation failed"
            )
    
    def _classify_industry(self, task: Dict[str, Any]) -> AgentResult:
        """Classify company industry and recommend valuation method"""
        company_data = task.get('company_data', {})
        
        if not company_data:
            return AgentResult(success=False, error="Company data not provided")
        
        logger.info(f"Classifying industry for company")
        
        # Use LLM reasoner for intelligent classification
        result = self.execute_tool(
            'llm_reasoner',
            task_type='classify_industry',
            context=company_data
        )
        
        if result and result.success:
            return AgentResult(
                success=True,
                data=result.data,
                metadata={'method': 'LLM'}
            )
        else:
            # Fallback to rule-based classification
            fallback_result = self.execute_tool(
                'industry_classification',
                **company_data
            )
            
            if fallback_result and fallback_result.success:
                return AgentResult(
                    success=True,
                    data=fallback_result.data,
                    metadata={'method': 'rules'}
                )
            
            return AgentResult(
                success=False,
                error="Industry classification failed"
            )
    
    def _perform_comparable_analysis(self, task: Dict[str, Any]) -> AgentResult:
        """Perform comparable company analysis"""
        ticker = task.get('ticker')
        
        if not ticker:
            return AgentResult(success=False, error="Ticker not provided")
        
        logger.info(f"Performing comparable analysis for {ticker}")
        
        result = self.execute_tool('comparable_analysis', ticker=ticker)
        
        if result and result.success:
            return AgentResult(
                success=True,
                data=result.data,
                metadata={'ticker': ticker, 'method': 'comparable'}
            )
        else:
            return AgentResult(
                success=False,
                error=result.error if result else "Comparable analysis failed"
            )
    
    def _perform_sensitivity_analysis(self, task: Dict[str, Any]) -> AgentResult:
        """Perform sensitivity analysis on valuation"""
        base_valuation = task.get('base_valuation')
        
        if not base_valuation:
            return AgentResult(success=False, error="Base valuation not provided")
        
        logger.info("Performing sensitivity analysis")
        
        result = self.execute_tool('sensitivity_analysis', **base_valuation)
        
        if result and result.success:
            return AgentResult(
                success=True,
                data=result.data,
                metadata={'method': 'sensitivity'}
            )
        else:
            return AgentResult(
                success=False,
                error=result.error if result else "Sensitivity analysis failed"
            )
    
    def _recommend_valuation_method(self, task: Dict[str, Any]) -> AgentResult:
        """Recommend the best valuation method based on company characteristics"""
        company_data = task.get('company_data', {})
        
        if not company_data:
            return AgentResult(success=False, error="Company data not provided")
        
        logger.info("Recommending valuation method")
        
        result = self.execute_tool(
            'llm_reasoner',
            task_type='recommend_valuation',
            context=company_data
        )
        
        if result and result.success:
            return AgentResult(
                success=True,
                data=result.data,
                metadata={'method': 'LLM'}
            )
        else:
            # Rule-based fallback
            return self._rule_based_recommendation(company_data)
    
    def _rule_based_recommendation(self, company_data: Dict) -> AgentResult:
        """Fallback rule-based valuation method recommendation"""
        industry = company_data.get('industry', '').lower()
        is_profitable = company_data.get('is_profitable', True)
        has_dividends = company_data.get('has_dividends', False)
        
        # Financial institutions
        if any(kw in industry for kw in ['bank', 'insurance', 'financial']):
            methods = ['DDM', 'P/B']
        # High growth / unprofitable
        elif not is_profitable:
            methods = ['P/S', 'EV/Revenue']
        # Default
        else:
            methods = ['DCF', 'EV/EBITDA']
        
        return AgentResult(
            success=True,
            data={
                'recommended_methods': methods,
                'method_weights': {m: 1.0/len(methods) for m in methods},
                'reasoning': 'Rule-based recommendation'
            }
        )
    
    def _analyze_failure(self, task: Dict[str, Any]) -> AgentResult:
        """Analyze why a valuation failed and recommend alternatives"""
        failed_method = task.get('failed_method')
        context = task.get('context', {})
        
        logger.info(f"Analyzing failure of {failed_method}")
        
        result = self.execute_tool(
            'llm_reasoner',
            task_type='analyze_failure',
            context={
                'failed_method': failed_method,
                **context
            }
        )
        
        if result and result.success:
            return AgentResult(
                success=True,
                data=result.data,
                metadata={'failed_method': failed_method}
            )
        else:
            # Fallback recommendations
            alternatives = {
                'DCF': ['EV/EBITDA', 'P/E', 'Comparable'],
                'DDM': ['DCF', 'P/B'],
                'P/S': ['EV/Revenue', 'DCF']
            }
            
            return AgentResult(
                success=True,
                data={
                    'alternative_methods': alternatives.get(failed_method, ['DCF']),
                    'recommended_approach': 'Use relative valuation'
                }
            )
    
    def analyze(self, ticker: str, data: Dict[str, Any]) -> AgentResult:
        """
        Full analysis workflow for a company
        
        This is a convenience method that runs a complete analysis pipeline
        """
        logger.info(f"Running full analysis for {ticker}")
        
        # Step 1: Classify industry
        industry_result = self._classify_industry({'company_data': data})
        
        # Step 2: Determine valuation method
        if industry_result.success:
            primary_method = industry_result.data.get('primary_method', 'DCF')
        else:
            primary_method = 'DCF'
        
        # Step 3: Perform valuation
        valuation_result = None
        method_tried = []
        
        for method in [primary_method] + ['DCF', 'EV/EBITDA']:
            if method in method_tried:
                continue
                
            method_tried.append(method)
            
            if method == 'DCF':
                valuation_result = self._perform_dcf_valuation({
                    'ticker': ticker,
                    'financial_data': data
                })
            elif method == 'DDM':
                valuation_result = self._perform_ddm_valuation({'ticker': ticker})
            
            if valuation_result and valuation_result.success:
                break
        
        # Step 4: Get investment recommendation
        if valuation_result and valuation_result.success:
            recommendation = self._get_investment_recommendation(
                ticker,
                valuation_result.data
            )
        else:
            recommendation = None
        
        # Compile results
        return AgentResult(
            success=valuation_result.success if valuation_result else False,
            data={
                'ticker': ticker,
                'industry': industry_result.data if industry_result.success else None,
                'valuation': valuation_result.data if valuation_result else None,
                'recommendation': recommendation,
                'methods_tried': method_tried
            },
            metadata={
                'success': valuation_result.success if valuation_result else False
            }
        )
    
    def _get_investment_recommendation(self, ticker: str, valuation_data: Dict) -> Dict[str, Any]:
        """Generate investment recommendation based on valuation"""
        try:
            result = self.execute_tool(
                'llm_reasoner',
                task_type='decide_action',
                context={
                    'ticker': ticker,
                    **valuation_data
                }
            )
            
            if result and result.success:
                return result.data
        except Exception as e:
            logger.warning(f"LLM recommendation failed: {e}")
        
        # Fallback rule-based recommendation
        upside = valuation_data.get('upside_percent', 0)
        
        if upside > 20:
            action = 'BUY'
        elif upside > -10:
            action = 'HOLD'
        else:
            action = 'SELL'
        
        return {
            'action': action,
            'confidence': 'medium',
            'reasoning': f'Upside of {upside:.1f}% leads to {action}'
        }
