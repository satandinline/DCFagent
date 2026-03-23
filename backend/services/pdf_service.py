import re
import logging

import pdfplumber

logger = logging.getLogger(__name__)

FINANCIAL_KEYWORDS = [
    "营业收入", "净利润", "资产总额", "负债", "所有者权益",
    "每股收益", "现金流", "利润表", "资产负债表",
    "revenue", "net income", "total assets", "earnings per share",
    "balance sheet", "income statement", "cash flow",
    "主要会计数据", "主要财务指标", "财务报告",
    "operating income", "depreciation", "capital expenditure",
    "股本", "shares outstanding", "总股本",
]


def _page_relevance(text: str) -> int:
    if not text:
        return 0
    lower = text.lower()
    return sum(1 for kw in FINANCIAL_KEYWORDS if kw.lower() in lower)


def extract_text_from_pdf(file_path: str) -> str:
    """Extract text from key financial pages of a PDF report."""
    pages_text: list[tuple[int, str, int]] = []

    with pdfplumber.open(file_path) as pdf:
        total_pages = len(pdf.pages)
        logger.info("PDF has %d pages", total_pages)

        for i, page in enumerate(pdf.pages):
            try:
                text = page.extract_text() or ""
            except Exception:
                text = ""
            relevance = _page_relevance(text)
            pages_text.append((i, text, relevance))

    pages_text.sort(key=lambda x: x[2], reverse=True)

    selected: list[tuple[int, str]] = []
    total_chars = 0
    max_chars = 30000

    for page_idx, text, relevance in pages_text:
        if not text.strip():
            continue
        if total_chars + len(text) > max_chars:
            remaining = max_chars - total_chars
            if remaining > 200:
                selected.append((page_idx, text[:remaining]))
                total_chars += remaining
            break
        selected.append((page_idx, text))
        total_chars += len(text)

    selected.sort(key=lambda x: x[0])

    result = "\n".join(text for _, text in selected)
    logger.info(
        "Extracted %d chars from %d relevant pages (out of %d total)",
        len(result), len(selected), len(pages_text),
    )
    return result
