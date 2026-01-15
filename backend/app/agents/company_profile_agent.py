"""
Company Profile Agent - Gathers basic company information from multiple sources.

Workflow:
1. Search for company website
2. Scrape company website for about/mission
3. Scrape Wikipedia for overview
4. Use LLM to synthesize structured profile
"""

from typing import Dict, Any, Optional, List
from app.agents.base_agent import BaseAgent
from app.utils.web_scraper import get_web_scraper
from app.utils.logger import logger


class CompanyProfileAgent(BaseAgent):
    """Agent for gathering comprehensive company profile information."""
    
    def __init__(self):
        """Initialize the company profile agent."""
        super().__init__(name="CompanyProfileAgent", use_cache=True)
        self.web_scraper = get_web_scraper()
        self.total_steps = 5
    
    def _find_company_website(self, company_name: str) -> Optional[str]:
        """Find the official company website."""
        self._log_step(f"Searching for {company_name} website")
        
        search_results = self.web_scraper.search_google(
            f"{company_name} official website",
            num_results=5
        )
        
        if not search_results:
            self._add_error("Could not find company website")
            return None
        
        # Return the first result (usually the official website)
        website = search_results[0]['url']
        logger.info(f"Found website: {website}")
        return website
    
    def _scrape_company_website(self, url: str) -> Dict[str, str]:
        """Scrape basic information from company website."""
        self._log_step("Scraping company website")
        
        soup = self.web_scraper.fetch_and_parse(url)
        if soup is None:
            return {}
        
        data = {
            "url": url,
            "homepage_text": self.web_scraper.extract_text(soup)[:5000],  # Limit to first 5000 chars
        }
        
        # Try to find About page
        links = self.web_scraper.extract_links(soup, url, filter_domain=True)
        about_links = [link for link in links if 'about' in link.lower()]
        
        if about_links:
            about_soup = self.web_scraper.fetch_and_parse(about_links[0])
            if about_soup:
                data["about_text"] = self.web_scraper.extract_text(about_soup)[:5000]
        
        return data
    
    def _scrape_wikipedia(self, company_name: str) -> Optional[str]:
        """Scrape Wikipedia for company information."""
        self._log_step("Scraping Wikipedia")
        
        # Search for Wikipedia page
        search_results = self.web_scraper.search_google(
            f"{company_name} Wikipedia",
            num_results=3
        )
        
        wiki_url = None
        for result in search_results:
            if 'wikipedia.org' in result['url']:
                wiki_url = result['url']
                break
        
        if not wiki_url:
            logger.info("No Wikipedia page found")
            return None
        
        soup = self.web_scraper.fetch_and_parse(wiki_url)
        if soup is None:
            return None
        
        # Extract main content
        content = soup.select_one('#mw-content-text')
        if content:
            return self.web_scraper.extract_text(content)[:10000]
        
        return None
    
    def _synthesize_profile(self, company_name: str, website_data: Dict[str, str], wiki_text: Optional[str]) -> Dict[str, Any]:
        """Use LLM to synthesize structured company profile."""
        self._log_step("Synthesizing company profile with LLM")
        
        # Build context for LLM
        context = f"Company: {company_name}\n\n"
        
        if website_data.get("url"):
            context += f"Website: {website_data['url']}\n\n"
        
        if website_data.get("homepage_text"):
            context += f"Homepage Content:\n{website_data['homepage_text']}\n\n"
        
        if website_data.get("about_text"):
            context += f"About Page Content:\n{website_data['about_text']}\n\n"
        
        if wiki_text:
            context += f"Wikipedia Content:\n{wiki_text}\n\n"
        
        prompt = f"""{context}

Based on the above information about {company_name}, extract and structure the following details in JSON format:

{{
  "company_name": "Official company name",
  "ticker": "Stock ticker symbol (if mentioned, otherwise null)",
  "website": "Official website URL",
  "industry": "Primary industry",
  "sector": "Business sector",
  "founded": "Year or date founded",
  "headquarters": "Headquarters location",
  "employees": "Number of employees (as integer, null if unknown)",
  "description": "Brief 2-3 sentence description of what the company does",
  "products": ["List", "of", "main", "products"]  or services],
  "key_people": [{{"name": "Person Name", "role": "CEO/Founder/etc"}}]
}}

Important:
- Extract only factual information present in the source material
- Use null for missing information
- Keep the description concise and factual
- Only include top 3-5 products/services
- Only include top 3-5 key people

Return ONLY valid JSON, no additional text."""

        response = self._llm_generate(prompt, temperature=0.3, max_tokens=1500)
        
        if response is None:
            return {}
        
        # Parse JSON response
        try:
            import json
            # Extract JSON from response (handle potential markdown code blocks)
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            profile = json.loads(response)
            return profile
        except json.JSONDecodeError as e:
            self._add_error(f"Failed to parse LLM JSON response: {e}")
            return {}
    
    def execute(self, company_name: str, ticker: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute the company profile research workflow.
        
        Args:
            company_name: Name of the company
            ticker: Optional stock ticker symbol
            
        Returns:
            Dictionary with company profile data
        """
        # Generate cache key
        cache_key = self._generate_cache_key(company_name=company_name, ticker=ticker)
        
        def _execute():
            # Step 1: Find company website
            website = self._find_company_website(company_name)
            
            # Step 2: Scrape company website
            website_data = {}
            if website:
                website_data = self._scrape_company_website(website)
            
            # Step 3: Scrape Wikipedia
            wiki_text = self._scrape_wikipedia(company_name)
            
            # Step 4: Synthesize profile with LLM
            profile = self._synthesize_profile(company_name, website_data, wiki_text)
            
            # Ensure ticker is included if provided
            if ticker and not profile.get("ticker"):
                profile["ticker"] = ticker
            
            return profile
        
        # Execute with caching (24 hour TTL)
        result = self._execute_with_cache(cache_key, _execute, ttl_hours=24)
        
        return result
