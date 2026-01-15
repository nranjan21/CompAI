"""
Test the updated financial research agent with annualreports.com
"""

import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.agents.financial_research_agent import FinancialResearchAgent


def test_financial_agent():
    """Test FinancialResearchAgent with annualreports.com."""
    print("\n" + "="*80)
    print("Testing FinancialResearchAgent with annualreports.com")
    print("="*80)
    
    agent = FinancialResearchAgent()
    result = agent.run(company_name="Amazon", ticker="AMZN")
    
    print(f"\n✅ Result Keys: {list(result.keys())}")
    print(f"Fiscal Year: {result.get('fiscal_year', 'N/A')}")
    print(f"Revenue: ${result.get('revenue', 'N/A')}M")
    print(f"Net Income: ${result.get('net_income', 'N/A')}M")
    print(f"Financial Health: {result.get('financial_health', 'N/A')}")
    print(f"PDF Path: {result.get('pdf_path', 'N/A')}")
    
    metadata = result.get('_metadata', {})
    print(f"\nSuccess: {metadata.get('success', False)}")
    print(f"Errors: {metadata.get('errors', [])}")
    
    if metadata.get('success'):
        print("\n✅ FinancialResearchAgent test PASSED!")
        return True
    else:
        print("\n⚠️ FinancialResearchAgent test completed with warnings")
        return False


if __name__ == "__main__":
    test_financial_agent()
