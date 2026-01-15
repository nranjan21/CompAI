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
from app.utils.retry_utils import retry_on_failure


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
    
    @retry_on_failure(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(requests.exceptions.RequestException,))
    def fetch_html(self, url: str, timeout: int = 15) -> Optional[str]:
        """
        Fetch HTML content from a URL with retry logic.
        Tries ScrapingBee first if available, otherwise falls back to direct requests.
        """
        from app.core.config import config
        
        # Try ScrapingBee first (Main)
        if config.data_sources.scrapingbee_api_key:
            try:
                logger.debug(f"🐝 Fetching via ScrapingBee: {url}")
                params = {
                    'api_key': config.data_sources.scrapingbee_api_key,
                    'url': url,
                    'render_js': 'true',
                    'timeout': timeout * 1000  # ScrapingBee uses ms
                }
                response = requests.get('https://app.scrapingbee.com/api/v1/', params=params, timeout=timeout + 5)
                if response.status_code == 200:
                    return response.text
                else:
                    logger.warning(f"⚠️ ScrapingBee returned status {response.status_code} for {url}, falling back...")
            except Exception as e:
                logger.warning(f"⚠️ ScrapingBee failed for {url}: {e}, falling back...")

        # Fallback to direct requests
        self._rate_limit()
        logger.debug(f"🌐 Fetching directly: {url}")
        response = self.session.get(url, timeout=timeout)
        response.raise_for_status()
        return response.text
    
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
        Search Google and return results.
        Priority: ScrapingBee (Main) -> SerpAPI (Fallback) -> Direct Scraping
        """
        from app.core.config import config
        
        # 1. Try ScrapingBee (Main)
        if config.data_sources.scrapingbee_api_key:
            try:
                params = {
                    'api_key': config.data_sources.scrapingbee_api_key,
                    'search_engine': 'google',
                    'query': query,
                    'nb_results': num_results
                }
                logger.info(f"🐝 Searching Google via ScrapingBee: {query}")
                response = requests.get('https://app.scrapingbee.com/api/v1/google', params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    organic_results = data.get("organic_results", [])
                    for result in organic_results[:num_results]:
                        results.append({
                            'title': result.get('title', ''),
                            'url': result.get('url', ''),
                            'snippet': result.get('description', '')
                        })
                    if results:
                        return results
            except Exception as e:
                logger.warning(f"⚠️ ScrapingBee Search failed: {e}, trying fallback")

        # 2. Try SerpAPI (Fallback)
        if config.data_sources.serpapi_key:
            try:
                params = {
                    "q": query,
                    "num": num_results,
                    "api_key": config.data_sources.serpapi_key,
                    "engine": "google"
                }
                logger.info(f"🔍 Searching Google via SerpAPI: {query}")
                response = requests.get("https://serpapi.com/search", params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    organic_results = data.get("organic_results", [])
                    for result in organic_results[:num_results]:
                        results.append({
                            'title': result.get('title', ''),
                            'url': result.get('link', ''),
                            'snippet': result.get('snippet', '')
                        })
                    if results:
                        return results
            except Exception as e:
                logger.warning(f"⚠️ SerpAPI Search failed: {e}")
        
        # 3. Fallback to direct Google scraping
        search_url = f"https://www.google.com/search?q={requests.utils.quote(query)}&num={num_results}"
        # Use our fetch_html which might use ScrapingBee anyway
        html = self.fetch_html(search_url)
        if not html:
            return []
            
        soup = BeautifulSoup(html, 'lxml')
        results = []
        for result in soup.select('div.g'):
            title_element = result.select_one('h3')
            link_element = result.select_one('a')
            if title_element and link_element:
                title = title_element.get_text(strip=True)
                url = link_element.get('href', '')
                if url and not url.startswith('/search'):
                    results.append({'title': title, 'url': url})
        return results[:num_results]
    
    def search_google_news(self, query: str, months_back: int = 6, num_results: int = 20) -> List[Dict[str, Any]]:
        """
        Search Google News.
        Priority: ScrapingBee (Main) -> SerpAPI (Fallback)
        """
        from app.core.config import config
        
        # 1. Try ScrapingBee (Main)
        if config.data_sources.scrapingbee_api_key:
            try:
                params = {
                    'api_key': config.data_sources.scrapingbee_api_key,
                    'search_engine': 'google',
                    'query': f"{query} news", # ScrapingBee doesn't have a specific news engine like SerpAPI, so we append 'news'
                    'nb_results': num_results,
                    'tbm': 'nws' # Standard Google News parameter
                }
                logger.info(f"🐝 Searching Google News via ScrapingBee: {query}")
                response = requests.get('https://app.scrapingbee.com/api/v1/google', params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    organic_results = data.get("organic_results", [])
                    for result in organic_results[:num_results]:
                        results.append({
                            'title': result.get('title', ''),
                            'url': result.get('url', ''),
                            'source': result.get('source', ''),
                            'date': result.get('published_date', ''),
                            'snippet': result.get('description', '')
                        })
                    if results:
                        return results
            except Exception as e:
                logger.warning(f"⚠️ ScrapingBee News Search failed: {e}, trying fallback")

        # 2. Try SerpAPI (Fallback)
        if config.data_sources.serpapi_key:
            try:
                params = {
                    "engine": "google_news",
                    "q": query,
                    "num": num_results,
                    "api_key": config.data_sources.serpapi_key,
                    "tbs": "qdr:m6" # Default 6 months
                }
                if months_back <= 1: params["tbs"] = "qdr:m"
                elif months_back <= 12: params["tbs"] = "qdr:y"

                logger.info(f"🔍 Searching Google News via SerpAPI: {query}")
                response = requests.get("https://serpapi.com/search", params=params, timeout=15)
                
                if response.status_code == 200:
                    data = response.json()
                    news_results = data.get("news_results", [])
                    articles = []
                    for article in news_results[:num_results]:
                        articles.append({
                            'title': article.get('title', ''),
                            'url': article.get('link', ''),
                            'source': article.get('source', ''),
                            'date': article.get('date', ''),
                            'snippet': article.get('snippet', '')
                        })
                    return articles
            except Exception as e:
                logger.exception(f"⚠️ SerpAPI News failed: {e}")
        
        return self.search_google(f"{query} news", num_results)
    
    def extract_wikipedia_history(self, wiki_url: str) -> Optional[str]:
        """
        Extract the History section from a Wikipedia page.
        
        Args:
            wiki_url: URL of the Wikipedia page
            
        Returns:
            Extracted history text or None if not found
        """
        try:
            soup = self.fetch_and_parse(wiki_url)
            if not soup:
                return None
            
            # Find History heading
            # Wikipedia used h2 for major sections. We look for id "History"
            history_heading = None
            for h2 in soup.find_all('h2'):
                span = h2.find('span', id='History')
                if span:
                    history_heading = h2
                    break
            
            if not history_heading:
                # Try case insensitive or partial match
                for h2 in soup.find_all('h2'):
                    text = h2.get_text().lower()
                    if 'history' in text or 'background' in text:
                        history_heading = h2
                        break
            
            if not history_heading:
                return None
            
            content = []
            # Gather all subsequent siblings until the next h2
            curr = history_heading.next_sibling
            while curr and curr.name != 'h2':
                if curr.name in ['p', 'ul', 'ol']:
                    text = curr.get_text(strip=True)
                    if text:
                        content.append(text)
                curr = curr.next_sibling
            
            return "\n\n".join(content) if content else None
            
        except Exception as e:
            logger.warning(f"Error extracting Wikipedia history: {e}")
            return None

    @retry_on_failure(max_attempts=3, delay=1.0, backoff=2.0, exceptions=(requests.exceptions.RequestException, IOError))
    def download_file(self, url: str, save_path: str, timeout: int = 30) -> bool:
        """
        Download a file from URL with retry logic.
        
        Args:
            url: URL to download from
            save_path: Path to save the file
            timeout: Request timeout in seconds
            
        Returns:
            True if successful, False otherwise
        """
        self._rate_limit()
        
        logger.debug(f"📥 Downloading {url}")
        response = self.session.get(url, timeout=timeout, stream=True)
        response.raise_for_status()
        
        with open(save_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        
        logger.info(f"✅ Downloaded {url} to {save_path}")
        return True


# Global web scraper instance
web_scraper = None

def get_web_scraper() -> WebScraper:
    """Get or create global web scraper instance."""
    global web_scraper
    if web_scraper is None:
        web_scraper = WebScraper()
    return web_scraper
