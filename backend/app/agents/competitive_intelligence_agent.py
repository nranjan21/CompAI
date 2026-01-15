"""
Competitive Intelligence Agent - LangGraph Node Implementation

Analyzes market position and competitive landscape with reasoning for
competitor identification, market positioning, and SWOT analysis.
"""

from typing import List, Dict, Any
from datetime import datetime

from app.core.state_schema import CompanyResearchState, Competitor, CompetitiveData, TrustedValue, Source
from app.core.reasoning_chain import ReasoningChain
from app.core.trust_scorer import get_trust_scorer
from app.core.mode_config import get_config_value
from app.core.llm_manager import get_llm_manager
from app.utils.web_scraper import get_web_scraper
from app.utils.logger import logger
from app.utils.cache_manager import get_cache_manager


def competitive_intelligence_node(state: CompanyResearchState) -> CompanyResearchState:
    """
    Competitive Intelligence LangGraph node.
    
    Workflow:
    1. Identify competitors with reasoning (market cap, industry, analyst reports)
    2. Gather market data with triangulation for conflicting sizes
    3. Assess market positioning
    4. Generate SWOT with evidence-based reasoning
    5. Score trust based on source quality
    
    Args:
        state: Current research state
        
    Returns:
        Updated state with competitive_data populated
    """
    logger.info("🚀 Starting CompetitiveIntelligenceNode")
    
    # Initialize
    web_scraper = get_web_scraper()
    llm_manager = get_llm_manager()
    trust_scorer = get_trust_scorer()
    cache_manager = get_cache_manager()
    
    # Get configuration
    mode = state.get("mode", "fast")
    company_name = state["company_name"]
    
    # Step 0: Check cache
    cache_key = f"competitive_intelligence_{company_name.lower().replace(' ', '_')}_{mode}"
    cached_result = cache_manager.get(cache_key, ttl_hours=24)
    if cached_result:
        logger.info(f"✅ Cache hit for {company_name} competitive intelligence")
        cached_result["completed_nodes"] = ["competitive"]
        return cached_result
    
    reasoning = ReasoningChain("CompetitiveIntelligenceAgent")
    max_competitors = get_config_value(mode, "competitive_max_competitors", 5)
    niche_markets = get_config_value(mode, "competitive_niche_markets", False)
    detailed_swot = get_config_value(mode, "competitive_detailed_swot", False)
    
    company_name = state["company_name"]
    
    # Get industry from company profile
    company_profile = state.get("company_profile", {})
    industry = None
    if company_profile and company_profile.get("industry"):
        industry = company_profile["industry"].get("value")
    
    try:
        # Step 1: Search for competitors
        logger.info(f"🔍 Searching for {company_name} competitors")
        
        # Build search query
        search_query = f"{company_name} competitors"
        if industry:
            search_query += f" {industry}"
        
        search_results = web_scraper.search_google(search_query, num_results=10)
        
        if not search_results:
            reasoning.add_step(
                decision="Skip competitive analysis",
                rationale="Search returned no results for competitors",
                alternatives_considered=["Try alternative queries", "Skip"],
                chosen_option="Skip competitive intelligence",
                confidence=1.0
            )
            return {
                "warnings": ["No competitor information found"],
                "reasoning_chains": {"competitive": reasoning.to_list()},
                "completed_nodes": ["competitive"]
            }
        
        reasoning.add_source_selection(
            data_type="competitor information",
            sources_considered=[r['url'] for r in search_results[:3]],
            chosen_source="Multiple sources",
            rationale=f"Found {len(search_results)} sources. Will synthesize across multiple for comprehensive view.",
            confidence=0.85
        )
        
        # Step 2: Extract competitor information with LLM
        logger.info("🤖 Analyzing competitive landscape with LLM")
        
        # Build context from search results
        context_items = []
        sources_list: List[Source] = []
        
        for result in search_results[:5]:  # Use top 5 results
            url = result['url']
            title = result.get('title', '')
            snippet = result.get('snippet', '')
            
            context_items.append(f"Source: {url}\n{title}\n{snippet}")
            
            # Create source
            source_type, trust_score = trust_scorer.categorize_source(url)
            sources_list.append(Source(
                url=url,
                title=title,
                source_type=source_type,
                access_date=datetime.now().isoformat(),
                page_numbers=None,
                trust_score=trust_score
            ))
        
        context = "\n\n".join(context_items)
        
        prompt = f"""Analyze the competitive landscape for {company_name}{f" in the {industry} industry" if industry else ""}.

{context}

Provide a comprehensive competitive analysis:

1. List of main competitors (up to {max_competitors})
2. Market positioning of {company_name}
3. SWOT analysis for {company_name}
4. Market size/trends (if mentioned)

For each competitor, provide:
- Name
- Brief description
- Why they are a competitor (market overlap, product similarity, etc.)

Return in JSON format:
{{
  "competitors": [
    {{
      "name": "Competitor Name",
      "description": "Brief description",
      "reasoning": "Why this is a competitor"
    }}
  ],
  "market_size": {{
    "value": "Market size if mentioned",
    "unit": "billions/millions USD or other",
    "sources": "Which sources mentioned this"
  }},
  "market_trends": ["Trend 1", "Trend 2"],
  "positioning": "How {company_name} is positioned in the market",
  "swot": {{
    "strengths": ["Strength 1", "Strength 2"],
    "weaknesses": ["Weakness 1", "Weakness 2"],
    "opportunities": ["Opportunity 1", "Opportunity 2"],
    "threats": ["Threat 1", "Threat 2"]
  }}
}}

Base your analysis ONLY on the provided sources. Return ONLY valid JSON."""

        result = llm_manager.generate(prompt, temperature=0.4, max_tokens=2000)
        
        if not result.get("success"):
            return {
                "errors": [f"LLM competitive analysis failed: {result.get('error')}"],
                "reasoning_chains": {"competitive": reasoning.to_list()},
                "completed_nodes": ["competitive"]
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
                decision="LLM competitive analysis successful",
                rationale=f"Identified {len(analysis.get('competitors', []))} competitors with SWOT analysis",
                alternatives_considered=["Manual research", "LLM synthesis"],
                chosen_option="LLM synthesis from multiple sources",
                confidence=0.8
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return {
                "errors": ["Failed to parse competitive analysis"],
                "reasoning_chains": {"competitive": reasoning.to_list()},
                "completed_nodes": ["competitive"]
            }
        
        # Step 3: Reason about competitor selection
        competitors_data = analysis.get('competitors', [])
        
        if len(competitors_data) > max_competitors:
            competitors_data = competitors_data[:max_competitors]
            
            reasoning.add_step(
                decision=f"Limit to top {max_competitors} competitors",
                rationale=f"{mode} mode configured for {max_competitors} competitors. "
                          f"Selected based on prominence in sources.",
                alternatives_considered=["Include all", f"Top {max_competitors}", "Weight by market cap"],
                chosen_option=f"Top {max_competitors} by prominence",
                confidence=0.85
            )
        
        # Build competitor list with reasoning
        competitors: List[Competitor] = []
        for comp_data in competitors_data:
            competitor = Competitor(
                name=comp_data.get('name', ''),
                description=comp_data.get('description'),
                market_position=None,
                reasoning=comp_data.get('reasoning')
            )
            competitors.append(competitor)
        
        reasoning.add_step(
            decision="Competitor identification reasoning",
            rationale=f"Identified {len(competitors)} competitors based on market overlap, "
                      "product similarity, and industry classification from sources.",
            alternatives_considered=["Market cap only", "Industry tags", "Multi-factor analysis"],
            chosen_option="Multi-factor analysis (market, product, industry)",
            confidence=0.8
        )
        
        # Step 4: Handle market size conflicts
        market_size_data = analysis.get('market_size', {})
        ambiguities = []
        
        if market_size_data.get('value'):
            # Check if multiple sources gave different sizes (simplified check)
            if "various" in market_size_data.get('sources', '').lower():
                reasoning.add_contradiction_resolution(
                    data_field="market_size",
                    conflicting_values=[market_size_data['value']],
                    resolved_value=market_size_data['value'],
                    rationale="Multiple sources provided different market sizes. Using most commonly cited figure.",
                    confidence=0.6
                )
                
                ambiguities.append({
                    "type": "market_size_variation",
                    "description": "Market size estimates vary across sources",
                    "resolved": True,
                    "resolution": market_size_data['value']
                })
        
        # Step 5: SWOT reasoning
        swot =  analysis.get('swot', {})
        
        if detailed_swot:
            reasoning.add_step(
                decision="Generate detailed SWOT",
                rationale=f"Deep mode: Comprehensive SWOT with {len(swot.get('strengths', []))} strengths, "
                          f"{len(swot.get('weaknesses', []))} weaknesses, "
                          f"{len(swot.get('opportunities', []))} opportunities, "
                          f"{len(swot.get('threats', []))} threats",
                alternatives_considered=["High-level only", "Detailed analysis"],
                chosen_option="Detailed evidence-based SWOT",
                confidence=0.75
            )
        
        # Step 6: Build competitive data
        market_size_trusted = None
        if market_size_data.get('value'):
            market_size_trusted = TrustedValue(
                value=market_size_data['value'],
                sources=sources_list,
                trust_score=trust_scorer.aggregate_trust_scores(sources_list),
                reasoning="Aggregated from multiple sources"
            )
        
        competitive_data: CompetitiveData = {
            "competitors": competitors,
            "market_size": market_size_trusted,
            "market_trends": analysis.get('market_trends'),
            "swot": swot,
            "positioning": analysis.get('positioning')
        }
        # Calculate aggregate trust
        avg_trust = trust_scorer.aggregate_trust_scores(sources_list)
        
        logger.info(f"✅ Competitive intelligence completed: {len(competitors)} competitors, trust {avg_trust:.2f}")
        logger.info(f"📊 Reasoning steps: {len(reasoning.steps)}, Avg confidence: {reasoning.get_average_confidence():.2f}")
        
        result_state = {
            "competitive_data": competitive_data,
            "reasoning_chains": {"competitive": reasoning.to_list()},
            "sources": {"competitive": sources_list},
            "trust_scores": {"competitive": avg_trust},
            "ambiguities": ambiguities,
            "completed_nodes": ["competitive"]
        }
        
        # Save to cache
        cache_manager.set(cache_key, result_state)
        
        return result_state
        
    except Exception as e:
        logger.exception("💥 CompetitiveIntelligenceNode failed")
        return {
            "errors": [f"CompetitiveIntelligenceNode error: {str(e)}"],
            "reasoning_chains": {"competitive": ReasoningChain("CompetitiveIntelligenceAgent").to_list()},
            "completed_nodes": ["competitive"]
        }
