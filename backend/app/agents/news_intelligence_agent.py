"""
News Intelligence Agent - Gathers and analyzes recent news about a company.

Workflow:
1. Search for recent news articles
2. Scrape article content
3. Categorize articles by topic
4. Create timeline of events
5. Extract major themes
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from app.agents.base_agent import BaseAgent
from app.utils.web_scraper import get_web_scraper
from app.utils.logger import logger


class NewsIntelligenceAgent(BaseAgent):
    """Agent for gathering and analyzing news articles."""
    
    def __init__(self):
        """Initialize the news intelligence agent."""
        super().__init__(name="NewsIntelligenceAgent", use_cache=True)
        self.web_scraper = get_web_scraper()
        self.total_steps = 5
    
    def _search_news(self, company_name: str, months_back: int = 12) -> List[Dict[str, str]]:
        """Search for recent news articles."""
        self._log_step(f"Searching for news about {company_name}")
        
        # Calculate date range
        from_date = datetime.now() - timedelta(days=months_back * 30)
        date_str = from_date.strftime("%Y")
        
        # Search Google News
        queries = [
            f"{company_name} news {date_str}",
            f"{company_name} announcement {date_str}",
            f"{company_name} latest news"
        ]
        
        all_articles = []
        seen_urls = set()
        
        for query in queries:
            results = self.web_scraper.search_google(query, num_results=15)
            
            for result in results:
                url = result['url']
                if url not in seen_urls:
                    seen_urls.add(url)
                    all_articles.append(result)
        
        logger.info(f"Found {len(all_articles)} unique articles")
        return all_articles[:30]  # Limit to 30 articles
    
    def _scrape_articles(self, articles: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Scrape full content from article URLs."""
        self._log_step("Scraping article content")
        
        scraped_articles = []
        
        for article in articles:
            soup = self.web_scraper.fetch_and_parse(article['url'])
            
            if soup is None:
                continue
            
            # Extract article content (basic heuristic)
            # Try common article content selectors
            content = ""
            for selector in ['article', '.article-body', '.post-content', 'main']:
                element = soup.select_one(selector)
                if element:
                    content = self.web_scraper.extract_text(element)
                    break
            
            # Fallback to full page text
            if not content:
                content = self.web_scraper.extract_text(soup)
            
            # Get metadata for date and source
            metadata = self.web_scraper.extract_metadata(soup)
            
            # Try multiple metadata fields for publication date
            published_date = (
                metadata.get('article:published_time') or 
                metadata.get('og:pubdate') or 
                metadata.get('pubdate') or 
                metadata.get('datePublished') or 
                metadata.get('date') or
                'Unknown'
            )
            
            # Truncate title if it's too long
            title = article.get('title', metadata.get('title', 'Untitled'))
            if len(title) > 120:
                title = title[:117] + "..."
            
            scraped_articles.append({
                'title': title,
                'url': article['url'],
                'content': content[:5000],  # Limit content length
                'published_date': published_date,
                'source': metadata.get('og:site_name', 'Unknown')
            })
        
        logger.info(f"Successfully scraped {len(scraped_articles)} articles")
        return scraped_articles
    
    def _categorize_and_summarize(self, articles: List[Dict[str, Any]], company_name: str) -> List[Dict[str, Any]]:
        """Use LLM to categorize and summarize articles."""
        self._log_step("Categorizing and summarizing articles with LLM")
        
        if not articles:
            return []
        
        categorized_articles = []
        
        # Process articles in batches to avoid token limits
        batch_size = 3
        for i in range(0, len(articles), batch_size):
            batch = articles[i:i+batch_size]
            
            # Build context for batch
            articles_text = ""
            for idx, article in enumerate(batch):
                articles_text += f"\n\n--- Article {idx + 1} ---\n"
                articles_text += f"Title: {article['title']}\n"
                articles_text += f"URL: {article['url']}\n"
                articles_text += f"Content: {article['content'][:2000]}\n"
            
            prompt = f"""Analyze these news articles about {company_name} and provide structured information.

{articles_text}

For each article, return a JSON array with objects containing:

[
  {{
    "article_number": 1,
    "category": "Product Launch|Acquisition|Financial Results|Leadership|Controversy|Partnership|Other",
    "sentiment": "Positive|Neutral|Negative",
    "summary": "One sentence summary of the article",
    "key_points": ["Key", "point", "one", "or", "two"]
  }}
]

Important:
- Be concise with summaries and key points
- Choose the most appropriate category
- Assess sentiment based on overall tone

Return ONLY valid JSON array, no additional text."""

            response = self._llm_generate(prompt, temperature=0.5, max_tokens=1500)
            
            if response is None:
                continue
            
            # Parse JSON response
            try:
                import json
                if "```json" in response:
                    response = response.split("```json")[1].split("```")[0].strip()
                elif "```" in response:
                    response = response.split("```")[1].split("```")[0].strip()
                
                batch_results = json.loads(response)
                
                # Map results back to articles
                for result in batch_results:
                    article_idx = result.get("article_number", 1) - 1
                    if 0 <= article_idx < len(batch):
                        article = batch[article_idx].copy()
                        article['category'] = result.get('category', 'Other')
                        article['sentiment'] = result.get('sentiment', 'Neutral')
                        article['summary'] = result.get('summary', '')
                        article['key_points'] = result.get('key_points', [])
                        categorized_articles.append(article)
            except Exception as e:
                logger.warning(f"Error parsing batch results: {e}")
                continue
        
        return categorized_articles
    
    def _create_timeline_and_themes(self, articles: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create timeline and extract major themes."""
        self._log_step("Creating timeline and extracting themes")
        
        # Group by category
        categories = {}
        for article in articles:
            category = article.get('category', 'Other')
            if category not in categories:
                categories[category] = []
            categories[category].append(article)
        
        # Extract major events (filtered by category)
        major_events = []
        important_categories = ['Acquisition', 'Product Launch', 'Leadership', 'Financial Results']
        
        for article in articles:
            if article.get('category') in important_categories:
                # Parse date if it's a string
                date_str = article.get('published_date', 'Unknown')
                if date_str and date_str != 'Unknown':
                    try:
                        from dateutil import parser
                        parsed_date = parser.parse(date_str)
                        date_str = parsed_date.strftime('%Y-%m-%d')
                    except:
                        pass  # Keep original if parsing fails
                
                major_events.append({
                    'title': article['title'],
                    'date': date_str,
                    'category': article['category'],
                    'summary': article.get('summary', ''),
                    'url': article.get('url', '')  # Add URL for citations
                })
        
        # Count sentiments
        sentiment_counts = {'Positive': 0, 'Neutral': 0, 'Negative': 0}
        for article in articles:
            sentiment = article.get('sentiment', 'Neutral')
            sentiment_counts[sentiment] = sentiment_counts.get(sentiment, 0) + 1
        
        return {
            'categories': {k: len(v) for k, v in categories.items()},
            'major_events': major_events,
            'sentiment_distribution': sentiment_counts
        }
    
    def execute(self, company_name: str, months_back: int = 12) -> Dict[str, Any]:
        """
        Execute the news intelligence workflow.
        
        Args:
            company_name: Name of the company
            months_back: How many months of news to gather
            
        Returns:
            Dictionary with news articles and analysis
        """
        # Generate cache key
        cache_key = self._generate_cache_key(company_name=company_name, months_back=months_back)
        
        def _execute():
            # Step 1: Search for news
            articles = self._search_news(company_name, months_back)
            
            if not articles:
                return {
                    "articles": [],
                    "error": "No news articles found"
                }
            
            # Step 2: Scrape articles
            scraped_articles = self._scrape_articles(articles)
            
            # Step 3: Categorize and summarize
            categorized_articles = self._categorize_and_summarize(scraped_articles, company_name)
            
            # Step 4: Create timeline and extract themes
            analysis = self._create_timeline_and_themes(categorized_articles)
            
            return {
                "articles": categorized_articles,
                "total_articles": len(categorized_articles),
                "timeline": analysis['major_events'],
                "categories": analysis['categories'],
                "sentiment_distribution": analysis['sentiment_distribution']
            }
        
        # Execute with caching (6 hour TTL since news changes frequently)
        result = self._execute_with_cache(cache_key, _execute, ttl_hours=6)
        
        return result
