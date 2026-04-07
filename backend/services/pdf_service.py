import re
import json
import logging
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from typing import Optional, Dict, Any
import httpx

logger = logging.getLogger(__name__)

# Try to import PyMuPDF (much faster), fall back to pdfplumber
try:
    import fitz  # PyMuPDF
    HAS_PYMUPDF = True
except ImportError:
    HAS_PYMUPDF = False
    import pdfplumber

# Load API key from environment
def _get_dashscope_key() -> Optional[str]:
    """获取通义千问API密钥"""
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.startswith('DASHSCOPE_API_KEY='):
                    return line.split('=', 1)[1].strip()
    return os.getenv('DASHSCOPE_API_KEY')

# A股年报关键页面模式 - 基于财报结构智能定位
# 财务报告章节通常在年报的60-85%处
FINANCIAL_KEYWORDS = [
    # Chinese keywords
    "营业收入", "净利润", "资产总额", "负债", "所有者权益",
    "每股收益", "现金流", "利润表", "资产负债表",
    "主要会计数据", "主要财务指标", "财务报告",
    "营业成本", "毛利率", "ROE", "ROA",
    "营业收入增长率", "净利润增长率", "总股本", "股本",
    # English keywords
    "revenue", "net income", "total assets", "earnings per share",
    "balance sheet", "income statement", "cash flow",
    "operating income", "depreciation", "capital expenditure",
    "shares outstanding", "total revenue", "gross profit",
]

# Financial keywords set for fast lookup
FINANCIAL_KEYWORD_SET = set(kw.lower() for kw in FINANCIAL_KEYWORDS)

# 财务报表重点页码模式（中英文）
PAGE_NUMBER_PATTERNS = [
    r'第\s*\d+\s*页', r'Page\s*\d+',
    r'合并资产负债表', r'资产负债表', r'balance sheet',
    r'合并利润表', r'利润表', r'income statement',
    r'现金流量表', r'cash flow',
    r'主要财务指标', r'financial highlights',
    r'会计数据', r'financial data',
]

def _get_smart_page_ranges(total_pages: int) -> list:
    """
    基于A股年报结构智能推断关键页面范围
    
    A股年报通常结构:
    - 前面(5-10%): 封面、目录、重要提示、主要会计数据
    - 中间(10-60%): 业务讨论、分析
    - 后面(35-85%): 财务报表（审计报告、资产负债表、利润表、现金流量表）
    
    策略：覆盖更广范围确保包含关键财务数据，因为不同公司年报结构略有差异
    
    Returns:
        list of (start_page, end_page) tuples (0-indexed)
    """
    if total_pages < 50:
        return [(0, total_pages)]
    
    # 关键页面范围 - 覆盖更广确保不遗漏
    # 1. 主要会计数据/财务指标 - 前面章节 (3-10%)
    # 2. 合并财务报表 - 财务报表章节 (35-85%)
    #    A股年报的财务报表通常在35%-50%处开始
    
    section_start = int(total_pages * 0.35)  # 财务报表开始位置（提前）
    
    return [
        # 1. 主要会计数据/财务指标 - 前面章节
        (int(total_pages * 0.03), int(total_pages * 0.10)),
        # 2. 合并财务报表 - 资产负债表
        (section_start, section_start + 12),
        # 3. 合并利润表 - 紧随资产负债表
        (section_start + 6, section_start + 18),
        # 4. 现金流量表 - 紧随利润表
        (section_start + 12, section_start + 24),
    ]

def _page_relevance(text: str) -> int:
    """计算页面的财务相关性得分（优化版）"""
    if not text or len(text) < 50:
        return 0
    
    lower = text.lower()
    
    # 快速关键词匹配（使用集合交集）
    words = set(re.findall(r'\b\w{3,}\b', lower))
    keyword_matches = len(words & FINANCIAL_KEYWORD_SET)
    keyword_score = min(keyword_matches * 2, 30)  # 加权得分
    
    # 数字密度（财务页面通常有很多数字）
    digit_count = len(re.findall(r'\d+[,，]?\d*[.。]?\d*', text))
    digit_score = min(digit_count // 15, 15)  # 最多15分
    
    # 表格特征（使用更快的检测）
    table_score = 5 if ('\t' in text or '|' in text or '  ' in text) else 0
    
    # 页码模式匹配
    pattern_score = 0
    for pattern in PAGE_NUMBER_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            pattern_score += 3
    pattern_score = min(pattern_score, 15)
    
    return keyword_score + digit_score + table_score + pattern_score


def _extract_single_page_fitz(page) -> tuple:
    """使用PyMuPDF提取单个页面（快速）"""
    try:
        text = page.get_text("text") or ""
        relevance = _page_relevance(text)
        return (page.number, text, relevance)
    except Exception as e:
        logger.warning(f"Failed to extract page {page.number}: {e}")
        return (page.number, "", 0)


def _extract_single_page_pdfplumber(page) -> tuple:
    """使用pdfplumber提取单个页面"""
    try:
        text = page.extract_text() or ""
        relevance = _page_relevance(text)
        return (page.page_number - 1, text, relevance)
    except Exception as e:
        logger.warning(f"Failed to extract page {page.page_number}: {e}")
        return (page.page_number - 1, "", 0)


# 关键财务数据表页眉关键词 - 用于精确定位财务表所在页
FINANCIAL_TABLE_HEADERS = [
    # 中文财务报表表头
    r'\u5408\u5e76\u8d44\u4ea7\u8d34\u8868',  # 合并资产负债表
    r'\u8d44\u4ea7\u8d34\u8868',  # 资产负债表
    r'\u5408\u5e76\u5229\u6da6\u8868',  # 合并利润表
    r'\u5229\u6da6\u8868',  # 利润表
    r'\u73b0\u91d1\u6d41\u91cf\u8868',  # 现金流量表
    r'\u6240\u6709\u8005\u6743\u76ca\u53d8\u52a8\u8868',  # 所有者权益变动表
    r'\u4f1a\u8ba1\u62a5\u8868\u6ce8\u91ca',  # 会计报表注释
    # 英文财务报表表头
    'consolidated balance sheet', 'balance sheet',
    'consolidated income statement', 'income statement', 'statement of income',
    'cash flow statement', 'statement of cash flows',
    'statements of changes in equity',
    # 财务指标
    r'\u4e3b\u8981\u4f1a\u8ba1\u6570\u636e',  # 主要会计数据
    r'\u4e3b\u8981\u8d22\u52a1\u6307\u6807',  # 主要财务指标
    'financial highlights', 'key financial data',
]

# 编译正则表达式
FINANCIAL_TABLE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE) for pattern in FINANCIAL_TABLE_HEADERS
]

def _extract_page_fast(page) -> tuple:
    """统一接口提取页面"""
    if HAS_PYMUPDF:
        return _extract_single_page_fitz(page)
    return _extract_single_page_pdfplumber(page)


def extract_text_from_pdf(file_path: str, max_pages: int = 150, max_chars: int = 20000) -> str:
    """
    优化版：从PDF中提取关键财务页面的文本（极速版）
    
    优化点：
    1. 使用PyMuPDF（比pdfplumber快5-10倍）
    2. 智能页面选择 - 基于A股年报结构定位关键页面
    3. 提前终止低相关页面
    4. 字符数限制减少LLM处理压力
    
    Args:
        file_path: PDF文件路径
        max_pages: 最大处理页数
        max_chars: 最大提取字符数
    
    Returns:
        提取的文本内容
    """
    logger.info(f"开始提取PDF: {file_path} (使用{'PyMuPDF' if HAS_PYMUPDF else 'pdfplumber'})")
    
    if HAS_PYMUPDF:
        return _extract_with_fitz_smart(file_path, max_pages, max_chars)
    return _extract_with_pdfplumber_smart(file_path, max_pages, max_chars)


def _extract_with_fitz_smart(file_path: str, max_pages: int, max_chars: int) -> str:
    """
    使用PyMuPDF智能提取 - 只扫描前20页和最后2页
    
    A股年报结构特点：
    - 前20页：包含公司基本情况、主要会计数据、财务指标摘要
    - 最后2页：包含完整的财务报表（资产负债表、利润表、现金流量表）
    - 中间页：主要是文字描述、业务分析，对DCF直接有用的数据较少
    
    策略：只扫描有效页面（前20页+最后2页），提高效率
    """
    doc = fitz.open(file_path)
    total_pages = min(len(doc), max_pages)
    logger.info(f"PDF共 {len(doc)} 页，将扫描前{min(20, total_pages)}页和最后2页")
    
    # 计算需要扫描的页面
    front_pages = min(20, total_pages)  # 前20页
    back_pages = 2  # 最后2页
    
    # 收集需要处理的页面（避免重复）
    pages_to_scan = set()
    
    # 添加前20页
    for i in range(front_pages):
        pages_to_scan.add(i)
    
    # 添加最后2页（确保不与前20页重复）
    for i in range(max(0, total_pages - back_pages), total_pages):
        pages_to_scan.add(i)
    
    logger.info(f"共需扫描 {len(pages_to_scan)} 个页面: 前{front_pages}页 + 后{back_pages}页")
    
    # 快速提取并评分
    page_scores = []
    financial_table_pages = []
    
    for page_num in pages_to_scan:
        page = doc[page_num]
        text = page.get_text("text") or ""
        score = _page_relevance(text)
        
        # 检查是否是关键财务表所在页
        is_financial_table = False
        for pattern in FINANCIAL_TABLE_PATTERNS:
            if pattern.search(text):
                is_financial_table = True
                break
        
        if text.strip():
            page_scores.append((page_num, text, score, is_financial_table))
            if is_financial_table:
                financial_table_pages.append(page_num)
    
    doc.close()
    
    logger.info(f"扫描完成: 找到 {len(financial_table_pages)} 个财务表页: {[p+1 for p in financial_table_pages]}")
    
    # 计算动态阈值
    if page_scores:
        avg_score = sum(s[2] for s in page_scores) / len(page_scores)
        threshold = max(avg_score * 0.5, 10)
    else:
        threshold = 10
    
    logger.info(f"相关性阈值: {threshold:.1f}")
    
    # 选择有效页面
    selected = []
    total_chars = 0
    target_chars = int(max_chars * 1.1)
    
    # 财务表页优先添加
    for page_num, text, score, is_ft in sorted(page_scores, key=lambda x: (x[3], x[2]), reverse=True):
        if is_ft and total_chars < target_chars:
            remaining = target_chars - total_chars
            if len(text) > remaining:
                text = text[:remaining]
            selected.append((page_num, text, score, is_ft))
            total_chars += len(text)
    
    # 然后按得分添加其他有效页面
    for page_num, text, score, is_ft in sorted(page_scores, key=lambda x: x[2], reverse=True):
        if is_ft:
            continue
        if score < threshold:
            continue
        if total_chars >= target_chars:
            break
        remaining = target_chars - total_chars
        if len(text) > remaining:
            text = text[:remaining]
        selected.append((page_num, text, score, is_ft))
        total_chars += len(text)
    
    # 按页码排序并输出
    selected.sort(key=lambda x: x[0])
    result = "\n".join(text for _, text, _, _ in selected)
    
    # 确保不超过原始限制
    if len(result) > max_chars:
        result = result[:max_chars]
    
    logger.info(f"内容智能提取完成: {len(result)} 字符，来自 {len(selected)} 个有效页面")
    return result


def _extract_with_pdfplumber_smart(file_path: str, max_pages: int, max_chars: int) -> str:
    """
    使用pdfplumber智能提取 - 只扫描前20页和最后2页
    
    A股年报结构特点：
    - 前20页：包含公司基本情况、主要会计数据、财务指标摘要
    - 最后2页：包含完整的财务报表
    - 中间页：主要是文字描述、业务分析，对DCF直接有用的数据较少
    
    策略：只扫描有效页面（前20页+最后2页），提高效率
    """
    with pdfplumber.open(file_path) as pdf:
        total_pages = min(len(pdf.pages), max_pages)
        logger.info(f"PDF共 {len(pdf.pages)} 页，将扫描前{min(20, total_pages)}页和最后2页")
        
        # 计算需要扫描的页面
        front_pages = min(20, total_pages)
        back_pages = 2
        
        # 收集需要处理的页面
        pages_to_scan = set()
        
        # 添加前20页
        for i in range(front_pages):
            pages_to_scan.add(i)
        
        # 添加最后2页
        for i in range(max(0, total_pages - back_pages), total_pages):
            pages_to_scan.add(i)
        
        logger.info(f"共需扫描 {len(pages_to_scan)} 个页面: 前{front_pages}页 + 后{back_pages}页")
        
        # 并行提取
        pages_text = []
        financial_table_pages = []
        
        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(_extract_page_fast, pdf.pages[i])
                      for i in pages_to_scan]
            for future in as_completed(futures):
                page_num, text, score = future.result()
                
                # 检查是否是关键财务表所在页
                is_financial_table = False
                for pattern in FINANCIAL_TABLE_PATTERNS:
                    if pattern.search(text):
                        is_financial_table = True
                        break
                
                pages_text.append((page_num, text, score, is_financial_table))
                if is_financial_table:
                    financial_table_pages.append(page_num)
        
        logger.info(f"扫描完成: 找到 {len(financial_table_pages)} 个财务表页: {[p+1 for p in financial_table_pages]}")
        
        # 计算动态阈值
        if pages_text:
            avg_score = sum(s[2] for s in pages_text) / len(pages_text)
            threshold = max(avg_score * 0.5, 10)
        else:
            threshold = 10
        
        logger.info(f"相关性阈值: {threshold:.1f}")
        
        # 选择有效页面
        selected = []
        total_chars = 0
        target_chars = int(max_chars * 1.1)
        
        # 财务表页优先添加
        for page_num, text, score, is_ft in sorted(pages_text, key=lambda x: (x[3], x[2]), reverse=True):
            if is_ft and total_chars < target_chars:
                remaining = target_chars - total_chars
                if len(text) > remaining:
                    text = text[:remaining]
                selected.append((page_num, text, is_ft))
                total_chars += len(text)
        
        # 然后按得分添加其他有效页面
        for page_num, text, score, is_ft in sorted(pages_text, key=lambda x: x[2], reverse=True):
            if is_ft:
                continue
            if score < threshold:
                continue
            if total_chars >= target_chars:
                break
            remaining = target_chars - total_chars
            if len(text) > remaining:
                text = text[:remaining]
            selected.append((page_num, text, is_ft))
            total_chars += len(text)
        
        # 按页码排序
        selected.sort(key=lambda x: x[0])
        result = "\n".join(text for _, text, _ in selected)
        
        # 确保不超过原始限制
        if len(result) > max_chars:
            result = result[:max_chars]
        
        logger.info(f"内容智能提取完成: {len(result)} 字符，来自 {len(selected)} 个有效页面")
        return result


# LLM辅助分析提示词
LLM_ANALYSIS_PROMPT = """你是一个专业的财务分析师。请从以下年报文本中提取关键财务数据，
以JSON格式返回。只提取能明确找到的数据，找不到的值设为null。

需要提取的字段：
- company_name: 公司名称
- report_year: 报告年度（如2025）
- revenue: 营业收入（元）
- net_profit: 归属于股东的净利润（元）
- total_assets: 资产总计（元）
- total_liabilities: 负债总计（元）
- equity: 归属于股东的所有者权益（元）
- eps: 基本每股收益（元）
- roe: 净资产收益率（%），如果找不到除以股东权益计算
- cash_flow_operating: 经营活动产生的现金流量净额（元）
- cash_flow_investing: 投资活动产生的现金流量净额（元）
- cash_flow_financing: 筹资活动产生的现金流量净额（元）
- gross_margin: 毛利率（%），如果找不到设为null
- revenue_growth: 营业收入同比增长率（%），带正负号
- net_profit_growth: 净利润同比增长率（%），带正负号

返回格式示例：
{
  "company_name": "某某公司",
  "report_year": 2025,
  "revenue": 7548826104.54,
  "net_profit": 402189233.13,
  ...
}

年报文本内容：
{fiscal_text}
"""


async def call_qwen_api(text: str, api_key: str) -> Optional[Dict[str, Any]]:
    """
    调用通义千问API分析财务数据
    
    Args:
        text: 年报文本内容
        api_key: API密钥
    
    Returns:
        结构化的财务数据字典
    """
    url = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    prompt = LLM_ANALYSIS_PROMPT.replace('{fiscal_text}', text[:8000])  # 限制输入长度
    
    payload = {
        "model": "qwen-plus",
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.1  # 低温度确保稳定性
    }
    
    raw_content = None
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            result = response.json()
            
            if 'choices' in result and len(result['choices']) > 0:
                raw_content = result['choices'][0]['message']['content']
                # 清理并解析JSON
                content = raw_content.strip()
                # 如果包含markdown代码块，提取内部内容
                if content.startswith('```'):
                    lines = content.split('\n')
                    content = '\n'.join(lines[1:-1])  # 去掉```json和```
                elif content.startswith('```json'):
                    lines = content.split('\n')
                    content = '\n'.join(lines[1:-1])
                return json.loads(content)
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {e}, 原始内容: {raw_content[:200] if raw_content else 'N/A'}")
    except Exception as e:
        logger.error(f"LLM API调用失败: {e}")
        return None
    
    return None


def extract_with_llm_assist(file_path: str, use_llm: bool = True, max_chars: int = 20000) -> Dict[str, Any]:
    """
    结合LLM辅助分析提取PDF财务数据
    
    策略：
    1. 智能截取关键页面（快速）
    2. 调用LLM分析提取结构化数据（准确）
    3. 保留原始文本供备选
    
    Args:
        file_path: PDF文件路径
        use_llm: 是否使用LLM辅助分析
        max_chars: 最大提取字符数
    
    Returns:
        {
            'raw_text': 原始提取文本,
            'structured_data': LLM提取的结构化数据（如果use_llm=True）,
            'extraction_method': 'smart' 或 'smart+llm',
            'char_count': 提取字符数
        }
    """
    # 步骤1：智能截取关键页面
    logger.info(f"开始{'智能+LLM' if use_llm else '智能'}提取PDF: {file_path}")
    raw_text = extract_text_from_pdf(file_path, max_pages=226, max_chars=max_chars)
    
    result = {
        'raw_text': raw_text,
        'structured_data': None,
        'extraction_method': 'smart+llm' if use_llm else 'smart',
        'char_count': len(raw_text)
    }
    
    # 步骤2：LLM辅助分析
    if use_llm:
        api_key = _get_dashscope_key()
        if api_key:
            logger.info("调用通义千问API进行财务数据分析...")
            # 使用同步方式调用
            import asyncio
            try:
                structured_data = asyncio.run(call_qwen_api(raw_text, api_key))
                if structured_data:
                    result['structured_data'] = structured_data
                    logger.info(f"LLM分析成功，提取了 {len(structured_data)} 个字段")
                else:
                    logger.warning("LLM分析未返回有效数据")
            except Exception as e:
                logger.error(f"LLM分析失败: {e}")
        else:
            logger.warning("未找到API密钥，跳过LLM分析")
    
    return result
