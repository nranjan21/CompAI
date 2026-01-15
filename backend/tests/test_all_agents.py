"""
Comprehensive test script for all agents.
Tests each agent independently and then tests parallel execution.
"""

import sys
import asyncio
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

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
    """Test CompanyProfileAgent independently."""
    print("\n" + "="*80)
    print("Testing CompanyProfileAgent")
    print("="*80)
    
    agent = CompanyProfileAgent()
    start_time = time.time()
    result = agent.run(company_name="Microsoft", ticker="MSFT")
    duration = time.time() - start_time
    
    print(f"\n✅ Duration: {duration:.2f} seconds")
    print(f"Company Name: {result.get('company_name', 'N/A')}")
    print(f"Industry: {result.get('industry', 'N/A')}")
    print(f"Founded: {result.get('founded', 'N/A')}")
    print(f"Headquarters: {result.get('headquarters', 'N/A')}")
    print(f"Products: {len(result.get('products', []))}")
    
    metadata = result.get('_metadata', {})
    success = metadata.get('success', False)
    errors = metadata.get('errors', [])
    
    print(f"Success: {success}")
    if errors:
        print(f"Errors: {errors}")
    
    return success


def test_financial_research_agent():
    """Test FinancialResearchAgent independently."""
    print("\n" + "="*80)
    print("Testing FinancialResearchAgent")
    print("="*80)
    
    agent = FinancialResearchAgent()
    start_time = time.time()
    result = agent.run(company_name="Microsoft", ticker="MSFT")
    duration = time.time() - start_time
    
    print(f"\n✅ Duration: {duration:.2f} seconds")
    print(f"Fiscal Year: {result.get('fiscal_year', 'N/A')}")
    print(f"Revenue: ${result.get('revenue', 'N/A')}M")
    print(f"Net Income: ${result.get('net_income', 'N/A')}M")
    print(f"Financial Health: {result.get('financial_health', 'N/A')}")
    
    metadata = result.get('_metadata', {})
    success = metadata.get('success', False)
    errors = metadata.get('errors', [])
    
    print(f"Success: {success}")
    if errors:
        print(f"Errors: {errors}")
    
    return success


def test_news_intelligence_agent():
    """Test NewsIntelligenceAgent independently."""
    print("\n" + "="*80)
    print("Testing NewsIntelligenceAgent")
    print("="*80)
    
    agent = NewsIntelligenceAgent()
    start_time = time.time()
    result = agent.run(company_name="Microsoft", months_back=6)
    duration = time.time() - start_time
    
    print(f"\n✅ Duration: {duration:.2f} seconds")
    print(f"Total Articles: {result.get('total_articles', 0)}")
    print(f"Categories: {result.get('categories', {})}")
    print(f"Sentiment Distribution: {result.get('sentiment_distribution', {})}")
    print(f"Major Events: {len(result.get('timeline', []))}")
    
    metadata = result.get('_metadata', {})
    success = metadata.get('success', False)
    errors = metadata.get('errors', [])
    
    print(f"Success: {success}")
    if errors:
        print(f"Errors: {errors}")
    
    return success


def test_sentiment_analysis_agent():
    """Test SentimentAnalysisAgent independently."""
    print("\n" + "="*80)
    print("Testing SentimentAnalysisAgent")
    print("="*80)
    
    # Create sample data
    sample_news = [
        {
            'title': 'Microsoft announces new AI breakthrough',
            'summary': 'Microsoft unveiled groundbreaking AI technology that will revolutionize computing',
            'category': 'Product Launch'
        },
        {
            'title': 'Microsoft faces privacy concerns',
            'summary': 'Privacy advocates raise concerns about Microsoft data collection practices',
            'category': 'Controversy'
        },
        {
            'title': 'Microsoft beats earnings expectations',
            'summary': 'Strong cloud growth drives Microsoft to record quarterly revenue',
            'category': 'Financial Results'
        }
    ]
    
    agent = SentimentAnalysisAgent()
    start_time = time.time()
    result = agent.run(data_sources={'news': sample_news})
    duration = time.time() - start_time
    
    print(f"\n✅ Duration: {duration:.2f} seconds")
    print(f"Overall Sentiment: {result.get('overall_sentiment', 'N/A')}")
    print(f"Sentiment Distribution: {result.get('sentiment_distribution', {})}")
    print(f"Themes: {len(result.get('themes', []))}")
    
    metadata = result.get('_metadata', {})
    success = metadata.get('success', False)
    errors = metadata.get('errors', [])
    
    print(f"Success: {success}")
    if errors:
        print(f"Errors: {errors}")
    
    return success


def test_competitive_intelligence_agent():
    """Test CompetitiveIntelligenceAgent independently."""
    print("\n" + "="*80)
    print("Testing CompetitiveIntelligenceAgent")
    print("="*80)
    
    agent = CompetitiveIntelligenceAgent()
    start_time = time.time()
    result = agent.run(company_name="Microsoft", industry="Technology")
    duration = time.time() - start_time
    
    print(f"\n✅ Duration: {duration:.2f} seconds")
    print(f"Competitors Found: {len(result.get('competitors', []))}")
    
    if result.get('competitors'):
        print("Competitors:")
        for comp in result.get('competitors', [])[:3]:
            print(f"  - {comp.get('name', 'N/A')}")
    
    swot = result.get('swot', {})
    print(f"SWOT Analysis:")
    print(f"  Strengths: {len(swot.get('strengths', []))}")
    print(f"  Weaknesses: {len(swot.get('weaknesses', []))}")
    print(f"  Opportunities: {len(swot.get('opportunities', []))}")
    print(f"  Threats: {len(swot.get('threats', []))}")
    
    metadata = result.get('_metadata', {})
    success = metadata.get('success', False)
    errors = metadata.get('errors', [])
    
    print(f"Success: {success}")
    if errors:
        print(f"Errors: {errors}")
    
    return success


def test_parallel_execution():
    """Test running multiple agents in parallel using ThreadPoolExecutor."""
    print("\n" + "="*80)
    print("Testing Parallel Execution")
    print("="*80)
    
    # Define agent tasks
    tasks = {
        'profile': lambda: CompanyProfileAgent().run(company_name="Apple", ticker="AAPL"),
        'news': lambda: NewsIntelligenceAgent().run(company_name="Apple", months_back=3),
        'competitive': lambda: CompetitiveIntelligenceAgent().run(company_name="Apple", industry="Technology")
    }
    
    print(f"\nRunning {len(tasks)} agents in parallel...")
    start_time = time.time()
    
    results = {}
    
    # Execute in parallel
    with ThreadPoolExecutor(max_workers=3) as executor:
        # Submit all tasks
        future_to_name = {executor.submit(task): name for name, task in tasks.items()}
        
        # Collect results as they complete
        for future in as_completed(future_to_name):
            agent_name = future_to_name[future]
            try:
                result = future.result()
                results[agent_name] = result
                print(f"  ✅ {agent_name} completed")
            except Exception as e:
                print(f"  ❌ {agent_name} failed: {e}")
                results[agent_name] = None
    
    duration = time.time() - start_time
    
    print(f"\n✅ Parallel execution completed in {duration:.2f} seconds")
    print(f"Results collected: {len(results)}/{len(tasks)}")
    
    # Check success
    success_count = sum(1 for r in results.values() if r and r.get('_metadata', {}).get('success'))
    print(f"Successful agents: {success_count}/{len(tasks)}")
    
    return success_count == len(tasks)


def test_orchestrator():
    """Test OrchestratorAgent (full workflow)."""
    print("\n" + "="*80)
    print("Testing OrchestratorAgent (Full Workflow)")
    print("="*80)
    
    orchestrator = OrchestratorAgent()
    start_time = time.time()
    result = orchestrator.run(company_name="Google", ticker="GOOGL")
    duration = time.time() - start_time
    
    print(f"\n✅ Duration: {duration:.2f} seconds")
    print(f"Status: {result.get('status', 'N/A')}")
    print(f"Errors: {len(result.get('errors', []))}")
    
    # Check each section
    sections = ['profile', 'financial', 'news', 'sentiment', 'competitive']
    for section in sections:
        has_section = section in result
        success = result.get(section, {}).get('_metadata', {}).get('success', False) if has_section else False
        status = '✅' if success else '⚠️' if has_section else '❌'
        print(f"  {status} {section}")
    
    return result.get('status') == 'completed'


def main():
    """Run all tests."""
    print("\n🚀 Comprehensive Agent Testing Suite")
    print("Testing all agents independently and parallel execution\n")
    
    results = {}
    
    try:
        # Test individual agents
        print("\n" + "="*80)
        print("PHASE 1: Individual Agent Tests")
        print("="*80)
        
        results['company_profile'] = test_company_profile_agent()
        results['financial_research'] = test_financial_research_agent()
        results['news_intelligence'] = test_news_intelligence_agent()
        results['sentiment_analysis'] = test_sentiment_analysis_agent()
        results['competitive_intelligence'] = test_competitive_intelligence_agent()
        
        # Test parallel execution
        print("\n" + "="*80)
        print("PHASE 2: Parallel Execution Test")
        print("="*80)
        
        results['parallel_execution'] = test_parallel_execution()
        
        # Test orchestrator
        print("\n" + "="*80)
        print("PHASE 3: Orchestrator Test")
        print("="*80)
        
        results['orchestrator'] = test_orchestrator()
        
        # Summary
        print("\n" + "="*80)
        print("📊 Test Results Summary")
        print("="*80)
        
        for test_name, passed in results.items():
            status = "✅ PASSED" if passed else "❌ FAILED"
            print(f"  {test_name}: {status}")
        
        passed_count = sum(1 for v in results.values() if v)
        total_count = len(results)
        
        print(f"\nTotal: {passed_count}/{total_count} tests passed")
        
        if passed_count == total_count:
            print("\n✅ All tests PASSED!")
        elif passed_count >= total_count - 1:
            print("\n⚠️ Most tests passed (acceptable)")
        else:
            print("\n❌ Multiple tests failed")
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
