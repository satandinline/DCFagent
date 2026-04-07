"""
LLM Reasoner Tool for DCF Valuation Agent
Uses MiniMax LLM for intelligent reasoning, classification and decision making
"""
from __future__ import annotations
from typing import Dict, Any, List, Optional
import logging
import time
import json
import re

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))

from backend.tools.base import (
    BaseTool, ToolCategory, ToolResult,
    ToolParameter, ToolCapability
)

logger = logging.getLogger(__name__)


class LLMReasonerTool(BaseTool):
    """
    LLM驱动的推理工具，用于：
    1. 智能行业分类（替代规则匹配）
    2. 估值方法推荐
    3. 投资决策建议生成
    4. 复杂情况分析
    """
    
    @property
    def name(self) -> str:
        return "llm_reasoner"
    
    @property
    def description(self) -> str:
        return "使用MiniMax LLM进行智能推理、行业分类和估值方法推荐"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.ANALYST
    
    @property
    def capabilities(self) -> List[str]:
        return [
            ToolCapability.INDUSTRY_CLASSIFICATION,
            ToolCapability.DCF_VALUATION
        ]
    
    def __init__(self):
        super().__init__()
        self._parameters = [
            ToolParameter(
                name="task_type",
                type="string",
                description="任务类型：classify_industry/recommend_valuation/decide_action/explain_result",
                required=True
            ),
            ToolParameter(
                name="context",
                type="object",
                description="任务上下文数据",
                required=True
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        task_type = kwargs.get('task_type')
        context = kwargs.get('context', {})
        
        try:
            if task_type == 'classify_industry':
                result = self._classify_industry(context)
            elif task_type == 'recommend_valuation':
                result = self._recommend_valuation(context)
            elif task_type == 'decide_action':
                result = self._decide_action(context)
            elif task_type == 'explain_result':
                result = self._explain_result(context)
            elif task_type == 'analyze_failure':
                result = self._analyze_failure(context)
            elif task_type == 'select_alternative':
                result = self._select_alternative(context)
            else:
                result = self._general_reasoning(context)
            
            execution_time = time.time() - start_time
            self._track_execution(execution_time)
            
            return ToolResult(
                success=True,
                data=result,
                metadata={
                    'task_type': task_type,
                    'llm_model': 'MiniMax-M2.7-highspeed'
                },
                execution_time=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            logger.error(f"LLM reasoner error: {e}")
            return ToolResult(
                success=False,
                error=str(e),
                tool_name=self.name
            )
    
    def _call_llm(self, prompt: str, system_prompt: str = None) -> str:
        """Call MiniMax LLM API"""
        try:
            from openai import OpenAI
            from backend.config import MINIMAX_API_KEY, MINIMAX_BASE_URL, MINIMAX_MODEL
            
            if not MINIMAX_API_KEY:
                # Fallback to simple rule-based reasoning
                return self._fallback_reasoning(prompt)
            
            client = OpenAI(
                api_key=MINIMAX_API_KEY,
                base_url=MINIMAX_BASE_URL
            )
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat.completions.create(
                model=MINIMAX_MODEL,
                messages=messages,
                temperature=0.3,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.warning(f"LLM API call failed: {e}, using fallback")
            return self._fallback_reasoning(prompt)
    
    def _classify_industry(self, context: Dict) -> Dict[str, Any]:
        """LLM-driven industry classification"""
        
        prompt = f"""分析以下公司信息，判断其行业类型并推荐合适的估值方法。

公司信息：
- 公司名称: {context.get('company_name', '未知')}
- 行业: {context.get('industry', '未知')}
- 板块: {context.get('sector', '未知')}
- 是否盈利: {'是' if context.get('is_profitable', True) else '否'}
- 净利润: {context.get('net_income', 0):,.0f}
- 收入增长: {context.get('revenue_growth', 0)*100:.1f}%
- 是否有股息: {'是' if context.get('has_dividends', False) else '否'}
- 描述: {context.get('description', '无')}

行业类型选项：
1. manufacturing_consumer (制造业/消费) - 有稳定现金流和利润
2. financial_institution (金融机构) - 银行、保险等，营运资本难定义
3. high_growth_loss (高增长亏损) - SaaS、科技等，未盈利或低盈利
4. diversified_group (多元化集团) - 多业务板块
5. technology (科技) - 科技公司

估值方法选项：
- DCF: 现金流折现，适合稳定现金流
- DDM: 股息贴现模型，适合金融机构
- P/S: 市销率，适合未盈利高增长
- P/B: 市净率，适合金融机构
- EV/EBITDA: 企业价值倍数，适合稳定盈利
- SOTP: 分类加总法，适合多元化集团

请以JSON格式输出：
{{
    "industry_type": "选择上述行业类型之一",
    "industry_type_name": "行业中文名",
    "reasoning": "推理过程简述",
    "confidence": "高/中/低",
    "primary_method": "主估值方法",
    "secondary_methods": ["次估值方法列表"],
    "warnings": ["需要关注的异常情况，如果有的话"]
}}"""
        
        system_prompt = """你是一位专业的金融分析师，擅长对公司进行行业分类和估值方法选择。
请仔细分析公司信息，给出准确的分类和推荐。你的回答应该简洁且专业。"""
        
        response = self._call_llm(prompt, system_prompt)
        
        # Parse JSON response
        try:
            # Extract JSON from response
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = json.loads(response)
        except:
            # Fallback to rule-based if JSON parsing fails
            result = self._rule_based_classification(context)
        
        return result
    
    def _recommend_valuation(self, context: Dict) -> Dict[str, Any]:
        """Recommend valuation methods with LLM reasoning"""
        
        prompt = f"""基于以下公司信息，推荐合适的估值方法组合并给出理由。

公司信息：
- 行业类型: {context.get('industry_type', '未知')}
- 当前股价: {context.get('current_price', 0):.2f}
- 目标价: {context.get('target_price', 0):.2f}
- 上涨空间: {context.get('upside', 0):.1f}%
- 置信度: {context.get('confidence', '中')}

历史分析（如有）：
{context.get('history_context', '无历史数据')}

请输出：
{{
    "recommended_methods": ["方法1", "方法2"],
    "method_weights": {{"方法1": 0.6, "方法2": 0.4}},
    "reasoning": "推荐理由",
    "expected_accuracy": "高/中/低",
    "alternative_if_failed": "如果主方法失败，备用方法"
}}"""
        
        response = self._call_llm(prompt)
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {"recommended_methods": ["DCF", "EV/EBITDA"], "reasoning": "默认推荐"}
        except:
            result = {"recommended_methods": ["DCF", "EV/EBITDA"], "reasoning": "默认推荐"}
        
        return result
    
    def _decide_action(self, context: Dict) -> Dict[str, Any]:
        """Decide investment action with LLM reasoning"""
        
        prompt = f"""基于以下分析结果，做出投资决策。

分析数据：
- 股票代码: {context.get('ticker', '未知')}
- 当前价格: ${context.get('current_price', 0):.2f}
- 估值价格: ${context.get('fair_value', 0):.2f}
- 上涨空间: {context.get('upside_percent', 0):.1f}%
- 置信度: {context.get('confidence', '中')}
- 行业: {context.get('industry', '未知')}

估值详情：
{json.dumps(context.get('valuation_details', {}), indent=2, ensure_ascii=False)}

市场环境：{context.get('market_conditions', '未指定')}

请给出最终投资建议：
{{
    "action": "BUY/HOLD/SELL",
    "confidence": "高/中/低",
    "target_price": 目标价格,
    "stop_loss": 止损价格,
    "reasoning": "决策理由",
    "risk_factors": ["风险因素列表"],
    "time_horizon": "短期/中期/长期"
}}"""
        
        response = self._call_llm(prompt)
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {"action": "HOLD", "reasoning": "数据不足，默认持有"}
        except:
            result = {"action": "HOLD", "reasoning": "LLM解析失败，默认持有"}
        
        return result
    
    def _explain_result(self, context: Dict) -> Dict[str, Any]:
        """Explain valuation result in natural language"""
        
        prompt = f"""用通俗易懂的语言解释以下DCF估值结果：

估值结果：
- 每股价值: ${context.get('per_share_value', 0):.2f}
- 当前价格: ${context.get('current_price', 0):.2f}
- 上涨空间: {context.get('upside_percent', 0):.1f}%
- WACC: {context.get('wacc', 0)*100:.1f}%
- 永续增长率: {context.get('terminal_growth', 0)*100:.1f}%

预测数据：
{json.dumps(context.get('projections', []), indent=2, ensure_ascii=False)}

请生成一段简洁的分析报告，帮助投资者理解决策依据。"""
        
        explanation = self._call_llm(prompt)
        
        return {
            "explanation": explanation,
            "key_highlights": self._extract_highlights(context)
        }
    
    def _analyze_failure(self, context: Dict) -> Dict[str, Any]:
        """Analyze why a valuation method failed and suggest alternatives"""
        
        prompt = f"""分析以下估值失败情况，并给出解决方案：

失败信息：
- 失败方法: {context.get('failed_method', '未知')}
- 错误原因: {context.get('error', '未知')}
- 公司信息: {context.get('company_info', {})}

请输出：
{{
    "root_cause": "根本原因分析",
    "alternative_methods": ["替代方法1", "替代方法2"],
    "recommended_approach": "推荐的处理方式",
    "should_retry": true/false,
    "retry_strategy": "如果重试，应该如何调整"
}}"""
        
        response = self._call_llm(prompt)
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {"alternative_methods": ["P/S", "EV/Revenue"], "recommended_approach": "使用相对估值"}
        except:
            result = {"alternative_methods": ["P/S", "EV/Revenue"], "recommended_approach": "使用相对估值"}
        
        return result
    
    def _select_alternative(self, context: Dict) -> Dict[str, Any]:
        """Select alternative valuation when primary fails"""
        
        prompt = f"""当主要估值方法失败时，选择替代方法。

情况：
- 主要方法: {context.get('primary_method', 'DCF')}
- 失败原因: {context.get('failure_reason', '未知')}
- 可用数据: {list(context.get('available_data', {}).keys())}
- 行业: {context.get('industry', '未知')}

请选择最合适的替代估值方法：
{{
    "selected_method": "替代方法",
    "confidence": "选择置信度",
    "adjusted_parameters": {{"参数调整建议"}},
    "expected_accuracy": "预期准确性"
}}"""
        
        response = self._call_llm(prompt)
        
        try:
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
            else:
                result = {"selected_method": "P/S", "confidence": "中"}
        except:
            result = {"selected_method": "P/S", "confidence": "中"}
        
        return result
    
    def _general_reasoning(self, context: Dict) -> Dict[str, Any]:
        """General LLM reasoning for complex situations"""
        
        prompt = f"""分析以下情况并给出建议：

情况描述：{context.get('description', '无')}

相关数据：{json.dumps(context.get('data', {}), indent=2, ensure_ascii=False)}

请给出你的分析和建议。"""
        
        response = self._call_llm(prompt)
        
        return {
            "reasoning": response,
            "conclusion": self._extract_conclusion(response)
        }
    
    def _rule_based_classification(self, context: Dict) -> Dict[str, Any]:
        """Fallback rule-based classification when LLM fails"""
        
        industry = (context.get('industry', '') + ' ' + context.get('sector', '')).lower()
        is_profitable = context.get('is_profitable', True)
        has_dividends = context.get('has_dividends', False)
        revenue_growth = context.get('revenue_growth', 0)
        
        # Financial keywords
        financial_keywords = ['bank', 'banking', 'insurance', 'financial', 'securities', 'investment']
        if any(kw in industry for kw in financial_keywords):
            return {
                "industry_type": "financial_institution",
                "industry_type_name": "金融机构",
                "reasoning": "基于关键词识别为金融机构",
                "confidence": "高",
                "primary_method": "DDM",
                "secondary_methods": ["P/B", "DCF"],
                "warnings": []
            }
        
        # High growth / loss making
        if not is_profitable and revenue_growth > 0.15:
            return {
                "industry_type": "high_growth_loss",
                "industry_type_name": "高增长亏损企业",
                "reasoning": "未盈利但收入高增长",
                "confidence": "中",
                "primary_method": "P/S",
                "secondary_methods": ["EV/Revenue", "超长期DCF"],
                "warnings": ["公司尚未盈利，风险较高"]
            }
        
        # Diversified
        diversified_keywords = ['conglomerate', 'holdings', 'diversified', 'group']
        if any(kw in industry for kw in diversified_keywords):
            return {
                "industry_type": "diversified_group",
                "industry_type_name": "多元化集团",
                "reasoning": "识别为多元化集团",
                "confidence": "中",
                "primary_method": "SOTP",
                "secondary_methods": ["DCF", "EV/EBITDA"],
                "warnings": []
            }
        
        # Default: manufacturing/consumer
        return {
            "industry_type": "manufacturing_consumer",
            "industry_type_name": "制造业/消费",
            "reasoning": "默认分类",
            "confidence": "中",
            "primary_method": "DCF",
            "secondary_methods": ["EV/EBITDA", "P/E"],
            "warnings": []
        }
    
    def _fallback_reasoning(self, prompt: str) -> str:
        """Simple fallback when LLM is not available"""
        return json.dumps({
            "action": "HOLD",
            "reasoning": "LLM暂时不可用，默认持有策略"
        })
    
    def _extract_highlights(self, context: Dict) -> List[str]:
        """Extract key highlights from context"""
        highlights = []
        
        if context.get('upside_percent', 0) > 20:
            highlights.append("上涨空间超过20%，值得关注")
        elif context.get('upside_percent', 0) < -10:
            highlights.append("存在下跌风险，需要谨慎")
        
        if context.get('confidence') == '高':
            highlights.append("当前分析置信度较高")
        
        return highlights
    
    def _extract_conclusion(self, response: str) -> str:
        """Extract conclusion from LLM response"""
        lines = response.strip().split('\n')
        if lines:
            return lines[-1][:200]
        return response[:200]


class LLMJudgeTool(BaseTool):
    """
    LLM Judge Tool - 用于评估和验证其他工具输出的质量
    """
    
    @property
    def name(self) -> str:
        return "llm_judge"
    
    @property
    def description(self) -> str:
        return "使用LLM评估分析结果的质量和可靠性"
    
    @property
    def category(self) -> ToolCategory:
        return ToolCategory.ANALYST
    
    def __init__(self):
        super().__init__()
        self._parameters = [
            ToolParameter(
                name="content_to_judge",
                type="string",
                description="需要评判的内容",
                required=True
            ),
            ToolParameter(
                name="criteria",
                type="array",
                description="评判标准列表",
                required=False,
                default=["准确性", "完整性", "专业性"]
            )
        ]
    
    def execute(self, **kwargs) -> ToolResult:
        start_time = time.time()
        
        content = kwargs.get('content_to_judge', '')
        criteria = kwargs.get('criteria', ['准确性', '完整性'])
        
        prompt = f"""请评估以下分析报告的质量：

待评估内容：
{content}

评判标准：{', '.join(criteria)}

请给出1-10分的评分和简要评价。"""
        
        llm_reasoner = LLMReasonerTool()
        response = llm_reasoner._call_llm(prompt)
        
        execution_time = time.time() - start_time
        
        return ToolResult(
            success=True,
            data={'evaluation': response, 'criteria': criteria},
            execution_time=execution_time,
            tool_name=self.name
        )


def register_llm_reasoner_tools():
    """Register LLM reasoner tools"""
    from backend.tools.registry import tool_registry
    
    tools = [
        LLMReasonerTool(),
        LLMJudgeTool()
    ]
    
    for tool in tools:
        tool_registry.register(tool)
    
    return tools
