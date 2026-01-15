"""
Orchestrator Agent - Coordinates all research agents to conduct comprehensive company research.

Workflow:
1. Initialize all agents
2. Run CompanyProfileAgent to get basic info
3. Run Financial, News, and Competitive agents in parallel (simulated)
4. Run SentimentAnalysisAgent on news data
5. Aggregate all results
6. Track progress and handle errors
"""

from typing import Dict, Any, Optional
from datetime import datetime
from app.agents.base_agent import BaseAgent
from app.agents.company_profile_agent import CompanyProfileAgent
from app.agents.financial_research_agent import FinancialResearchAgent
from app.agents.news_intelligence_agent import NewsIntelligenceAgent
from app.agents.sentiment_analysis_agent import SentimentAnalysisAgent
from app.agents.competitive_intelligence_agent import CompetitiveIntelligenceAgent
from app.utils.logger import logger


class OrchestratorAgent(BaseAgent):
    """Main orchestrator that coordinates all research agents."""
    
    def __init__(self):
        """Initialize the orchestrator and all sub-agents."""
        super().__init__(name="OrchestratorAgent", use_cache=False)
        
        # Initialize all agents
        self.company_profile_agent = CompanyProfileAgent()
        self.financial_research_agent = FinancialResearchAgent()
        self.news_intelligence_agent = NewsIntelligenceAgent()
        self.sentiment_analysis_agent = SentimentAnalysisAgent()
        self.competitive_intelligence_agent = CompetitiveIntelligenceAgent()
        
        self.total_steps = 6
        
        logger.info("🎭 Orchestrator initialized with all agents")
    
    def _update_progress(self, current_agent: str, progress: int, callback=None):
        """Update progress (can be extended to report to external systems)."""
        logger.info(f"📊 Progress: {progress}% - Currently running: {current_agent}")
        if callback:
            callback(current_agent, progress)
    
    def conduct_research(self, company_name: str, ticker: Optional[str] = None, parallel: bool = True, progress_callback=None) -> Dict[str, Any]:
        """
        Legacy method for backward compatibility.
        Redirects to execute().
        """
        return self.execute(company_name=company_name, ticker=ticker, parallel=parallel, progress_callback=progress_callback)
    
    def execute(self, company_name: str, ticker: Optional[str] = None, parallel: bool = True, progress_callback=None) -> Dict[str, Any]:
        """
        Execute the complete research workflow.
        
        Args:
            company_name: Name of the company to research
            ticker: Optional stock ticker symbol
            parallel: Whether to run agents in parallel (True = faster)
            progress_callback: Optional callback function(agent_name, progress) for progress updates
            
        Returns:
            Dictionary with all research results
        """
        start_time = datetime.now()
        results = {
            "company_name": company_name,
            "ticker": ticker,
            "timestamp": start_time.isoformat(),
            "status": "running",
            "errors": []
        }
        
        try:
            # Step 1: Company Profile (0-20%) - Must run first to get industry/ticker
            self._log_step("Running Company Profile Agent")
            self._update_progress("CompanyProfileAgent", 10, progress_callback)
            
            profile_result = self.company_profile_agent.run(
                company_name=company_name,
                ticker=ticker
            )
            results["profile"] = profile_result
            
            # Extract industry for competitive analysis
            industry = profile_result.get("industry")
            
            # Update ticker if found in profile
            if not ticker and profile_result.get("ticker"):
                ticker = profile_result["ticker"]
                results["ticker"] = ticker
            
            self._update_progress("CompanyProfileAgent", 20, progress_callback)
            
            # Step 2-4: Run Financial, News, and Competitive agents
            if parallel:
                # Parallel execution using ThreadPoolExecutor
                self._log_step("Running Financial, News, and Competitive agents in parallel")
                self._update_progress("Parallel Agents", 25, progress_callback)
                
                from concurrent.futures import ThreadPoolExecutor, as_completed
                
                tasks = {
                    'financial': lambda: self.financial_research_agent.run(
                        company_name=company_name,
                        ticker=ticker
                    ),
                    'news': lambda: self.news_intelligence_agent.run(
                        company_name=company_name,
                        months_back=12
                    ),
                    'competitive': lambda: self.competitive_intelligence_agent.run(
                        company_name=company_name,
                        industry=industry
                    )
                }
                
                with ThreadPoolExecutor(max_workers=3) as executor:
                    future_to_name = {executor.submit(task): name for name, task in tasks.items()}
                    
                    for future in as_completed(future_to_name):
                        agent_name = future_to_name[future]
                        try:
                            result = future.result()
                            results[agent_name] = result
                            
                            # Update progress
                            if agent_name == 'financial':
                                self._update_progress("FinancialResearchAgent", 40, progress_callback)
                            elif agent_name == 'news':
                                self._update_progress("NewsIntelligenceAgent", 55, progress_callback)
                            elif agent_name == 'competitive':
                                self._update_progress("CompetitiveIntelligenceAgent", 70, progress_callback)
                        except Exception as e:
                            logger.error(f"Agent {agent_name} failed: {e}")
                            results[agent_name] = {"error": str(e)}
                
                self._update_progress("Parallel Agents", 75, progress_callback)
                
            else:
                # Sequential execution
                self._log_step("Running Financial Research Agent")
                self._update_progress("FinancialResearchAgent", 25, progress_callback)
                
                financial_result = self.financial_research_agent.run(
                    company_name=company_name,
                    ticker=ticker
                )
                results["financial"] = financial_result
                self._update_progress("FinancialResearchAgent", 40, progress_callback)
                
                self._log_step("Running News Intelligence Agent")
                self._update_progress("NewsIntelligenceAgent", 45, progress_callback)
                
                news_result = self.news_intelligence_agent.run(
                    company_name=company_name,
                    months_back=12
                )
                results["news"] = news_result
                self._update_progress("NewsIntelligenceAgent", 60, progress_callback)
                
                self._log_step("Running Competitive Intelligence Agent")
                self._update_progress("CompetitiveIntelligenceAgent", 65, progress_callback)
                
                competitive_result = self.competitive_intelligence_agent.run(
                    company_name=company_name,
                    industry=industry
                )
                results["competitive"] = competitive_result
                self._update_progress("CompetitiveIntelligenceAgent", 75, progress_callback)
            
            # Step 5: Sentiment Analysis (75-90%)
            self._log_step("Running Sentiment Analysis Agent")
            self._update_progress("SentimentAnalysisAgent", 80, progress_callback)
            
            # Prepare data sources for sentiment analysis
            sentiment_data_sources = {}
            
            # Use news articles if available
            news_result = results.get("news", {})
            if news_result.get("articles"):
                sentiment_data_sources["news"] = news_result["articles"]
            
            sentiment_result = self.sentiment_analysis_agent.run(
                data_sources=sentiment_data_sources
            )
            results["sentiment"] = sentiment_result
            self._update_progress("SentimentAnalysisAgent", 90, progress_callback)
            
            # Step 6: Finalize (95-100%)
            self._log_step("Finalizing research")
            
            # Collect all errors from agents
            all_errors = []
            for key in ["profile", "financial", "news", "sentiment", "competitive"]:
                if key in results and "_metadata" in results[key]:
                    agent_errors = results[key]["_metadata"].get("errors", [])
                    all_errors.extend(agent_errors)
            
            results["errors"] = all_errors
            results["status"] = "completed"
            results["completion_time"] = datetime.now().isoformat()
            results["duration_seconds"] = (datetime.now() - start_time).total_seconds()
            
            self._update_progress("Complete", 100, progress_callback)
            
            logger.info(f"✅ Research completed for {company_name} in {results['duration_seconds']:.2f} seconds")
            
            return results
            
        except Exception as e:
            logger.exception(f"💥 Orchestrator failed")
            results["status"] = "failed"
            results["errors"].append(f"Orchestrator error: {str(e)}")
            results["completion_time"] = datetime.now().isoformat()
            return results
