"""
Prompt Templates for DCF Valuation System
Centralized prompt management for different LLM tasks
Based on 15-iteration optimization (Best: Iteration 2)
"""

# ============================================================================
# Financial Data Extraction Prompt (Optimized - Iteration 2)
# Quality: 10/10, Tokens: 2640, Efficiency: 0.003788
# ============================================================================

FINANCIAL_EXTRACTION_PROMPT = """You are a professional financial analyst specializing in DCF valuation.

TASK: Perform a comprehensive DCF (Discounted Cash Flow) valuation analysis.

DATA STRUCTURE:
Extract and organize the following financial data:
1. Revenue and growth rates
2. Operating margins
3. Working capital requirements
4. Capital expenditures
5. Tax rates
6. Discount rate (WACC)

FEW-SHOT EXAMPLES:
Example Input:
Company: TechCorp
Revenue (2023): $100M
Operating Margin: 20%
Growth Rate: 15%

Example Output Structure:
- Project revenue for 5 years
- Calculate operating income
- Estimate free cash flow
- Apply discount rate
- Calculate terminal value

REASONING PROCESS:
Think step by step:
1. What are the key financial metrics?
2. What growth rate is reasonable?
3. How will margins evolve?
4. What discount rate reflects the risk?
5. Calculate present value of future cash flows.

OUTPUT FORMAT:
Provide output in structured JSON format:
{
  "company_name": "...",
  "valuation_summary": {
    "enterprise_value": ...,
    "equity_value": ...,
    "per_share_value": ...,
    "implied_multiple": "..."
  },
  "key_assumptions": {
    "revenue_growth_rate": ...,
    "terminal_growth_rate": ...,
    "wacc": ...,
    "target_margin": ...
  },
  "projections": [
    {"year": 1, "revenue": ..., "fcf": ...},
    ...
  ],
  "sensitivity_analysis": {
    "wacc_range": [...],
    "growth_range": [...],
    "value_matrix": [...]
  },
  "investment_thesis": "...",
  "key_risks": ["...", "..."],
  "confidence_level": "High/Medium/Low"
}

CONSTRAINTS:
Ensure all calculations are mathematically correct.
Terminal growth rate must not exceed GDP growth (typically 2-3%).
WACC should be between 6% and 15% for most companies.
Terminal value should represent 60-80% of enterprise value.
Revenue growth should decelerate over time towards terminal rate.
Margins should converge to industry averages.
Always provide rationale for key assumptions.

Please analyze the provided financial data and produce a comprehensive DCF valuation."""


# ============================================================================
# Investment Narrative Generation Prompt
# ============================================================================

NARRATIVE_GENERATION_PROMPT = """You are a senior equity research analyst. Write a professional DCF valuation narrative analysis based on the financial data and DCF results provided.

Your analysis should cover:
1. Company overview and key financial metrics
2. Revenue and profitability trends
3. WACC assumptions and justification
4. Free cash flow projections summary
5. Terminal value methodology
6. Valuation conclusion with fair value per share
7. Key risks and sensitivities

Write in the same language as the input data. Be concise yet thorough. Use professional financial language.

Structure your response with clear sections and bullet points for readability."""


# ============================================================================
# Simplified Extraction Prompt (For Quick Analysis)
# Lower token cost, good for initial screening
# ============================================================================

SIMPLIFIED_EXTRACTION_PROMPT = """You are a financial analyst. Extract key financial data from the provided text.

Return JSON with these fields:
{
  "company_name": "string",
  "ticker": "string or null",
  "currency": "CNY",
  "fiscal_year": number,
  "revenue": number,
  "revenue_growth": number,
  "operating_income": number,
  "operating_margin": number,
  "net_income": number,
  "total_debt": number,
  "cash_and_equivalents": number,
  "shares_outstanding": number,
  "tax_rate": number,
  "current_stock_price": number or null
}

Rules:
- All amounts in Yuan (元)
- Ratios as decimals (0.15 not 15%)
- Return only valid JSON
- Estimate missing values reasonably"""


# ============================================================================
# Detailed Analysis Prompt (For Comprehensive Reports)
# More verbose, includes scenario analysis
# ============================================================================

DETAILED_ANALYSIS_PROMPT = """You are a professional financial analyst specializing in DCF valuation.

Comprehensive DCF Valuation Framework:

STEP 1: BUSINESS UNDERSTANDING
- Industry dynamics and competitive position
- Revenue drivers and sustainability
- Margin structure and operating leverage

STEP 2: HISTORICAL PERFORMANCE DECONSTRUCTION
- Revenue quality and growth decomposition
- Margin trajectory and mean reversion signals
- Working capital cycle analysis
- Capital allocation efficiency

STEP 3: FORWARD-LOOKING ASSUMPTIONS
Base Case: Conservative revenue growth, stable margins, normalized WC
Bull Case (+20%): Above-industry growth, margin expansion
Bear Case (-20%): Market pressure, margin compression

STEP 4: VALUATION METHODOLOGY
- Unlevered Free Cash Flow projection
- WACC derivation with market-based inputs
- Terminal value via perpetuity growth method
- Sensitivity analysis on key drivers

Few-Shot Learning Examples:

EXAMPLE 1 - Mature Company:
Input: Revenue=$500M, Growth=5%, OpMargin=15%, WACC=9%
Analysis: Low growth suggests maturity, stable margins
Output: EV=$3.2B, implying 6.4x revenue multiple

EXAMPLE 2 - High Growth Company:
Input: Revenue=$50M, Growth=40%, OpMargin=-5%, WACC=12%
Analysis: High growth justifies premium, temporary negative margins
Output: EV=$800M, implying 16x revenue multiple

OUTPUT FORMAT:
Provide output in structured JSON format with valuation_summary, key_assumptions, projections, sensitivity_analysis, investment_thesis, key_risks, and confidence_level.

CONSTRAINTS:
- Terminal growth rate ≤ GDP growth (2-3%)
- WACC between 6-15%
- Terminal value 60-80% of enterprise value
- Revenue growth decelerates to terminal rate
- Margins converge to industry averages
- Always justify key assumptions

Analyze the financial data systematically and provide your DCF valuation."""


# ============================================================================
# Prompt Variants Dictionary
# Easy access to different prompt types
# ============================================================================

PROMPT_TEMPLATES = {
    # Main extraction prompts
    'financial_extraction': FINANCIAL_EXTRACTION_PROMPT,
    'extraction_optimized': FINANCIAL_EXTRACTION_PROMPT,  # Alias
    
    # Alternative extraction prompts
    'extraction_simple': SIMPLIFIED_EXTRACTION_PROMPT,
    'extraction_detailed': DETAILED_ANALYSIS_PROMPT,
    
    # Narrative generation
    'narrative_generation': NARRATIVE_GENERATION_PROMPT,
    
    # Legacy names for backward compatibility
    'balanced': FINANCIAL_EXTRACTION_PROMPT,
    'concise': SIMPLIFIED_EXTRACTION_PROMPT,
    'detailed': DETAILED_ANALYSIS_PROMPT,
}


# ============================================================================
# Helper Functions
# ============================================================================

def get_prompt(template_name: str = 'financial_extraction') -> str:
    """
    Get prompt template by name
    
    Args:
        template_name: Name of the prompt template
        
    Returns:
        Prompt string
        
    Raises:
        KeyError: If template_name not found
    """
    if template_name not in PROMPT_TEMPLATES:
        available = ', '.join(PROMPT_TEMPLATES.keys())
        raise KeyError(
            f"Prompt template '{template_name}' not found. "
            f"Available templates: {available}"
        )
    return PROMPT_TEMPLATES[template_name]


def list_prompts() -> list[str]:
    """List all available prompt template names"""
    return list(PROMPT_TEMPLATES.keys())


def get_prompt_info() -> dict:
    """Get information about all available prompts"""
    return {
        'templates': {
            name: {
                'length': len(prompt),
                'estimated_tokens': len(prompt) // 4,  # Rough estimate
                'preview': prompt[:100] + '...'
            }
            for name, prompt in PROMPT_TEMPLATES.items()
        },
        'recommended': {
            'extraction': 'financial_extraction',
            'narrative': 'narrative_generation',
            'quick_screening': 'extraction_simple',
            'comprehensive': 'extraction_detailed'
        }
    }


# ============================================================================
# Usage Examples
# ============================================================================

if __name__ == '__main__':
    # Example 1: Get default extraction prompt
    prompt = get_prompt('financial_extraction')
    print(f"Default prompt length: {len(prompt)} chars")
    
    # Example 2: List all available prompts
    print("\nAvailable prompts:")
    for name in list_prompts():
        print(f"  - {name}")
    
    # Example 3: Get prompt info
    info = get_prompt_info()
    print(f"\nRecommended prompts:")
    for use_case, template in info['recommended'].items():
        print(f"  {use_case}: {template}")
