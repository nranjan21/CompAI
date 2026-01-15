"""
Web Scraper utility for fetching and parsing HTML content.
Includes rate limiting and robust error handling.
"""

import time
import requests
from typing import Optional, List, Dict, Any
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from app.utils.logger import logger


class WebScraper:
    """Web scraping utility with rate limiting and error handling."""
    
    def __init__(self, rate_limit_delay: float = 1.0):
        """
        Initialize web scraper.
        
        Args:
            rate_limit_delay: Delay in seconds between requests
        """
        self.rate_limit_delay = rate_limit_delay
        self.last_request_time = 0
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.rate_limit_delay:
            sleep_time = self.rate_limit_delay - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def fetch_html(self, url: str, timeout: int = 10) -> Optional[str]:
        """
        Fetch HTML content from a URL.
        
        Args:
            url: URL to fetch
            timeout: Request timeout in seconds
            
        Returns:
            HTML content or None if failed
        """
        self._rate_limit()
        
        try:
            logger.debug(f"🌐 Fetching {url}")
            response = self.session.get(url, timeout=timeout)
            response.raise_for_status()
            return response.text
        except requests.exceptions.Timeout:
            logger.warning(f"⏱️ Timeout fetching {url}")
            return None
        except requests.exceptions.HTTPError as e:
            logger.warning(f"❌ HTTP error {e.response.status_code} fetching {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.warning(f"⚠️ Error fetching {url}: {e}")
            return None
    
    def parse_html(self, html: str) -> Optional[BeautifulSoup]:
        """
        Parse HTML content with BeautifulSoup.
        
        Args:
            html: HTML content
            
        Returns:
            BeautifulSoup object or None if failed
        """
        try:
            return BeautifulSoup(html, 'lxml')
        except Exception as e:
            logger.warning(f"⚠️ Error parsing HTML: {e}")
            return None
    
    def fetch_and_parse(self, url: str, timeout: int = 10) -> Optional[BeautifulSoup]:
        """
        Fetch and parse HTML in one step.
        
        Args:
            url: URL to fetch
            timeout: Request timeout in seconds
            
        Returns:
            BeautifulSoup object or None if failed
        """
        html = self.fetch_html(url, timeout)
        if html is None:
            return None
        return self.parse_html(html)
    
    def extract_text(self, soup: BeautifulSoup, selector: Optional[str] = None) -> str:
        """
        Extract clean text from HTML.
        
        Args:
            soup: BeautifulSoup object
            selector: CSS selector (None = entire document)
            
        Returns:
            Extracted text
        """
        if selector:
            element = soup.select_one(selector)
            if element:
                return element.get_text(separator=' ', strip=True)
            return ""
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        return soup.get_text(separator=' ', strip=True)
    
    def extract_links(self, soup: BeautifulSoup, base_url: str, filter_domain: bool = True) -> List[str]:
        """
        Extract all links from HTML.
        
        Args:
            soup: BeautifulSoup object
            base_url: Base URL for resolving relative links
            filter_domain: Only return links from same domain
            
        Returns:
            List of absolute URLs
        """
        links = []
        base_domain = urlparse(base_url).netloc
        
        for link in soup.find_all('a', href=True):
            absolute_url = urljoin(base_url, link['href'])
            
            if filter_domain:
                if urlparse(absolute_url).netloc == base_domain:
                    links.append(absolute_url)
            else:
                links.append(absolute_url)
        
        return list(set(links))  # Remove duplicates
    
    def extract_metadata(self, soup: BeautifulSoup) -> Dict[str, str]:
        """
        Extract metadata from HTML (title, description, etc.).
        
        Args:
            soup: BeautifulSoup object
            
        Returns:
            Dictionary of metadata
        """
        metadata = {}
        
        # Title
        title_tag = soup.find('title')
        if title_tag:
            metadata['title'] = title_tag.get_text(strip=True)
        
        # Meta tags
        for meta in soup.find_all('meta'):
            name = meta.get('name') or meta.get('property')
            content = meta.get('content')
            
            if name and content:
                metadata[name] = content
        
        return metadata
    
    def search_google(self, query: str, num_results: int = 10) -> List[Dict[str, str]]:
        """
        Search Google and return results using SerpAPI if available.
        
        Args:
            query: Search query
            num_results: Number of results to return
            
        Returns:
            List of search results with title and URL
        """
        # Try SerpAPI first if available
        from app.core.config import config
        
        if config.data_sources.serpapi_key:
            try:
                import requests
                
                params = {
                    "q": query,
                    "num": num_results,
                    "api_key": config.data_sources.serpapi_key,
                    "engine": "google"
                }
                
                response = requests.get("https://serpapi.com/search", params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    
                    # Check for error in response
                    if "error" in data:
                        logger.warning(f"SerpAPI error: {data['error']}")
                    else:
                        # Extract organic results
                        organic_results = data.get("organic_results", [])
                        for result in organic_results[:num_results]:
                            results.append({
                                'title': result.get('title', ''),
                                'url': result.get('link', '')
                            })
                        
                        if results:
                            logger.info(f"SerpAPI returned {len(results)} results")
                            return results
                        else:
                            logger.warning("SerpAPI returned no organic results")
                else:
                    logger.warning(f"SerpAPI returned status code {response.status_code}")
            except Exception as e:
                logger.warning(f"SerpAPI failed: {e}, falling back to direct scraping")
        
        # Fallback to direct Google scraping (may be blocked)
        search_url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num={num_results}"
        soup = self.fetch_and_parse(search_url)
        
        if soup is None:
            return []
        
        results = []
        
        # Parse search results
        for result in soup.select('div.g'):
            title_element = result.select_one('h3')
            link_element = result.select_one('a')
            
            if title_element and link_element:
                title = title_element.get_text(strip=True)
                url = link_element.get('href', '')
                
                if url and not url.startswith('/search'):
                    results.append({
                        'title': title,
                        'url': url
                    })
        
        return results[:num_results]
    
    def download_file(self, url: str, save_path: str, timeout: int = 30) -> bool:
        """
        Download a file from URL.
        
        Args:
            url: URL to download from
            save_path: Path to save the file
            timeout: Request timeout in seconds
            
        Returns:
            True if successful, False otherwise
        """
        self._rate_limit()
        
        try:
            logger.debug(f"📥 Downloading {url}")
            response = self.session.get(url, timeout=timeout, stream=True)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            logger.info(f"✅ Downloaded {url} to {save_path}")
            return True
        except Exception as e:
            logger.warning(f"⚠️ Error downloading {url}: {e}")
            return False


# Global web scraper instance
web_scraper = None

def get_web_scraper() -> WebScraper:
    """Get or create global web scraper instance."""
    global web_scraper
    if web_scraper is None:
        web_scraper = WebScraper()
    return web_scraper
