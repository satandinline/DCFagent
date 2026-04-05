"""
Example usage of RAG (Retrieval-Augmented Generation) Service
Demonstrates how to use database retrieval + web search for enhanced DCF analysis
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from services.rag_service import rag_service


async def example_basic_rag():
    """Example 1: Basic RAG retrieval"""
    print("="*80)
    print("Example 1: Basic RAG Retrieval")
    print("="*80)
    
    # Retrieve context for a company
    result = await rag_service.retrieve_company_context(
        company_name="Apple Inc.",
        ticker="AAPL",
        use_web_search=True
    )
    
    print(f"\nCompany: {result['company_name']}")
    print(f"Ticker: {result['ticker']}")
    print(f"Sources: {', '.join(result['sources'])}")
    print(f"Web Search Used: {result['web_search_used']}")
    print(f"\nContext Summary:")
    print(result.get('context_summary', 'N/A'))
    print(f"\nContext Preview:")
    print(result.get('context', 'No context available')[:500])


async def example_database_only():
    """Example 2: Database-only retrieval (no web search)"""
    print("\n" + "="*80)
    print("Example 2: Database-Only Retrieval")
    print("="*80)
    
    result = await rag_service.retrieve_company_context(
        company_name="Test Company",
        ticker="TEST",
        use_web_search=False  # Disable web search
    )
    
    print(f"\nSources: {result['sources']}")
    print(f"Has Data: {'Yes' if result.get('financial_data') else 'No'}")
    print(f"Valuation History: {len(result.get('valuation_history', []))} records")


async def example_enhance_pdf_text():
    """Example 3: Enhance PDF text with RAG context"""
    print("\n" + "="*80)
    print("Example 3: Enhance PDF Text with RAG")
    print("="*80)
    
    # Simulate PDF text
    pdf_text = """
    Apple Inc. Financial Report 2023
    
    Revenue: $383 billion
    Net Income: $97 billion
    Operating Margin: 30%
    """
    
    enhanced_text = await rag_service.enhance_with_rag(
        pdf_text=pdf_text,
        company_name="Apple Inc.",
        ticker="AAPL",
        use_web_search=True
    )
    
    print(f"\nOriginal text length: {len(pdf_text)} chars")
    print(f"Enhanced text length: {len(enhanced_text)} chars")
    print(f"Enhancement: +{len(enhanced_text) - len(pdf_text)} chars")
    print(f"\nEnhanced text preview (last 500 chars):")
    print(enhanced_text[-500:])


async def example_rag_flow():
    """Example 4: Complete RAG flow explanation"""
    print("\n" + "="*80)
    print("Example 4: RAG Flow Explanation")
    print("="*80)
    
    print("""
RAG (Retrieval-Augmented Generation) Flow:

┌─────────────────────┐
│  User Input         │
│  (PDF/Text)         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Step 1: Database   │ ◄── Primary source
│  Retrieval          │     - Historical data
│                     │     - Past valuations
│  ✓ Fast            │     - Growth trends
│  ✓ Reliable        │
└──────────┬──────────┘
           │
           ├─ Has Data? ──YES──► Use DB data
           │
           NO
           │
           ▼
┌─────────────────────┐
│  Step 2: Web Search │ ◄── Fallback source
│  (if enabled)       │     - Current info
│                     │     - Market data
│  ✓ Comprehensive   │     - News & updates
│  ✓ Up-to-date      │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Step 3: Combine    │
│  Context            │
│                     │
│  DB + Web = Rich   │
│  Context            │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Step 4: LLM        │
│  Analysis           │
│                     │
│  Enhanced prompt    │
│  with context       │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│  Final Result       │
│  (More accurate)    │
└─────────────────────┘

Benefits:
✓ Leverages historical data
✓ Reduces hallucination
✓ Provides market context
✓ Improves accuracy
✓ Faster when data exists
    """)


async def main():
    """Run all examples"""
    print("\n" + "="*80)
    print("  RAG SERVICE - USAGE EXAMPLES")
    print("="*80)
    
    await example_basic_rag()
    await example_database_only()
    await example_enhance_pdf_text()
    await example_rag_flow()
    
    print("\n" + "="*80)
    print("All examples completed!")
    print("="*80)
    
    print("\n💡 Quick Start:")
    print("  from services.rag_service import rag_service")
    print("  ")
    print("  # Basic retrieval")
    print("  context = await rag_service.retrieve_company_context(")
    print("      company_name='Apple Inc.',")
    print("      ticker='AAPL',")
    print("      use_web_search=True")
    print("  )")
    print("  ")
    print("  # Enhance PDF text")
    print("  enhanced = await rag_service.enhance_with_rag(")
    print("      pdf_text=text,")
    print("      company_name='Apple Inc.',")
    print("      ticker='AAPL'")
    print("  )")


if __name__ == '__main__':
    asyncio.run(main())
