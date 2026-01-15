"""
News Intelligence Agent - LangGraph Node Implementation

Gathers and analyzes news and media coverage with reasoning for source prioritization,
credibility assessment, and event categorization.
"""

from typing import List, Dict, Any
from datetime import datetime, timedelta

from app.core.state_schema import CompanyResearchState, Source, NewsArticle, NewsData
from app.core.reasoning_chain import ReasoningChain
from app.core.trust_scorer import get_trust_scorer
from app.core.mode_config import get_config_value
from app.core.llm_manager import get_llm_manager
from app.utils.web_scraper import get_web_scraper
from app.utils.logger import logger


def news_intelligence_node(state: CompanyResearchState) -> CompanyResearchState:
    """
    News Intelligence LangGraph node.
    
    Workflow:
    1. Search for recent news with reasoning for timeframe
    2. Prioritize sources by credibility (Reuters > blogs)
    3. Handle conflicting reports with cross-verification
    4. Categorize events and assess significance
    5. Build timeline with reasoning
    
    Args:
        state: Current research state
        
    Returns:
        Updated state with news_data populated
    """
    logger.info("🚀 Starting NewsIntelligenceNode")
    
    # Initialize
    reasoning = ReasoningChain("NewsIntelligenceAgent")
    web_scraper = get_web_scraper()
    llm_manager = get_llm_manager()
    trust_scorer = get_trust_scorer()
    
    # Get configuration
    mode = state.get("mode", "fast")
    months_back = get_config_value(mode, "news_months_back", 6)
    max_articles = get_config_value(mode, "news_max_articles", 20)
    detailed_events = get_config_value(mode, "news_detailed_events", False)
    
    company_name = state["company_name"]
    
    try:
        # Step 1: Search for news
        logger.info(f"🔍 Searching for news about {company_name} (last {months_back} months)")
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months_back * 30)
        
        reasoning.add_step(
            decision=f"Search news for {months_back} months",
            rationale=f"{mode} mode configured for {months_back} months of news history",
            alternatives_considered=["3 months", "6 months", "12 months", "24+ months"],
            chosen_option=f"{months_back} months ({mode} mode)",
            confidence=0.95
        )
        
        
        # Search Google News using dedicated news endpoint
        logger.info(f"Searching Google News for {company_name}")
        search_results = web_scraper.search_google_news(
            query=company_name,
            months_back=months_back,
            num_results=max_articles * 2
        )
        
        if not search_results:
            reasoning.add_step(
                decision="No news found",
                rationale="Search returned no results",
                alternatives_considered=["Try alternative queries", "Skip news"],
                chosen_option="Skip news research",
                confidence=1.0
            )
            return {
                "warnings": ["No news articles found"],
                "reasoning_chains": {"news": reasoning.to_list()},
                "completed_nodes": ["news"]
            }
        
        logger.info(f"Found {len(search_results)} news results")
        
        # Step 2: Filter and prioritize by source credibility
        articles_with_trust = []
        
        for result in search_results:
            url = result.get('url', '')
            title = result.get('title', '')
            snippet = result.get('snippet', '')
            
            # Score source
            source_type, trust_score = trust_scorer.categorize_source(url)
            
            # Filter low-trust sources in fast mode
            if mode == "fast" and trust_score < 0.5:
                continue
            
            articles_with_trust.append({
                'url': url,
                'title': title,
                'snippet': snippet,
                'source_type': source_type,
                'trust_score': trust_score
            })
        
        # Sort by trust score (high to low)
        articles_with_trust.sort(key=lambda x: x['trust_score'], reverse=True)
        
        # Trim to max_articles
        articles_with_trust = articles_with_trust[:max_articles]
        
        reasoning.add_step(
            decision=f"Filter and prioritize {len(articles_with_trust)} articles",
            rationale=f"Filtered to top {max_articles} articles by trust score. "
                      f"Excluded {len(search_results) - len(articles_with_trust)} low-quality sources.",
            alternatives_considered=["Include all sources", "Only tier-1 news", "Weighted selection"],
            chosen_option="Prioritize by trust score",
            confidence=0.9
        )
        
        logger.info(f"Selected {len(articles_with_trust)} prioritized articles")
        
        # Step 3: Use LLM to categorize and analyze
        logger.info("🤖 Analyzing news articles with LLM")
        
        # Build context for LLM
        articles_text = []
        for i, article in enumerate(articles_with_trust, 1):
            articles_text.append(
                f"Article {i}:\n"
                f"Title: {article['title']}\n"
                f"Source: {article['url']}\n"
                f"Trust Score: {article['trust_score']:.2f}\n"
                f"Snippet: {article['snippet']}\n"
            )
        
        context = "\n\n".join(articles_text)
        
        prompt = f"""Analyze the following news articles about {company_name} and provide structured insights.

{context}

For each article, provide:
1. Category (Financial Results, Product Launch, Legal/Regulatory, M&A, Leadership Change, Controversy, Other)
2. Sentiment (Positive, Negative, Neutral)
3. Significance score (0.0-1.0, how important this news is)
4. Brief summary (1 sentence)

Also identify:
- Major events (significance > 0.7) for a timeline
- Overall sentiment distribution
- Any conflicting reports that need clarification

Return in JSON format:
{{
  "articles": [
    {{
      "index": 1,
      "category": "Category",
      "sentiment": "Positive/Negative/Neutral",
      "significance": 0.8,
      "summary": "Brief summary"
    }}
  ],
  "timeline": [
    {{
      "event": "Major event description",
      "date": "Approximate date from article",
      "significance": 0.9
    }}
  ],
  "sentiment_distribution": {{
    "positive": 0.5,
    "negative": 0.2,
    "neutral": 0.3
  }},
  "conflicts": [
    {{
      "description": "Description of conflicting reports",
      "articles": [1, 3]
    }}
  ]
}}

Return ONLY valid JSON."""

        result = llm_manager.generate(prompt, temperature=0.4, max_tokens=2000)
        
        if not result.get("success"):
            return {
                "errors": [f"LLM news analysis failed: {result.get('error')}"],
                "reasoning_chains": {"news": reasoning.to_list()},
                "completed_nodes": ["news"]
            }
        
        response_text = result.get("text", "")
        
        # Parse JSON
        try:
            import json
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            analysis = json.loads(response_text)
            
            reasoning.add_step(
                decision="LLM categorization successful",
                rationale=f"Categorized {len(analysis.get('articles', []))} articles with sentiment and significance",
                alternatives_considered=["Rule-based categorization", "LLM analysis"],
                chosen_option="LLM for nuanced understanding",
                confidence=0.85
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return {
                "errors": ["Failed to parse news analysis"],
                "reasoning_chains": {"news": reasoning.to_list()},
                "completed_nodes": ["news"]
            }
        
        # Handle conflicts
        conflicts = analysis.get('conflicts', [])
        ambiguities = []
        if conflicts:
            for conflict in conflicts:
                reasoning.add_contradiction_resolution(
                    data_field="news_event",
                    conflicting_values=[conflict['description']],
                    resolved_value="Flagged for review",
                    rationale=f"Multiple outlets report conflicting information. Articles {conflict['articles']} need cross-verification.",
                    confidence=0.6
                )
                
                ambiguities.append({
                    "type": "conflicting_news",
                    "description": conflict['description'],
                    "articles": conflict['articles'],
                    "resolved": False
                })
        
        # Step 5: Build structured news data
        news_articles: List[NewsArticle] = []
        categories_count: Dict[str, int] = {}
        sources_list: List[Source] = []
        
        for i, article_data in enumerate(articles_with_trust):
            # Find corresponding analysis
            article_analysis = None
            for a in analysis.get('articles', []):
                if a.get('index') == i + 1:
                    article_analysis = a
                    break
            
            if not article_analysis:
                continue
            
            # Create source
            source = Source(
                url=article_data['url'],
                title=article_data['title'],
                source_type=article_data['source_type'],
                access_date=datetime.now().isoformat(),
                page_numbers=None,
                trust_score=article_data['trust_score']
            )
            
            sources_list.append(source)
            
            # Create news article
            category = article_analysis.get('category', 'Other')
            categories_count[category] = categories_count.get(category, 0) + 1
            
            news_article = NewsArticle(
                date=datetime.now().isoformat(),  # Ideally parse from article
                title=article_data['title'],
                summary=article_analysis.get('summary', article_data['snippet']),
                source=source,
                category=category,
                significance_score=article_analysis.get('significance')
            )
            
            news_articles.append(news_article)
        
        # Build news data
        news_data: NewsData = {
            "articles": news_articles,
            "total_articles": len(news_articles),
            "date_range": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat()
            },
            "categories": categories_count,
            "timeline": analysis.get('timeline', []),
            "sentiment_distribution": analysis.get('sentiment_distribution', {})
        }
        # Calculate aggregate trust
        avg_trust = trust_scorer.aggregate_trust_scores(sources_list)
        
        logger.info(f"✅ News research completed: {len(news_articles)} articles, avg trust {avg_trust:.2f}")
        logger.info(f"📊 Reasoning steps: {len(reasoning.steps)}, Avg confidence: {reasoning.get_average_confidence():.2f}")
        
        return {
            "news_data": news_data,
            "reasoning_chains": {"news": reasoning.to_list()},
            "sources": {"news": sources_list},
            "trust_scores": {"news": avg_trust},
            "ambiguities": ambiguities,
            "completed_nodes": ["news"]
        }
        
    except Exception as e:
        logger.exception("💥 NewsIntelligenceNode failed")
        return {
            "errors": [f"NewsIntelligenceNode error: {str(e)}"],
            "reasoning_chains": {"news": ReasoningChain("NewsIntelligenceAgent").to_list()},
            "completed_nodes": ["news"]
        }
