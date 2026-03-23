from __future__ import annotations

import json
import logging
import re
from typing import Any

from openai import AsyncOpenAI

from config import MINIMAX_API_KEY, MINIMAX_BASE_URL, MINIMAX_MODEL

logger = logging.getLogger(__name__)

EXTRACTION_SYSTEM_PROMPT = """\
你是一位资深财务分析师AI。你的任务是从财务报告文本中提取结构化财务数据。

请仔细阅读文本，找到以下关键数据并以JSON格式返回：

{
  "company_name": "公司全称",
  "ticker": "股票代码(如300390)，找不到则为null",
  "currency": "CNY",
  "fiscal_year": 报告年度(整数，如2025),
  "revenue": 营业收入(元，浮点数),
  "revenue_growth": 营收同比增长率(小数，如0.1423表示14.23%),
  "operating_income": 营业利润(元),
  "operating_margin": 营业利润率(小数),
  "net_income": 归属于上市公司股东的净利润(元),
  "depreciation_amortization": 折旧与摊销(元，从固定资产折旧+无形资产摊销推算),
  "capital_expenditure": 资本支出(元，购建固定资产/无形资产等支付的现金),
  "change_in_working_capital": 营运资本变动(元),
  "total_debt": 总债务(短期借款+长期借款+一年内到期的非流动负债+应付债券)(元),
  "cash_and_equivalents": 货币资金(元),
  "shares_outstanding": 总股本/流通股数(股),
  "tax_rate": 有效税率(小数，如0.25),
  "beta": Beta系数(找不到则使用1.0),
  "risk_free_rate": 无风险利率(小数，默认0.025),
  "market_return": 市场预期回报率(小数，默认0.09),
  "cost_of_debt": 债务成本(小数，从利息支出/总债务推算，默认0.045),
  "current_stock_price": 当前股价(找不到则为null)
}

重要规则：
- 所有金额单位必须统一为"元"（人民币元）
- 如果报告中金额单位是"万元"，需要乘以10000转换为"元"
- 如果报告中金额单位是"亿元"，需要乘以100000000转换为"元"
- 比率用小数表示，不用百分比（如14.23%应写为0.1423）
- 如果某个值在报告中找不到，请基于其他数据合理估算
- 只返回JSON对象，不要包含markdown代码块或额外文字
"""

NARRATIVE_SYSTEM_PROMPT = """\
You are a senior equity research analyst. Write a professional DCF valuation \
narrative analysis based on the financial data and DCF results provided.

Your analysis should cover:
1. Company overview and key financial metrics
2. Revenue and profitability trends
3. WACC assumptions and justification
4. Free cash flow projections summary
5. Terminal value methodology
6. Valuation conclusion with fair value per share
7. Key risks and sensitivities

Write in the same language as the input data. Be concise yet thorough. \
Use professional financial language.
"""


class LLMService:
    def __init__(self) -> None:
        self.client = AsyncOpenAI(
            api_key=MINIMAX_API_KEY,
            base_url=MINIMAX_BASE_URL,
        )
        self.model = MINIMAX_MODEL

    @staticmethod
    def _extract_json(raw: str) -> dict[str, Any]:
        """Extract JSON from LLM output, stripping thinking tags and code fences."""
        text = raw.strip()
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()

        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)

        match = re.search(r"\{[\s\S]*\}", text)
        if match:
            return json.loads(match.group())

        return json.loads(text)

    async def extract_financial_data(self, text: str) -> dict[str, Any]:
        truncated = text[:28000]
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": (
                            "请从以下财务报告中提取关键财务数据：\n\n"
                            f"{truncated}"
                        ),
                    },
                ],
                temperature=0.1,
                max_tokens=16000,
            )
            raw = response.choices[0].message.content or ""
            logger.info("LLM response length: %d chars", len(raw))
            data = self._extract_json(raw)
            logger.info("LLM extraction succeeded: %s", data.get("company_name", "Unknown"))
            return data
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse LLM JSON response: %s\nRaw (last 500): %s", exc, raw[-500:])
            raise ValueError(f"LLM returned invalid JSON: {exc}") from exc
        except Exception as exc:
            logger.error("LLM extraction failed: %s", exc)
            raise

    @staticmethod
    def _strip_think_tags(raw: str) -> str:
        """Remove <think>...</think> blocks from the response."""
        return re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()

    async def generate_narrative(
        self,
        financial_data: dict[str, Any],
        dcf_result: dict[str, Any],
    ) -> str:
        try:
            user_content = (
                "Financial Data:\n"
                f"{json.dumps(financial_data, ensure_ascii=False, indent=2)}\n\n"
                "DCF Valuation Results:\n"
                f"{json.dumps(dcf_result, ensure_ascii=False, indent=2)}"
            )
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": NARRATIVE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.4,
                max_tokens=16000,
            )
            raw = response.choices[0].message.content or ""
            return self._strip_think_tags(raw)
        except Exception as exc:
            logger.error("Narrative generation failed: %s", exc)
            raise
