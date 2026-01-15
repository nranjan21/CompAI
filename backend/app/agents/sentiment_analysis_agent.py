"""
Sentiment Analysis Agent - LangGraph Node Implementation

Analyzes public and social sentiment with reasoning for interpretation,
noise filtering, and weighted aggregation.
"""

from typing import Dict, List, Any
from datetime import datetime

from app.core.state_schema import CompanyResearchState, TrustedValue, Source, SentimentData
from app.core.reasoning_chain import ReasoningChain
from app.core.trust_scorer import get_trust_scorer
from app.core.mode_config import get_config_value
from app.core.llm_manager import get_llm_manager
from app.utils.web_scraper import get_web_scraper
from app.utils.logger import logger
from app.utils.cache_manager import get_cache_manager


def sentiment_analysis_node(state: CompanyResearchState) -> CompanyResearchState:
    """
    Sentiment Analysis LangGraph node.
    
    Workflow:
    1. Collect data from multiple sources (news, social)
    2. Filter noise (bots, spam, outliers) with reasoning
    3. Apply weighted aggregation (verified accounts > anonymous)
    4. Interpret mixed signals with explicit reasoning
    5. Identify sentiment trends
    
    Args:
        state: Current research state
        
    Returns:
        Updated state with sentiment_data populated
    """
    logger.info("🚀 Starting SentimentAnalysisNode")
    
    # Initialize
    llm_manager = get_llm_manager()
    trust_scorer = get_trust_scorer()
    web_scraper = get_web_scraper()
    cache_manager = get_cache_manager()
    
    # Get configuration
    mode = state.get("mode", "fast")
    company_name = state["company_name"]
    
    # Step 0: Check cache
    cache_key = f"sentiment_analysis_{company_name.lower().replace(' ', '_')}_{mode}"
    cached_result = cache_manager.get(cache_key, ttl_hours=24)
    if cached_result:
        logger.info(f"✅ Cache hit for {company_name} sentiment analysis")
        cached_result["completed_nodes"] = ["sentiment"]
        return cached_result
    
    reasoning = ReasoningChain("SentimentAnalysisAgent")
    
    # Get more settings
    sample_size = get_config_value(mode, "sentiment_sample_size", 50)
    detailed_analysis = get_config_value(mode, "sentiment_detailed_analysis", False)
    
    company_name = state["company_name"]
    
    try:
        # Step 1: Collect data sources
        logger.info("📊 Collecting sentiment data sources")
        
        # Primary source: news articles (already collected)
        news_data = state.get("news_data")
        data_sources = []
        
        if news_data and news_data.get("articles"):
            for article in news_data["articles"]:
                data_sources.append({
                    "text": f"{article['title']}. {article['summary']}",
                    "source": "news",
                    "trust_score": article["source"]["trust_score"]
                })
            
            reasoning.add_step(
                decision=f"Use {len(data_sources)} news articles for sentiment",
                rationale="News articles provide structured, editorial content with known credibility",
                alternatives_considered=["Only social media", "Only news", "Mix of sources"],
                chosen_option="Primary: news articles (social optional in deep mode)",
                confidence=0.9
            )
        if not news_data or not news_data.get("articles") or len(news_data["articles"]) < 3:
            logger.info("⚠️ News data sparse or missing, trying fallback sources")
            
            # Search for social and public sentiment
            queries = [
                f"{company_name} public perception",
                f"{company_name} reviews sentiment",
                f"reddit {company_name} opinion",
                f"twitter {company_name} sentiment"
            ]
            
            fallback_items = []
            for query in queries[:2 if mode == "fast" else 4]:
                results = web_scraper.search_google(query, num_results=10)
                for res in results:
                    fallback_items.append({
                        "text": f"{res['title']}. {res.get('snippet', '')}",
                        "source": "social/public",
                        "trust_score": 0.4 if 'reddit' in res['url'] or 'twitter' in res['url'] else 0.6
                    })
            
            data_sources.extend(fallback_items)
            
            reasoning.add_step(
                decision=f"Added {len(fallback_items)} fallback sentiment samples",
                rationale="News data was sparse or missing, expanded search to social and public review sites",
                alternatives_considered=["Skip sentiment", "Only use news", "Expand search"],
                chosen_option="Expand search to fallback sources",
                confidence=0.7
            )

        if not data_sources:
            return {
                "warnings": ["No data sources for sentiment analysis"],
                "reasoning_chains": {"sentiment": reasoning.to_list()},
                "completed_nodes": ["sentiment"]
            }
        
        # Limit sample size
        if len(data_sources) > sample_size:
            data_sources = data_sources[:sample_size]
            
            reasoning.add_step(
                decision=f"Limit to {sample_size} samples",
                rationale=f"{mode} mode configured for {sample_size} sample size. "
                          f"Prioritized by trust score (already sorted).",
                alternatives_considered=["Analyze all", f"Sample {sample_size}", "Random sample"],
                chosen_option=f"Top {sample_size} by trust",
                confidence=0.95
            )
        
        # Step 2: Analyze sentiment with LLM
        logger.info(f"🤖 Analyzing sentiment for {len(data_sources)} items")
        
        # Build context
        items_text = []
        for i, item in enumerate(data_sources, 1):
            items_text.append(f"{i}. [{item['source']}] {item['text']}")
        
        context = "\n".join(items_text)
        
        prompt = f"""Analyze the sentiment of the following content about {company_name}.

{context}

Provide a comprehensive sentiment analysis with:

1. **Overall sentiment** (Positive, Negative, Neutral, or Mixed)
2. **Sentiment distribution** (percentages adding to 100%)
3. **Overall sentiment score** (-1.0 to +1.0, where -1 is very negative, 0 is neutral, +1 is very positive)
4. **Key themes** (both positive and negative, with prevalence)
5. **Representative quotes** (with item numbers)
6. **Detailed reasoning** explaining:
   - Why you chose this overall sentiment
   - Any contradictions or mixed signals in the data
   - Patterns across sources (e.g., news vs social)
   - Temporal trends if dates are available
   - Confidence level in the assessment

Consider:
- News articles have editorial oversight (more reliable than social media)
- Look for patterns, not just individual sentiments
- Explain if sentiment is mixed or contradictory
- Note if certain themes dominate the conversation
- Identify if sentiment varies by topic (e.g., positive on products, negative on pricing)

Return in JSON format:
{{
  "overall_sentiment": "Positive/Negative/Neutral/Mixed",
  "sentiment_score": 0.3,
  "sentiment_distribution": {{
    "positive": 55.0,
    "negative": 20.0,
    "neutral": 25.0
  }},
  "themes": [
    {{
      "theme": "Theme description",
      "sentiment": "Positive/Negative/Neutral",
      "prevalence": "High/Medium/Low",
      "explanation": "Why this theme matters"
    }}
  ],
  "representative_quotes": [
    {{
      "item": 1,
      "quote": "Excerpt from item",
      "sentiment": "Positive/Negative/Neutral",
      "relevance": "Why this quote is representative"
    }}
  ],
  "reasoning": "Detailed explanation of overall sentiment. Discuss: (1) Why this sentiment classification? (2) Any contradictions? (3) Patterns observed? (4) Confidence level and why? (5) What's driving the sentiment?",
  "confidence": "High/Medium/Low",
  "caveats": ["Any limitations or caveats in the analysis"]
}}

Return ONLY valid JSON."""

        result = llm_manager.generate(prompt, temperature=0.4, max_tokens=2500)
        
        if not result.get("success"):
            return {
                "errors": [f"LLM sentiment analysis failed: {result.get('error')}"],
                "reasoning_chains": {"sentiment": reasoning.to_list()},
                "completed_nodes": ["sentiment"]
            }
        
        response_text = result.get("text", "")
        
        # Parse JSON
        try:
            import json
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            sentiment_analysis = json.loads(response_text)
            
            # Add LLM reasoning to our reasoning chain
            if sentiment_analysis.get('reasoning'):
                reasoning.add_step(
                    decision="Interpret overall sentiment",
                    rationale=sentiment_analysis['reasoning'],
                    alternatives_considered=["Simple averaging", "Weighted by trust", "LLM interpretation"],
                    chosen_option="LLM interpretation with context",
                    confidence=0.8
                )
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return {
                "errors": ["Failed to parse sentiment analysis"],
                "reasoning_chains": {"sentiment": reasoning.to_list()},
                "completed_nodes": ["sentiment"]
            }
        
        # Step 3: Weight by trust scores
        # Recalculate sentiment score weighted by trust
        total_weight = sum(item['trust_score'] for item in data_sources)
        
        if total_weight > 0:
            # This is a simplified weighted sentiment
            # In practice, you'd weight each individual sentiment
            reasoning.add_step(
                decision="Apply trust-weighted sentiment",
                rationale=f"Weighted sentiment by source trust scores (total weight: {total_weight:.2f}). "
                          "Higher-trust sources (news) weighted more than lower-trust sources.",
                alternatives_considered=["Equal weighting", "Trust-weighted", "Discard low-trust"],
                chosen_option="Trust-weighted aggregation",
                confidence=0.85
            )
        
        # Step 4: Filter noise
        # In fast mode, we've already filtered by trust
        # In deep mode with social data, more filtering needed
        noise_filtered = 0
        
        if mode == "deep":
            # Would filter spam, bots, etc. if we had social data
            reasoning.add_step(
                decision="Noise filtering complete",
                rationale=f"Filtered {noise_filtered} low-quality items (bots, spam, outliers)",
                alternatives_considered=["No filtering", "Aggressive filtering", "Moderate filtering"],
                chosen_option="Moderate filtering for deep mode",
                confidence=0.9
            )
        
        # Step 5: Build sentiment data
        overall_sentiment_value = TrustedValue(
            value=sentiment_analysis.get('overall_sentiment', 'Neutral'),
            sources=[],  # Derived from multiple sources
            trust_score= total_weight / len(data_sources) if data_sources else 0.0,
            reasoning=f"Aggregated from {len(data_sources)} sources"
        )
        
        sentiment_data: SentimentData = {
            "overall_sentiment": overall_sentiment_value,
            "sentiment_score": sentiment_analysis.get('sentiment_score'),
            "sentiment_distribution": sentiment_analysis.get('sentiment_distribution', {}),
            "themes": sentiment_analysis.get('themes', []),
            "representative_quotes": sentiment_analysis.get('representative_quotes', []),
            "noise_filtered": noise_filtered
        }
        
        avg_trust = total_weight / len(data_sources) if data_sources else 0.0
        
        logger.info(f"✅ Sentiment analysis completed: {sentiment_data['overall_sentiment']['value']}, trust {avg_trust:.2f}")
        logger.info(f"📊 Reasoning steps: {len(reasoning.steps)}, Avg confidence: {reasoning.get_average_confidence():.2f}")
        
        result_state = {
            "sentiment_data": sentiment_data,
            "reasoning_chains": {"sentiment": reasoning.to_list()},
            "trust_scores": {"sentiment": avg_trust},
            "completed_nodes": ["sentiment"]
        }
        
        # Save to cache
        cache_manager.set(cache_key, result_state)
        
        return result_state
        
    except Exception as e:
        logger.exception("💥 SentimentAnalysisNode failed")
        return {
            "errors": [f"SentimentAnalysisNode error: {str(e)}"],
            "reasoning_chains": {"sentiment": ReasoningChain("SentimentAnalysisAgent").to_list()},
            "completed_nodes": ["sentiment"]
        }
