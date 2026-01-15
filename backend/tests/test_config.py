"""
Quick test to verify SerpAPI integration and SEC EDGAR access.
"""

import sys
from pathlib import Path

backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from app.core.config import config
from app.utils.web_scraper import get_web_scraper
from app.utils.logger import logger


def test_serpapi():
    """Test SerpAPI integration."""
    print("\n" + "="*80)
    print("Testing SerpAPI Integration")
    print("="*80)
    
    # Check if API key is configured
    if config.data_sources.serpapi_key:
        print(f"✅ SerpAPI key found: {config.data_sources.serpapi_key[:10]}...")
    else:
        print("❌ SerpAPI key NOT found in config")
        return False
    
    # Test search
    scraper = get_web_scraper()
    results = scraper.search_google("Microsoft official website", num_results=5)
    
    print(f"\nSearch Results: {len(results)}")
    for i, result in enumerate(results[:3], 1):
        print(f"{i}. {result['title']}")
        print(f"   {result['url']}")
    
    if results:
        print("\n✅ SerpAPI is working!")
        return True
    else:
        print("\n❌ SerpAPI returned no results")
        return False


def test_sec_edgar():
    """Test SEC EDGAR access with proper headers."""
    print("\n" + "="*80)
    print("Testing SEC EDGAR Access")
    print("="*80)
    
    import requests
    
    url = "https://www.sec.gov/cgi-bin/browse-edgar?action=getcompany&CIK=MSFT&type=10-K&dateb=&owner=exclude&count=10"
    
    headers = {
        'User-Agent': 'Company Research Agent research@example.com'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ SEC EDGAR access successful!")
            
            # Check if we got filings
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            filings_table = soup.find('table', {'class': 'tableFile2'})
            
            if filings_table:
                rows = filings_table.find_all('tr')[1:]  # Skip header
                print(f"Found {len(rows)} filings")
                return True
            else:
                print("⚠️ No filings table found")
                return False
        else:
            print(f"❌ SEC EDGAR returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def main():
    """Run quick tests."""
    print("\n🔍 Quick Configuration Tests\n")
    
    results = {}
    results['serpapi'] = test_serpapi()
    results['sec_edgar'] = test_sec_edgar()
    
    print("\n" + "="*80)
    print("Summary")
    print("="*80)
    
    for test_name, passed in results.items():
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    if all(results.values()):
        print("\n✅ All configuration tests passed!")
    else:
        print("\n⚠️ Some tests failed - check configuration")


if __name__ == "__main__":
    main()
