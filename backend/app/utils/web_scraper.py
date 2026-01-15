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
    def fetch_html(self, url: str, timeout: int = 10) -> Optional[str]:
        """
        Fetch HTML content from a URL with retry logic.
        
        Args:
            url: URL to fetch
            timeout: Request timeout in seconds
            
        Returns:
            HTML content or None if failed
        """
        self._rate_limit()
        
        logger.debug(f"🌐 Fetching {url}")
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
                                'url': result.get('link', ''),
                                'snippet': result.get('snippet', '')
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
    
    def search_google_news(self, query: str, months_back: int = 6, num_results: int = 20) -> List[Dict[str, Any]]:
        """
        Search Google News specifically for recent articles with dates.
        
        Args:
            query: Search query (company name)
            months_back: How many months back to search
            num_results: Number of results to return
            
        Returns:
            List of news articles with title, URL, date, source, snippet
        """
        from app.core.config import config
        
        if not config.data_sources.serpapi_key:
            logger.warning("No SerpAPI key configured, falling back to search_google")
            return self.search_google(f"{query} news", num_results)
        
        try:
            import requests
            from datetime import datetime, timedelta
            
            # Calculate date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=months_back * 30)
            
            params = {
                "engine": "google_news",  # Use News engine
                "q": query,
                "gl": "us",  # Geographic location
                "hl": "en",  # Language
                "num": num_results,
                "api_key": config.data_sources.serpapi_key
            }
            
            # Add time filter (qdr parameter: m6 = 6 months, m12 = 12 months)
            if months_back <= 1:
                params["tbs"] = "qdr:m"  # Past month
            elif months_back <= 6:
                params["tbs"] = "qdr:m6"  # Past 6 months
            elif months_back <= 12:
                params["tbs"] = "qdr:y"  # Past year
            
            logger.info(f"Searching Google News for '{query}' (past {months_back} months)")
            response = requests.get("https://serpapi.com/search", params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if "error" in data:
                    logger.error(f"SerpAPI News error: {data['error']}")
                    return []
                
                news_results = data.get("news_results", [])
                
                if not news_results:
                    logger.warning(f"No news results found for '{query}'")
                    return []
                
                articles = []
                for article in news_results[:num_results]:
                    articles.append({
                        'title': article.get('title', ''),
                        'url': article.get('link', ''),
                        'source': article.get('source', ''),
                        'date': article.get('date', ''),  # e.g., "2 days ago"
                        'snippet': article.get('snippet', ''),
                        'thumbnail': article.get('thumbnail', '')
                    })
                
                logger.info(f"Found {len(articles)} news articles")
                return articles
            else:
                logger.error(f"SerpAPI News returned status {response.status_code}")
                return []
                
        except Exception as e:
            logger.exception(f"Failed to search Google News: {e}")
            return []
    
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
