"""
Simple test script to verify agent implementations.
Tests each agent individually with Amazon as the example company.
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.agents.company_profile_agent import CompanyProfileAgent
from app.agents.financial_research_agent import FinancialResearchAgent
from app.agents.news_intelligence_agent import NewsIntelligenceAgent
from app.agents.sentiment_analysis_agent import SentimentAnalysisAgent
from app.agents.competitive_intelligence_agent import CompetitiveIntelligenceAgent
from app.agents.orchestrator import OrchestratorAgent
from app.utils.logger import logger


def test_company_profile_agent():
    """Test CompanyProfileAgent."""
    print("\n" + "="*80)
    print("Testing CompanyProfileAgent")
    print("="*80)
    
    agent = CompanyProfileAgent()
    result = agent.run(company_name="Amazon", ticker="AMZN")
    
    print(f"\n✅ Result Keys: {list(result.keys())}")
    print(f"Company Name: {result.get('company_name', 'N/A')}")
    print(f"Industry: {result.get('industry', 'N/A')}")
    print(f"Success: {result.get('_metadata', {}).get('success', 'N/A')}")
    
    return result


def test_financial_research_agent():
    """Test FinancialResearchAgent."""
    print("\n" + "="*80)
    print("Testing FinancialResearchAgent")
    print("="*80)
    
    agent = FinancialResearchAgent()
    result = agent.run(company_name="Amazon", ticker="AMZN")
    
    print(f"\n✅ Result Keys: {list(result.keys())}")
    print(f"Fiscal Year: {result.get('fiscal_year', 'N/A')}")
    print(f"Revenue: {result.get('revenue', 'N/A')}")
    print(f"Success: {result.get('_metadata', {}).get('success', 'N/A')}")
    
    return result


def test_news_intelligence_agent():
    """Test NewsIntelligenceAgent."""
    print("\n" + "="*80)
    print("Testing NewsIntelligenceAgent")
    print("="*80)
    
    agent = NewsIntelligenceAgent()
    result = agent.run(company_name="Amazon", months_back=6)
    
    print(f"\n✅ Result Keys: {list(result.keys())}")
    print(f"Total Articles: {result.get('total_articles', 0)}")
    print(f"Categories: {result.get('categories', {})}")
    print(f"Success: {result.get('_metadata', {}).get('success', 'N/A')}")
    
    return result


def test_sentiment_analysis_agent():
    """Test SentimentAnalysisAgent."""
    print("\n" + "="*80)
    print("Testing SentimentAnalysisAgent")
    print("="*80)
    
    # Create sample data
    sample_news = [
        {
            'title': 'Amazon announces new AI features',
            'summary': 'Amazon Web Services launched new machine learning capabilities',
            'category': 'Product Launch'
        },
        {
            'title': 'Amazon faces regulatory scrutiny',
            'summary': 'Regulators investigating Amazon market practices',
            'category': 'Controversy'
        }
    ]
    
    agent = SentimentAnalysisAgent()
    result = agent.run(data_sources={'news': sample_news})
    
    print(f"\n✅ Result Keys: {list(result.keys())}")
    print(f"Overall Sentiment: {result.get('overall_sentiment', 'N/A')}")
    print(f"Sentiment Distribution: {result.get('sentiment_distribution', {})}")
    print(f"Success: {result.get('_metadata', {}).get('success', 'N/A')}")
    
    return result


def test_competitive_intelligence_agent():
    """Test CompetitiveIntelligenceAgent."""
    print("\n" + "="*80)
    print("Testing CompetitiveIntelligenceAgent")
    print("="*80)
    
    agent = CompetitiveIntelligenceAgent()
    result = agent.run(company_name="Amazon", industry="E-commerce and Cloud Computing")
    
    print(f"\n✅ Result Keys: {list(result.keys())}")
    print(f"Competitors: {len(result.get('competitors', []))}")
    print(f"SWOT Keys: {list(result.get('swot', {}).keys())}")
    print(f"Success: {result.get('_metadata', {}).get('success', 'N/A')}")
    
    return result


def test_orchestrator():
    """Test OrchestratorAgent (full workflow)."""
    print("\n" + "="*80)
    print("Testing OrchestratorAgent (Full Workflow)")
    print("="*80)
    
    orchestrator = OrchestratorAgent()
    result = orchestrator.run(company_name="Amazon", ticker="AMZN")
    
    print(f"\n✅ Result Keys: {list(result.keys())}")
    print(f"Status: {result.get('status', 'N/A')}")
    print(f"Duration: {result.get('duration_seconds', 'N/A')} seconds")
    print(f"Errors: {len(result.get('errors', []))} errors")
    
    # Check each section
    for section in ['profile', 'financial', 'news', 'sentiment', 'competitive']:
        has_section = section in result
        print(f"  - {section}: {'✅' if has_section else '❌'}")
    
    return result


def main():
    """Run all tests."""
    print("\n🚀 Starting Agent Tests")
    print("This will test each agent with Amazon as the example company\n")
    
    try:
        # Test individual agents
        test_company_profile_agent()
        # test_financial_research_agent()  # Uncomment if you want to test SEC downloads
        # test_news_intelligence_agent()   # Uncomment to test news gathering
        # test_sentiment_analysis_agent()  # Uncomment to test sentiment
        # test_competitive_intelligence_agent()  # Uncomment to test competitive
        
        # Test full orchestrator
        # test_orchestrator()  # Uncomment to test full workflow
        
        print("\n" + "="*80)
        print("✅ All tests completed!")
        print("="*80)
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
