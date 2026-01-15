"""
Sentiment Analysis Agent - Analyzes sentiment across multiple data sources.

Workflow:
1. Receive input data (news articles, social media, reviews)
2. Clean and prepare text
3. Batch analyze with LLM
4. Score and categorize sentiment
5. Extract themes and trends
"""

from typing import Dict, Any, List, Optional
from app.agents.base_agent import BaseAgent
from app.utils.logger import logger


class SentimentAnalysisAgent(BaseAgent):
    """Agent for analyzing sentiment across data sources."""
    
    def __init__(self):
        """Initialize the sentiment analysis agent."""
        super().__init__(name="SentimentAnalysisAgent", use_cache=True)
        self.total_steps = 4
    
    def _prepare_text_data(self, data_sources: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, str]]:
        """Prepare and clean text data from multiple sources."""
        self._log_step("Preparing text data")
        
        prepared_data = []
        
        # Process news articles
        if 'news' in data_sources:
            for article in data_sources['news']:
                text = f"{article.get('title', '')} {article.get('summary', '')}"
                prepared_data.append({
                    'source': 'news',
                    'text': text,
                    'category': article.get('category', 'General')
                })
        
        # Process social media (if provided)
        if 'social' in data_sources:
            for post in data_sources['social']:
                prepared_data.append({
                    'source': 'social',
                    'text': post.get('text', ''),
                    'category': 'Social'
                })
        
        # Process reviews (if provided)
        if 'reviews' in data_sources:
            for review in data_sources['reviews']:
                prepared_data.append({
                    'source': 'review',
                    'text': review.get('text', ''),
                    'category': 'Review'
                })
        
        logger.info(f"Prepared {len(prepared_data)} text items for analysis")
        return prepared_data
    
    def _analyze_sentiment_batch(self, text_items: List[Dict[str, str]]) -> List[Dict[str, Any]]:
        """Analyze sentiment in batches using LLM."""
        self._log_step("Analyzing sentiment with LLM")
        
        analyzed_items = []
        batch_size = 5
        
        for i in range(0, len(text_items), batch_size):
            batch = text_items[i:i+batch_size]
            
            # Build prompt for batch
            batch_text = ""
            for idx, item in enumerate(batch):
                batch_text += f"\n\n--- Text {idx + 1} ---\n"
                batch_text += f"Source: {item['source']}\n"
                batch_text += f"Category: {item['category']}\n"
                batch_text += f"Text: {item['text'][:500]}\n"
            
            prompt = f"""Analyze the sentiment of each text below. For each text, provide:

{batch_text}

Return a JSON array with sentiment analysis for each text:

[
  {{
    "text_number": 1,
    "sentiment_score": <-1 to 1, where -1 is very negative, 0 is neutral, 1 is very positive>,
    "sentiment_label": "Positive|Neutral|Negative",
    "confidence": <0 to 1, confidence in the assessment>,
    "key_themes": ["theme1", "theme2"],
    "reasoning": "Brief explanation of sentiment assessment"
  }}
]

Important:
- Be nuanced with sentiment scores (use decimals like 0.7, -0.3, etc.)
- Identify 1-3 key themes mentioned
- Keep reasoning concise (one sentence)

Return ONLY valid JSON array, no additional text."""

            response = self._llm_generate(prompt, temperature=0.3, max_tokens=1500)
            
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
                
                # Map results back to items
                for result in batch_results:
                    text_idx = result.get("text_number", 1) - 1
                    if 0 <= text_idx < len(batch):
                        item = batch[text_idx].copy()
                        item['sentiment_score'] = result.get('sentiment_score', 0.0)
                        item['sentiment_label'] = result.get('sentiment_label', 'Neutral')
                        item['confidence'] = result.get('confidence', 0.5)
                        item['key_themes'] = result.get('key_themes', [])
                        item['reasoning'] = result.get('reasoning', '')
                        analyzed_items.append(item)
            except Exception as e:
                logger.warning(f"Error parsing batch results: {e}")
                continue
        
        return analyzed_items
    
    def _aggregate_results(self, analyzed_items: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Aggregate sentiment analysis results."""
        self._log_step("Aggregating sentiment results")
        
        if not analyzed_items:
            return {
                "overall_sentiment": 0.0,
                "sentiment_distribution": {},
                "themes": [],
                "sentiment_trend": "unknown"
            }
        
        # Calculate overall sentiment
        total_score = sum(item['sentiment_score'] for item in analyzed_items)
        overall_sentiment = total_score / len(analyzed_items)
        
        # Count sentiment labels
        label_counts = {'Positive': 0, 'Neutral': 0, 'Negative': 0}
        for item in analyzed_items:
            label = item.get('sentiment_label', 'Neutral')
            label_counts[label] = label_counts.get(label, 0) + 1
        
        # Extract themes
        theme_scores = {}
        for item in analyzed_items:
            for theme in item.get('key_themes', []):
                if theme not in theme_scores:
                    theme_scores[theme] = {'count': 0, 'total_score': 0.0}
                theme_scores[theme]['count'] += 1
                theme_scores[theme]['total_score'] += item['sentiment_score']
        
        # Calculate average sentiment per theme
        themes = []
        for theme, data in theme_scores.items():
            avg_sentiment = data['total_score'] / data['count']
            themes.append({
                'theme': theme,
                'sentiment': round(avg_sentiment, 2),
                'frequency': data['count']
            })
        
        # Sort themes by frequency
        themes.sort(key=lambda x: x['frequency'], reverse=True)
        
        # Determine sentiment trend
        if overall_sentiment > 0.3:
            trend = "positive"
        elif overall_sentiment < -0.3:
            trend = "negative"
        else:
            trend = "neutral"
        
        return {
            "overall_sentiment": round(overall_sentiment, 2),
            "sentiment_distribution": label_counts,
            "themes": themes[:10],  # Top 10 themes
            "sentiment_trend": trend,
            "analyzed_items_count": len(analyzed_items),
            "detailed_items": analyzed_items
        }
    
    def execute(self, data_sources: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """
        Execute the sentiment analysis workflow.
        
        Args:
            data_sources: Dictionary with keys 'news', 'social', 'reviews', each containing list of items
            
        Returns:
            Dictionary with sentiment analysis results
        """
        # Generate cache key
        cache_key = self._generate_cache_key(data_sources=str(data_sources)[:1000])
        
        def _execute():
            # Step 1: Prepare text data
            prepared_data = self._prepare_text_data(data_sources)
            
            if not prepared_data:
                return {
                    "overall_sentiment": 0.0,
                    "error": "No data to analyze"
                }
            
            # Step 2: Analyze sentiment
            analyzed_items = self._analyze_sentiment_batch(prepared_data)
            
            # Step 3: Aggregate results
            aggregated = self._aggregate_results(analyzed_items)
            
            return aggregated
        
        # Execute with caching (6 hour TTL)
        result = self._execute_with_cache(cache_key, _execute, ttl_hours=6)
        
        return result
