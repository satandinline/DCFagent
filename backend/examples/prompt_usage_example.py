"""
Example usage of the prompts module
Demonstrates how to use different prompt templates for various tasks
"""
import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))

from prompts import get_prompt, list_prompts, get_prompt_info, PROMPT_TEMPLATES


def example_list_prompts():
    """Example 1: List all available prompts"""
    print("="*70)
    print("Example 1: List Available Prompts")
    print("="*70)
    
    prompts = list_prompts()
    print(f"\nTotal {len(prompts)} prompt templates available:\n")
    for i, name in enumerate(prompts, 1):
        print(f"{i}. {name}")


def example_get_prompt_info():
    """Example 2: Get detailed information about prompts"""
    print("\n" + "="*70)
    print("Example 2: Prompt Information")
    print("="*70)
    
    info = get_prompt_info()
    
    print("\nPrompt Details:")
    for name, details in info['templates'].items():
        print(f"\n  {name}:")
        print(f"    Length: {details['length']} chars")
        print(f"    Estimated Tokens: ~{details['estimated_tokens']}")
        print(f"    Preview: {details['preview']}")
    
    print("\nRecommended Prompts:")
    for use_case, template in info['recommended'].items():
        print(f"  • {use_case}: '{template}'")


def example_use_specific_prompt():
    """Example 3: Get and use a specific prompt"""
    print("\n" + "="*70)
    print("Example 3: Using Specific Prompts")
    print("="*70)
    
    # Get the optimized extraction prompt
    extraction_prompt = get_prompt('financial_extraction')
    print(f"\n✓ Got financial extraction prompt ({len(extraction_prompt)} chars)")
    
    # Get simplified prompt for quick screening
    simple_prompt = get_prompt('extraction_simple')
    print(f"✓ Got simplified prompt ({len(simple_prompt)} chars)")
    
    # Get detailed analysis prompt
    detailed_prompt = get_prompt('extraction_detailed')
    print(f"✓ Got detailed analysis prompt ({len(detailed_prompt)} chars)")
    
    # Get narrative generation prompt
    narrative_prompt = get_prompt('narrative_generation')
    print(f"✓ Got narrative generation prompt ({len(narrative_prompt)} chars)")


def example_direct_access():
    """Example 4: Direct access to prompt dictionary"""
    print("\n" + "="*70)
    print("Example 4: Direct Dictionary Access")
    print("="*70)
    
    # Access prompt directly from dictionary
    prompt = PROMPT_TEMPLATES['financial_extraction']
    print(f"\nDirect access: {len(prompt)} chars")
    
    # Check if a prompt exists
    if 'custom_prompt' not in PROMPT_TEMPLATES:
        print("✗ 'custom_prompt' does not exist")
    
    # Add custom prompt (runtime only)
    PROMPT_TEMPLATES['my_custom_prompt'] = "Custom prompt text here..."
    print("✓ Added custom prompt at runtime")


async def example_with_llm_service():
    """Example 5: Use prompts with LLM Service"""
    print("\n" + "="*70)
    print("Example 5: Integration with LLM Service")
    print("="*70)
    
    try:
        from services.llm_service import LLMService
        
        llm = LLMService()
        
        # Example: Extract with default optimized prompt
        print("\nUsing default optimized prompt...")
        # result = await llm.extract_financial_data_optimized(text, 'financial_extraction')
        
        # Example: Extract with simplified prompt (faster, cheaper)
        print("Using simplified prompt for quick screening...")
        # result = await llm.extract_financial_data_optimized(text, 'extraction_simple')
        
        # Example: Extract with detailed prompt (comprehensive analysis)
        print("Using detailed prompt for comprehensive analysis...")
        # result = await llm.extract_financial_data_optimized(text, 'extraction_detailed')
        
        print("✓ LLM service integration examples shown")
        print("  (Actual API calls commented out to avoid costs)")
        
    except ImportError as e:
        print(f"⚠ Could not import LLM service: {e}")


def example_error_handling():
    """Example 6: Error handling"""
    print("\n" + "="*70)
    print("Example 6: Error Handling")
    print("="*70)
    
    # Try to get non-existent prompt
    try:
        prompt = get_prompt('non_existent_prompt')
    except KeyError as e:
        print(f"✓ Caught expected error: {e}")
    
    # Fallback strategy
    try:
        prompt = get_prompt('invalid_name')
    except KeyError:
        print("✓ Using fallback to default prompt")
        prompt = get_prompt('financial_extraction')
        print(f"  Fallback successful: {len(prompt)} chars")


def main():
    """Run all examples"""
    print("\n" + "="*70)
    print("PROMPTS MODULE - USAGE EXAMPLES")
    print("="*70)
    
    # Run synchronous examples
    example_list_prompts()
    example_get_prompt_info()
    example_use_specific_prompt()
    example_direct_access()
    example_error_handling()
    
    # Run async example
    asyncio.run(example_with_llm_service())
    
    print("\n" + "="*70)
    print("All examples completed!")
    print("="*70)
    
    print("\n💡 Quick Start:")
    print("  from prompts import get_prompt")
    print("  prompt = get_prompt('financial_extraction')")
    print("\n📚 Available Templates:")
    for name in list_prompts():
        print(f"  - {name}")


if __name__ == '__main__':
    main()
