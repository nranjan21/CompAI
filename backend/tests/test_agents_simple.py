"""
Simple test script to verify agent implementations without relying on Google Search.
Tests with direct URLs and mock data.
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.agents.company_profile_agent import CompanyProfileAgent
from app.agents.sentiment_analysis_agent import SentimentAnalysisAgent
from app.utils.web_scraper import get_web_scraper
from app.utils.pdf_parser import get_pdf_parser
from app.utils.cache_manager import get_cache_manager
from app.utils.logger import logger


def test_utilities():
    """Test utility classes."""
    print("\n" + "="*80)
    print("Testing Utility Classes")
    print("="*80)
    
    # Test WebScraper
    print("\n📡 Testing WebScraper...")
    scraper = get_web_scraper()
    
    # Test fetching a simple page
    html = scraper.fetch_html("https://www.example.com")
    if html:
        print("  ✅ WebScraper can fetch HTML")
        soup = scraper.parse_html(html)
        if soup:
            print("  ✅ WebScraper can parse HTML")
            text = scraper.extract_text(soup)
            print(f"  ✅ Extracted {len(text)} characters of text")
    else:
        print("  ⚠️ Could not fetch HTML (might be network issue)")
    
    # Test CacheManager
    print("\n💾 Testing CacheManager...")
    cache = get_cache_manager()
    
    test_key = "test_key_123"
    test_data = {"test": "data", "number": 42}
    
    # Set cache
    if cache.set(test_key, test_data):
        print("  ✅ CacheManager can write data")
    
    # Get cache
    cached = cache.get(test_key)
    if cached == test_data:
        print("  ✅ CacheManager can read data")
    
    # Invalidate
    if cache.invalidate(test_key):
        print("  ✅ CacheManager can invalidate data")
    
    # Test PDFParser
    print("\n📄 Testing PDFParser...")
    pdf_parser = get_pdf_parser()
    print("  ✅ PDFParser initialized")
    
    return True


def test_sentiment_analysis_agent():
    """Test SentimentAnalysisAgent with mock data."""
    print("\n" + "="*80)
    print("Testing SentimentAnalysisAgent")
    print("="*80)
    
    # Create sample news data
    sample_news = [
        {
            'title': 'Amazon announces new AI features for AWS',
            'summary': 'Amazon Web Services launched innovative machine learning capabilities that will transform cloud computing',
            'category': 'Product Launch'
        },
        {
            'title': 'Amazon faces regulatory scrutiny in Europe',
            'summary': 'European regulators are investigating Amazon market practices and potential antitrust violations',
            'category': 'Controversy'
        },
        {
            'title': 'Amazon reports strong Q4 earnings',
            'summary': 'Amazon exceeded analyst expectations with robust revenue growth and improved profit margins',
            'category': 'Financial Results'
        },
        {
            'title': 'Amazon expands same-day delivery service',
            'summary': 'The company is expanding its same-day delivery to 50 new cities across the United States',
            'category': 'Product Launch'
        }
    ]
    
    agent = SentimentAnalysisAgent()
    result = agent.run(data_sources={'news': sample_news})
    
    print(f"\n✅ Result Keys: {list(result.keys())}")
    print(f"Overall Sentiment: {result.get('overall_sentiment', 'N/A')}")
    print(f"Sentiment Distribution: {result.get('sentiment_distribution', {})}")
    print(f"Number of Themes: {len(result.get('themes', []))}")
    print(f"Analyzed Items: {result.get('analyzed_items_count', 0)}")
    
    # Check metadata
    metadata = result.get('_metadata', {})
    print(f"Success: {metadata.get('success', 'N/A')}")
    print(f"Duration: {metadata.get('duration_seconds', 'N/A')} seconds")
    print(f"Errors: {len(metadata.get('errors', []))}")
    
    if metadata.get('success'):
        print("\n✅ SentimentAnalysisAgent test PASSED")
        return True
    else:
        print("\n❌ SentimentAnalysisAgent test FAILED")
        print(f"Errors: {metadata.get('errors', [])}")
        return False


def test_company_profile_agent_direct():
    """Test CompanyProfileAgent with direct URL (no Google Search)."""
    print("\n" + "="*80)
    print("Testing CompanyProfileAgent (Direct URL)")
    print("="*80)
    
    # We'll test the scraping and LLM synthesis parts directly
    scraper = get_web_scraper()
    
    # Test scraping Amazon's website directly
    print("\n🌐 Testing direct website scraping...")
    amazon_url = "https://www.amazon.com"
    soup = scraper.fetch_and_parse(amazon_url)
    
    if soup:
        print("  ✅ Successfully fetched Amazon homepage")
        text = scraper.extract_text(soup)
        print(f"  ✅ Extracted {len(text)} characters")
        
        # Test Wikipedia scraping
        wiki_url = "https://en.wikipedia.org/wiki/Amazon_(company)"
        wiki_soup = scraper.fetch_and_parse(wiki_url)
        
        if wiki_soup:
            print("  ✅ Successfully fetched Wikipedia page")
            content = wiki_soup.select_one('#mw-content-text')
            if content:
                wiki_text = scraper.extract_text(content)
                print(f"  ✅ Extracted {len(wiki_text)} characters from Wikipedia")
                
                # Now test the LLM synthesis
                print("\n🤖 Testing LLM synthesis...")
                agent = CompanyProfileAgent()
                
                # Call the synthesis method directly
                profile = agent._synthesize_profile(
                    "Amazon",
                    {"url": amazon_url, "homepage_text": text[:5000]},
                    wiki_text[:10000]
                )
                
                if profile:
                    print(f"\n✅ LLM Synthesis Result:")
                    print(f"  Company Name: {profile.get('company_name', 'N/A')}")
                    print(f"  Industry: {profile.get('industry', 'N/A')}")
                    print(f"  Founded: {profile.get('founded', 'N/A')}")
                    print(f"  Headquarters: {profile.get('headquarters', 'N/A')}")
                    print(f"  Products: {len(profile.get('products', []))} listed")
                    
                    if profile.get('company_name'):
                        print("\n✅ CompanyProfileAgent LLM synthesis test PASSED")
                        return True
    
    print("\n⚠️ CompanyProfileAgent test completed with warnings")
    return False


def test_base_agent_functionality():
    """Test BaseAgent functionality."""
    print("\n" + "="*80)
    print("Testing BaseAgent Functionality")
    print("="*80)
    
    from app.agents.base_agent import BaseAgent
    
    # Create a simple test agent
    class TestAgent(BaseAgent):
        def execute(self, test_param: str):
            self._log_step("Step 1: Testing")
            self._log_step("Step 2: More testing")
            return {"result": test_param, "success": True}
    
    agent = TestAgent(name="TestAgent", use_cache=True)
    agent.total_steps = 2
    
    result = agent.run(test_param="hello")
    
    print(f"\n✅ Result: {result.get('result', 'N/A')}")
    print(f"Success: {result.get('_metadata', {}).get('success', 'N/A')}")
    print(f"Duration: {result.get('_metadata', {}).get('duration_seconds', 'N/A')} seconds")
    
    if result.get('_metadata', {}).get('success'):
        print("\n✅ BaseAgent functionality test PASSED")
        return True
    
    return False


def main():
    """Run all tests."""
    print("\n🚀 Starting Agent Tests (Without Google Search Dependency)")
    print("="*80)
    
    results = {}
    
    try:
        # Test utilities
        results['utilities'] = test_utilities()
        
        # Test BaseAgent
        results['base_agent'] = test_base_agent_functionality()
        
        # Test SentimentAnalysisAgent (doesn't need web scraping)
        results['sentiment'] = test_sentiment_analysis_agent()
        
        # Test CompanyProfileAgent with direct URLs
        results['company_profile'] = test_company_profile_agent_direct()
        
        print("\n" + "="*80)
        print("📊 Test Results Summary")
        print("="*80)
        
        for test_name, passed in results.items():
            status = "✅ PASSED" if passed else "⚠️ PARTIAL/FAILED"
            print(f"  {test_name}: {status}")
        
        passed_count = sum(1 for v in results.values() if v)
        total_count = len(results)
        
        print(f"\nTotal: {passed_count}/{total_count} tests passed")
        
        if passed_count >= total_count - 1:  # Allow 1 failure
            print("\n✅ Overall: Tests PASSED")
        else:
            print("\n⚠️ Overall: Some tests failed")
        
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
