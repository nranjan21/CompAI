"""
Insight Synthesizer - Combines research results into actionable insights.
"""

from typing import Dict, Any, List
from app.core.llm_manager import get_llm_manager
from app.utils.logger import logger


class InsightSynthesizer:
    """Synthesizes research results into key insights and recommendations."""
    
    def __init__(self):
        """Initialize the insight synthesizer."""
        self.llm_manager = get_llm_manager()
        logger.info("🔮 Initialized InsightSynthesizer")
    
    def synthesize(self, research_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synthesize research results into actionable insights.
        
        Args:
            research_results: Complete research results from orchestrator
            
        Returns:
            Dictionary with synthesized insights
        """
        logger.info("🔮 Synthesizing insights from research results")
        
        company_name = research_results.get("company_name", "Unknown Company")
        
        # Extract key data from each section
        profile = research_results.get("profile", {})
        financial = research_results.get("financial", {})
        news = research_results.get("news", {})
        sentiment = research_results.get("sentiment", {})
        competitive = research_results.get("competitive", {})
        
        # Build context for LLM
        context = self._build_context(company_name, profile, financial, news, sentiment, competitive)
        
        # Generate insights using LLM
        insights = self._generate_insights(context, company_name)
        
        return insights
    
    def _build_context(self, company_name: str, profile: Dict, financial: Dict, 
                      news: Dict, sentiment: Dict, competitive: Dict) -> str:
        """Build context string from research results."""
        
        context = f"# Research Results for {company_name}\n\n"
        
        # Company Profile
        if profile:
            context += "## Company Profile\n"
            context += f"- Industry: {profile.get('industry', 'N/A')}\n"
            context += f"- Founded: {profile.get('founded', 'N/A')}\n"
            context += f"- Headquarters: {profile.get('headquarters', 'N/A')}\n"
            context += f"- Description: {profile.get('description', 'N/A')}\n\n"
        
        # Financial Data
        if financial:
            context += "## Financial Performance\n"
            context += f"- Revenue: ${financial.get('revenue', 'N/A')}M\n"
            context += f"- Net Income: ${financial.get('net_income', 'N/A')}M\n"
            context += f"- Financial Health: {financial.get('financial_health', 'N/A')}\n\n"
        
        # News & Sentiment
        if news:
            context += "## Recent News\n"
            context += f"- Total Articles: {news.get('total_articles', 0)}\n"
            context += f"- Categories: {news.get('categories', {})}\n\n"
        
        if sentiment:
            context += "## Sentiment Analysis\n"
            context += f"- Overall Sentiment: {sentiment.get('overall_sentiment', 'N/A')}\n"
            context += f"- Trend: {sentiment.get('sentiment_trend', 'N/A')}\n\n"
        
        # Competitive Landscape
        if competitive:
            swot = competitive.get('swot', {})
            if swot:
                context += "## SWOT Analysis\n"
                context += f"- Strengths: {len(swot.get('strengths', []))}\n"
                context += f"- Weaknesses: {len(swot.get('weaknesses', []))}\n"
                context += f"- Opportunities: {len(swot.get('opportunities', []))}\n"
                context += f"- Threats: {len(swot.get('threats', []))}\n\n"
        
        return context
    
    def _generate_insights(self, context: str, company_name: str) -> Dict[str, Any]:
        """Generate insights using LLM."""
        
        prompt = f"""{context}

Based on the research results above for {company_name}, provide a comprehensive analysis with:

1. **Executive Summary** (2-3 sentences)
2. **Key Insights** (3-5 bullet points)
3. **Investment Thesis** (if applicable)
4. **Risk Factors** (top 3)
5. **Opportunities** (top 3)
6. **Recommendations** (2-3 actionable items)

Return the analysis in JSON format:

{{
  "executive_summary": "Brief overview...",
  "key_insights": ["Insight 1", "Insight 2", "Insight 3"],
  "investment_thesis": "Investment perspective...",
  "risk_factors": ["Risk 1", "Risk 2", "Risk 3"],
  "opportunities": ["Opportunity 1", "Opportunity 2", "Opportunity 3"],
  "recommendations": ["Recommendation 1", "Recommendation 2"]
}}

Return ONLY valid JSON, no additional text."""

        try:
            result = self.llm_manager.generate(prompt, temperature=0.5, max_tokens=2000)
            
            if result.get("success"):
                response_text = result.get("text", "")
                
                # Parse JSON
                import json
                if "```json" in response_text:
                    response_text = response_text.split("```json")[1].split("```")[0].strip()
                elif "```" in response_text:
                    response_text = response_text.split("```")[1].split("```")[0].strip()
                
                insights = json.loads(response_text)
                logger.info("✅ Successfully generated insights")
                return insights
            else:
                logger.warning("⚠️ LLM failed to generate insights")
                return self._get_default_insights()
        except Exception as e:
            logger.error(f"❌ Error generating insights: {e}")
            return self._get_default_insights()
    
    def _get_default_insights(self) -> Dict[str, Any]:
        """Return default insights structure if LLM fails."""
        return {
            "executive_summary": "Research completed successfully. Detailed analysis available in full report.",
            "key_insights": ["Research data gathered from multiple sources"],
            "investment_thesis": "Further analysis recommended",
            "risk_factors": ["Market volatility", "Competitive pressure", "Regulatory changes"],
            "opportunities": ["Market expansion", "Innovation", "Strategic partnerships"],
            "recommendations": ["Monitor key metrics", "Review quarterly updates"]
        }
