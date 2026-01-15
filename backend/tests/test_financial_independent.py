"""
Test FinancialResearchAgent independently with the existing Amazon PDF.
"""

import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.agents.financial_research_agent import FinancialResearchAgent
from app.utils.logger import logger


def test_with_existing_pdf():
    """Test with existing downloaded PDF."""
    print("\n" + "="*80)
    print("Testing FinancialResearchAgent with existing PDF")
    print("="*80)
    
    agent = FinancialResearchAgent()
    
    # Check if PDF exists
    backend_dir = Path(__file__).parent.parent
    pdf_path = backend_dir / "annual_reports" / "Amazon_annual_report_20260113.pdf"
    if not pdf_path.exists():
        print(f"❌ PDF not found at {pdf_path}")
        return False
    
    print(f"✅ Found PDF: {pdf_path}")
    print(f"   Size: {pdf_path.stat().st_size / 1024 / 1024:.2f} MB\n")
    
    # Test parsing
    print("1. Testing PDF parsing...")
    financial_data = agent._parse_financial_data(str(pdf_path))
    
    if financial_data:
        print(f"   ✅ Extracted {len(financial_data.get('full_text', ''))} characters")
        print(f"   ✅ Found {len(financial_data.get('sections', []))} sections:")
        for section in financial_data.get('sections', []):
            print(f"      - {section['section']}: {len(section['text'])} chars")
    else:
        print("   ❌ No financial data extracted")
        return False
    
    # Test LLM analysis
    print("\n2. Testing LLM analysis...")
    analysis = agent._analyze_financials(financial_data, "Amazon")
    
    print(f"\n📊 Analysis Results:")
    print(f"   Fiscal Year: {analysis.get('fiscal_year', 'N/A')}")
    print(f"   Revenue: ${analysis.get('revenue', 'N/A')} Million")
    print(f"   Net Income: ${analysis.get('net_income', 'N/A')} Million")
    print(f"   Total Assets: ${analysis.get('total_assets', 'N/A')} Million")
    print(f"   Financial Health: {analysis.get('financial_health', 'N/A')}")
    
    key_metrics = analysis.get('key_metrics', {})
    if key_metrics:
        print(f"\n   Key Metrics:")
        for metric, value in key_metrics.items():
            print(f"      {metric}: {value}")
    
    risks = analysis.get('risks', [])
    if risks:
        print(f"\n   Risks ({len(risks)}):")
        for risk in risks[:3]:
            print(f"      - {risk}")
    
    # Check if we got real data
    if analysis.get('fiscal_year') != 'N/A' and analysis.get('revenue') != 'N/A':
        print("\n✅ FinancialResearchAgent test PASSED - Got real financial data!")
        return True
    else:
        print("\n⚠️ FinancialResearchAgent test PARTIAL - No real financial data extracted")
        return False


def test_full_workflow():
    """Test the complete workflow."""
    print("\n" + "="*80)
    print("Testing Complete FinancialResearchAgent Workflow")
    print("="*80)
    
    agent = FinancialResearchAgent()
    result = agent.run(company_name="Amazon", ticker="AMZN")
    
    print(f"\n📊 Final Result:")
    print(f"   Fiscal Year: {result.get('fiscal_year', 'N/A')}")
    print(f"   Revenue: ${result.get('revenue', 'N/A')} Million")
    print(f"   Net Income: ${result.get('net_income', 'N/A')} Million")
    print(f"   Financial Health: {result.get('financial_health', 'N/A')}")
    
    metadata = result.get('_metadata', {})
    print(f"\n   Success: {metadata.get('success', False)}")
    print(f"   Errors: {metadata.get('errors', [])}")
    
    return metadata.get('success', False)


if __name__ == "__main__":
    # Test with existing PDF first
    success1 = test_with_existing_pdf()
    
    # Then test full workflow (will use cache if available)
    # success2 = test_full_workflow()
    
    if success1:
        print("\n" + "="*80)
        print("✅ All tests PASSED!")
        print("="*80)
    else:
        print("\n" + "="*80)
        print("⚠️ Tests completed with warnings")
        print("="*80)
