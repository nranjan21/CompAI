"""
Company Profile Agent - LangGraph Node Implementation

Gathers basic company information from multiple sources with explicit reasoning,
disambiguation, and trust scoring.

This is a node function for LangGraph that reads and updates CompanyResearchState.
"""

from typing import Optional, List, Dict, Any
from app.core.state_schema import CompanyResearchState, TrustedValue, Source
from app.core.reasoning_chain import ReasoningChain
from app.core.trust_scorer import get_trust_scorer
from app.core.mode_config import get_config_value
from app.core.llm_manager import get_llm_manager
from app.utils.web_scraper import get_web_scraper
from app.utils.logger import logger
from app.utils.cache_manager import get_cache_manager
from datetime import datetime


def company_profile_node(state: CompanyResearchState) -> CompanyResearchState:
    """
    Company Profile LangGraph node.
    
    Workflow:
    1. Search for company website (with reasoning for source selection)
    2. Scrape company website and Wikipedia
    3. Disambiguate if multiple entities found
    4. Use LLM to synthesize structured profile
    5. Score trust and confidence for all extracted data
    
    Args:
        state: Current research state
        
    Returns:
        Updated state with company_profile populated
    """
    logger.info("🚀 Starting CompanyProfileNode")
    
    # Initialize reasoning chain
    reasoning = ReasoningChain("CompanyProfileAgent")
    
    # Get mode configuration
    mode = state.get("mode", "fast")
    max_sources = get_config_value(mode, "company_profile_max_sources", 2)
    search_results = get_config_value(mode, "company_profile_search_results", 5)
    multi_language = get_config_value(mode, "company_profile_multi_language", False)
    
    # Initialize components
    web_scraper = get_web_scraper()
    llm_manager = get_llm_manager()
    trust_scorer = get_trust_scorer()
    cache_manager = get_cache_manager()
    
    company_name = state["company_name"]
    ticker = state.get("ticker")
    
    # Step 0: Check cache
    cache_key = f"company_profile_{company_name.lower().replace(' ', '_')}_{mode}"
    cached_result = cache_manager.get(cache_key, ttl_hours=24)
    if cached_result:
        logger.info(f"✅ Cache hit for {company_name} profile")
        # Ensure we update completing node status while returning cached data
        cached_result["completed_nodes"] = ["company_profile"]
        return cached_result
    
    try:
        # Step 1: Find company website
        logger.info(f"🔍 Searching for {company_name} website")
        
        search_query = f"{company_name} official website"
        if ticker:
            search_query += f" {ticker}"
        
        search_results_list = web_scraper.search_google(search_query, num_results=search_results)
        
        if not search_results_list:
            return {
                "errors": ["Could not find company website"],
                "completed_nodes": ["company_profile"]
            }
        
        # Reasoning: Source selection for website
        website_candidates = [r['url'] for r in search_results_list]
        website = website_candidates[0]  # First result typically official
        
        reasoning.add_source_selection(
            data_type="company website",
            sources_considered=website_candidates[:3],
            chosen_source=website,
            rationale=f"Selected first search result as it typically represents the official website. "
                      f"Query '{search_query}' returned {len(website_candidates)} results.",
            confidence=0.9
        )
        
        logger.info(f"✅ Selected website: {website}")
        
        # Step 2: Scrape company website
        logger.info("📄 Scraping company website")
        
        soup = web_scraper.fetch_and_parse(website)
        website_data = {}
        
        if soup:
            website_data["url"] = website
            website_data["homepage_text"] = web_scraper.extract_text(soup)[:5000]
            
            # Try to find About page
            links = web_scraper.extract_links(soup, website, filter_domain=True)
            about_links = [link for link in links if 'about' in link.lower()]
            
            if about_links:
                about_soup = web_scraper.fetch_and_parse(about_links[0])
                if about_soup:
                    website_data["about_text"] = web_scraper.extract_text(about_soup)[:5000]
                    
                    reasoning.add_step(
                        decision="Include About page content",
                        rationale=f"Found {len(about_links)} About page(s), selected first one for additional context",
                        alternatives_considered=["Only use homepage", "Scrape all About pages"],
                        chosen_option="Scrape first About page",
                        confidence=0.85
                    )
        
        # Step 3: Scrape Wikipedia
        logger.info("📚 Searching for Wikipedia page")
        
        wiki_search = web_scraper.search_google(f"{company_name} Wikipedia", num_results=3)
        wiki_text = None
        wiki_url = None
        
        for result in wiki_search:
            if 'wikipedia.org' in result['url']:
                wiki_url = result['url']
                break
        
        if wiki_url:
            wiki_soup = web_scraper.fetch_and_parse(wiki_url)
            if wiki_soup:
                content = wiki_soup.select_one('#mw-content-text')
                if content:
                    wiki_text = web_scraper.extract_text(content)[:10000]
                    
                    # New: Specifically extract History section for richer profile
                    wiki_history = web_scraper.extract_wikipedia_history(wiki_url)
                    
                    reasoning.add_source_selection(
                        data_type="Wikipedia content",
                        sources_considered=[wiki_url],
                        chosen_source=wiki_url,
                        rationale="Wikipedia provides encyclopedic overview with factual information",
                        confidence=0.75
                    )
                    
                    if wiki_history:
                        reasoning.add_step(
                            decision="Extracted Wikipedia history",
                            rationale="Found and extracted specialized History section for company background",
                            alternatives_considered=["Use full text only"],
                            chosen_option="Extract and use History section",
                            confidence=0.9
                        )
        else:
            logger.info("ℹ️ No Wikipedia page found")
            reasoning.add_step(
                decision="Skip Wikipedia",
                rationale="No Wikipedia page found in search results",
                alternatives_considered=["Search harder", "Continue without"],
                chosen_option="Continue without Wikipedia",
                confidence=1.0
            )
        
        # Step 4: Check for disambiguation
        # If we have conflicting information, we need to disambiguate
        disambiguation_needed = False
        
        # Simple heuristic: if website domain doesn't contain company name, might be ambiguous
        if website:
            from urllib.parse import urlparse
            domain = urlparse(website).netloc.lower()
            company_name_lower = company_name.lower().replace(' ', '').replace('.', '').replace(',', '')
            
            # Check if company name (or parts) in domain
            name_parts = company_name.split()
            domain_match = any(part.lower() in domain for part in name_parts if len(part) > 3)
            
            if not domain_match and not ticker:
                disambiguation_needed = True
                
                reasoning.add_step(
                    decision="Flag potential ambiguity",
                    rationale=f"Website domain '{domain}' doesn't clearly match company name '{company_name}'. "
                              f"No ticker provided for verification.",
                    alternatives_considered=["Accept anyway", "Search for more specific results", "Flag as ambiguous"],
                    chosen_option="Flag as ambiguous but continue",
                    confidence=0.6
                )
                
                state.setdefault("ambiguities", []).append({
                    "type": "company_identification",
                    "description": f"Domain '{domain}' may not match company '{company_name}'",
                    "resolved": False,
                    "needs_review": True
                })
                # We'll return ambiguities at the end if needed, 
                # but better to collect them in a local list first.
        
        ambiguities = []
        if website and not domain_match and not ticker:
            ambiguities.append({
                "type": "company_identification",
                "description": f"Domain '{domain}' may not match company '{company_name}'",
                "resolved": False,
                "needs_review": True
            })
        
        # Step 5: Synthesize profile with LLM
        logger.info("🤖 Synthesizing company profile with LLM")
        
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
            
        if 'wiki_history' in locals() and wiki_history:
            context += f"Company History (from Wikipedia):\n{wiki_history}\n\n"
        
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
  "history": "Concise summary of company history, founding, and major milestones (2-4 paragraphs)",
  "products": ["List", "of", "main", "products or services"],
  "key_people": [{{"name": "Person Name", "role": "CEO/Founder/etc"}}]
}}

Important:
- Extract only factual information present in the source material
- Use null for missing information
- Keep the description concise and factual
- Only include top 3-5 products/services
- Only include top 3-5 key people
- If you find conflicting information (e.g., different founding years), choose the most authoritative source

Return ONLY valid JSON, no additional text."""

        result = llm_manager.generate(prompt, temperature=0.3, max_tokens=1500)
        
        if not result.get("success"):
            return {
                "errors": [f"LLM synthesis failed: {result.get('error')}"],
                "completed_nodes": ["company_profile"]
            }
        
        response = result.get("text", "")
        
        # Parse JSON response
        try:
            import json
            # Extract JSON from response (handle potential markdown code blocks)
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            profile_data = json.loads(response)
            
            reasoning.add_step(
                decision="LLM synthesis successful",
                rationale=f"Extracted structured profile from {len(context)} characters of source text",
                alternatives_considered=["Rule-based extraction", "LLM synthesis"],
                chosen_option="LLM synthesis",
                confidence=0.85
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}\nResponse: {response[:500]}")
            return {
                "errors": [f"Failed to parse LLM JSON response: {e}"],
                "completed_nodes": ["company_profile"]
            }
        
        # Step 6: Build TrustedValue structures with sources
        sources_list: List[Source] = []
        
        if website:
            sources_list.append(Source(
                url=website,
                title=f"{company_name} Official Website",
                source_type="official",
                access_date=datetime.now().isoformat(),
                page_numbers=None,
                trust_score=trust_scorer.score_source(website, "official")
            ))
        
        if wiki_url:
            sources_list.append(Source(
                url=wiki_url,
                title=f"{company_name} Wikipedia",
                source_type="research",
                access_date=datetime.now().isoformat(),
                page_numbers=None,
                trust_score=trust_scorer.score_source(wiki_url, "research")
            ))
        
        # Calculate aggregate trust score
        aggregate_trust = trust_scorer.aggregate_trust_scores(sources_list)
        
        reasoning.add_step(
            decision="Calculate trust scores",
            rationale=f"Aggregate trust score {aggregate_trust:.2f} from {len(sources_list)} sources",
            alternatives_considered=["Use simple average", "Weight by source type"],
            chosen_option="Weighted aggregation",
            confidence=0.9
        )
        
        # Build company profile with trusted values
        company_profile = {}
        
        for key, value in profile_data.items():
            if value is not None:
                company_profile[key] = TrustedValue(
                    value=value,
                    sources=sources_list,
                    trust_score=aggregate_trust,
                    reasoning=None
                )
        
        # Ensure ticker is included if provided
        if ticker and not profile_data.get("ticker"):
            company_profile["ticker"] = TrustedValue(
                value=ticker,
                sources=[Source(
                    url="user_provided",
                    title="User Input",
                    source_type="official", 
                    access_date=datetime.now().isoformat(),
                    page_numbers=None,
                    trust_score=1.0
                )],
                trust_score=1.0,
                reasoning="Ticker provided by user"
            )
        
        logger.info(f"✅ Company profile completed with trust score {aggregate_trust:.2f}")
        logger.info(f"📊 Reasoning steps: {len(reasoning.steps)}, Avg confidence: {reasoning.get_average_confidence():.2f}")
        
        result_state = {
            "company_profile": company_profile,
            "reasoning_chains": {"company_profile": reasoning.to_list()},
            "sources": {"company_profile": sources_list},
            "trust_scores": {"company_profile": aggregate_trust},
            "ambiguities": ambiguities,
            "completed_nodes": ["company_profile"]
        }
        
        # Save to cache
        cache_manager.set(cache_key, result_state)
        
        return result_state
        
    except Exception as e:
        logger.exception("💥 CompanyProfileNode failed")
        return {
            "errors": [f"CompanyProfileNode error: {str(e)}"],
            "completed_nodes": ["company_profile"]
        }
