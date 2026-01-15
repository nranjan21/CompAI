"""
Competitive Intelligence Agent - Analyzes competitive landscape and positioning.

Workflow:
1. Identify main competitors
2. Scrape competitor information
3. Compare features and positioning
4. Generate SWOT analysis
5. Provide strategic insights
"""

from typing import Dict, Any, List, Optional
from app.agents.base_agent import BaseAgent
from app.utils.web_scraper import get_web_scraper
from app.utils.logger import logger


class CompetitiveIntelligenceAgent(BaseAgent):
    """Agent for competitive intelligence and market analysis."""
    
    def __init__(self):
        """Initialize the competitive intelligence agent."""
        super().__init__(name="CompetitiveIntelligenceAgent", use_cache=True)
        self.web_scraper = get_web_scraper()
        self.total_steps = 5
    
    def _identify_competitors(self, company_name: str, industry: Optional[str] = None) -> List[str]:
        """Use LLM to identify main competitors."""
        self._log_step(f"Identifying competitors for {company_name}")
        
        industry_context = f" in the {industry} industry" if industry else ""
        
        prompt = f"""Identify the top 5 main competitors of {company_name}{industry_context}.

Consider:
- Direct competitors (similar products/services)
- Market leaders in the same space
- Well-known companies in the industry

Return a JSON array of competitor names:

[
  "Competitor 1",
  "Competitor 2",
  "Competitor 3",
  "Competitor 4",
  "Competitor 5"
]

Return ONLY valid JSON array, no additional text."""

        response = self._llm_generate(prompt, temperature=0.5, max_tokens=500)
        
        if response is None:
            return []
        
        # Parse JSON response
        try:
            import json
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            competitors = json.loads(response)
            logger.info(f"Identified {len(competitors)} competitors")
            return competitors
        except Exception as e:
            self._add_error(f"Failed to parse competitors: {e}")
            return []
    
    def _gather_competitor_info(self, competitors: List[str]) -> List[Dict[str, Any]]:
        """Gather basic information about competitors."""
        self._log_step("Gathering competitor information")
        
        competitor_data = []
        
        for competitor in competitors[:5]:  # Limit to 5 competitors
            # Search for competitor website
            search_results = self.web_scraper.search_google(
                f"{competitor} official website",
                num_results=3
            )
            
            if not search_results:
                continue
            
            website = search_results[0]['url']
            
            # Scrape competitor website
            soup = self.web_scraper.fetch_and_parse(website)
            if soup is None:
                continue
            
            # Extract basic info
            homepage_text = self.web_scraper.extract_text(soup)[:3000]
            metadata = self.web_scraper.extract_metadata(soup)
            
            competitor_data.append({
                'name': competitor,
                'website': website,
                'description': metadata.get('description', ''),
                'homepage_text': homepage_text
            })
        
        logger.info(f"Gathered data for {len(competitor_data)} competitors")
        return competitor_data
    
    def _analyze_competitive_landscape(self, company_name: str, competitor_data: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Use LLM to analyze competitive landscape."""
        self._log_step("Analyzing competitive landscape")
        
        # Build context
        context = f"Company: {company_name}\n\n"
        context += "Competitors:\n\n"
        
        for comp in competitor_data:
            context += f"--- {comp['name']} ---\n"
            context += f"Website: {comp['website']}\n"
            context += f"Description: {comp['description']}\n"
            context += f"About: {comp['homepage_text'][:1000]}\n\n"
        
        prompt = f"""{context}

Analyze the competitive landscape for {company_name} based on the competitor information above.

Return a JSON object with the following structure:

{{
  "competitors": [
    {{
      "name": "Competitor name",
      "market_position": "Market Leader|Strong Player|Challenger|Niche Player",
      "strengths": ["strength1", "strength2"],
      "weaknesses": ["weakness1", "weakness2"]
    }}
  ],
  "market_analysis": {{
    "market_position": "Description of {company_name}'s position",
    "competitive_advantages": ["advantage1", "advantage2", "advantage3"],
    "competitive_disadvantages": ["disadvantage1", "disadvantage2"],
    "key_differentiators": ["differentiator1", "differentiator2"]
  }}
}}

Important:
- Be specific with strengths/weaknesses (2-3 each)
- Focus on factual observations from the data
- Keep competitive advantages/disadvantages to top 3 each

Return ONLY valid JSON, no additional text."""

        response = self._llm_generate(prompt, temperature=0.5, max_tokens=2000)
        
        if response is None:
            return {}
        
        # Parse JSON response
        try:
            import json
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            analysis = json.loads(response)
            return analysis
        except Exception as e:
            self._add_error(f"Failed to parse competitive analysis: {e}")
            return {}
    
    def _generate_swot_analysis(self, company_name: str, competitive_analysis: Dict[str, Any]) -> Dict[str, List[str]]:
        """Generate SWOT analysis."""
        self._log_step("Generating SWOT analysis")
        
        import json
        context = json.dumps(competitive_analysis, indent=2)
        
        prompt = f"""Based on the competitive analysis below, generate a comprehensive SWOT analysis for {company_name}.

{context}

Return a JSON object with SWOT structure:

{{
  "strengths": ["Internal strength 1", "Internal strength 2", "Internal strength 3"],
  "weaknesses": ["Internal weakness 1", "Internal weakness 2", "Internal weakness 3"],
  "opportunities": ["External opportunity 1", "External opportunity 2", "External opportunity 3"],
  "threats": ["External threat 1", "External threat 2", "External threat 3"]
}}

Important:
- Strengths & Weaknesses are INTERNAL factors
- Opportunities & Threats are EXTERNAL factors
- Provide 3-4 items for each category
- Be specific and actionable

Return ONLY valid JSON, no additional text."""

        response = self._llm_generate(prompt, temperature=0.5, max_tokens=1500)
        
        if response is None:
            return {}
        
        # Parse JSON response
        try:
            import json
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0].strip()
            elif "```" in response:
                response = response.split("```")[1].split("```")[0].strip()
            
            swot = json.loads(response)
            return swot
        except Exception as e:
            self._add_error(f"Failed to parse SWOT analysis: {e}")
            return {}
    
    def execute(self, company_name: str, industry: Optional[str] = None) -> Dict[str, Any]:
        """
        Execute the competitive intelligence workflow.
        
        Args:
            company_name: Name of the company
            industry: Optional industry name for better competitor identification
            
        Returns:
            Dictionary with competitive intelligence data
        """
        # Generate cache key
        cache_key = self._generate_cache_key(company_name=company_name, industry=industry)
        
        def _execute():
            # Step 1: Identify competitors
            competitors = self._identify_competitors(company_name, industry)
            
            if not competitors:
                return {"error": "Could not identify competitors"}
            
            # Step 2: Gather competitor info
            competitor_data = self._gather_competitor_info(competitors)
            
            if not competitor_data:
                return {"error": "Could not gather competitor data"}
            
            # Step 3: Analyze competitive landscape
            competitive_analysis = self._analyze_competitive_landscape(company_name, competitor_data)
            
            # Step 4: Generate SWOT
            swot = self._generate_swot_analysis(company_name, competitive_analysis)
            
            # Combine results
            return {
                "competitors": competitive_analysis.get('competitors', []),
                "market_analysis": competitive_analysis.get('market_analysis', {}),
                "swot": swot
            }
        
        # Execute with caching (24 hour TTL)
        result = self._execute_with_cache(cache_key, _execute, ttl_hours=24)
        
        return result
