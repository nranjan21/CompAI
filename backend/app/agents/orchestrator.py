"""
LangGraph Orchestrator - State-based Multi-Agent Research Workflow

Coordinates all research agents using LangGraph's StateGraph for explicit
workflow management, parallel execution, and state-based communication.

This replaces the old class-based OrchestratorAgent with a functional LangGraph approach.
"""

from typing import Literal
from langgraph.graph import StateGraph, END
from app.core.state_schema import CompanyResearchState, create_initial_state
from app.agents.company_profile_agent import company_profile_node
from app.agents.financial_research_agent import financial_research_node
from app.agents.news_intelligence_agent import news_intelligence_node
from app.agents.sentiment_analysis_agent import sentiment_analysis_node
from app.agents.competitive_intelligence_agent import competitive_intelligence_node
from app.synthesis.insight_synthesizer import synthesis_node
from app.utils.logger import logger


def should_continue_to_synthesis(state: CompanyResearchState) -> str:
    """
    Conditional edge function to determine if we should proceed to synthesis.
    
    Waits for all parallel agents to complete before synthesis.
    
    Args:
        state: Current research state
        
    Returns:
        "synthesis" if ready, "wait" otherwise
    """
    completed = state.get("completed_nodes", [])
    
    # Required nodes for synthesis
    required_nodes = {"company_profile", "financial", "news", "competitive"}
    completed_set = set(completed)
    
    # Sentiment is optional (runs after news)
    if "sentiment" in completed_set:
        # If sentiment is done, check if all others are too
        if required_nodes.issubset(completed_set):
            return "synthesis"
    
    # Check if all required nodes are done (sentiment may still be running)
    if required_nodes.issubset(completed_set):
        #  If news is done but sentiment isn't, wait for sentiment
        if "news" in completed_set and "sentiment" not in completed_set:
            return "wait"
        # Otherwise proceed
        return "synthesis"
    
    return "wait"


def create_research_workflow(mode: Literal["fast", "deep"] = "fast") -> StateGraph:
    """
    Create the LangGraph research workflow.
    
    Workflow structure:
    1. START → CompanyProfile
    2. CompanyProfile → [Financial, News, Competitive] (parallel)
    3. News → Sentiment
    4. All agents → Synthesis (conditional, waits for all to complete)
    5. Synthesis → END
    
    Args:
        mode: Research mode ("fast" or "deep")
        
    Returns:
        Compiled StateGraph workflow
    """
    logger.info(f"🏗️ Creating research workflow in {mode} mode")
    
    # Create state graph
    workflow = StateGraph(CompanyResearchState)
    
    # Add nodes
    workflow.add_node("company_profile", company_profile_node)
    workflow.add_node("financial", financial_research_node)
    workflow.add_node("news", news_intelligence_node)
    workflow.add_node("sentiment", sentiment_analysis_node)
    workflow.add_node("competitive", competitive_intelligence_node)
    workflow.add_node("synthesis", synthesis_node)
    
    # Set entry point
    workflow.set_entry_point("company_profile")
    
    # Company profile must complete first, then fan out to parallel agents
    workflow.add_edge("company_profile", "financial")
    workflow.add_edge("company_profile", "news")
    workflow.add_edge("company_profile", "competitive")
    
    # News feeds into sentiment (sentiment needs news data)
    workflow.add_edge("news", "sentiment")
    
    # All agents converge to synthesis (but only when all are done)
    # We use conditional edges that check if all nodes are complete
    workflow.add_conditional_edges(
        "financial",
        should_continue_to_synthesis,
        {
            "synthesis": "synthesis",
            "wait": END  # Temporary end, synthesis will be triggered by last completing node
        }
    )
    
    workflow.add_conditional_edges(
        "sentiment",
        should_continue_to_synthesis,
        {
            "synthesis": "synthesis",
            "wait": END
        }
    )
    
    workflow.add_conditional_edges(
        "competitive",
        should_continue_to_synthesis,
        {
            "synthesis": "synthesis",
            "wait": END
        }
    )
    
    # Synthesis is the final step
    workflow.add_edge("synthesis", END)
    
    return workflow


def execute_research(
    company_name: str,
    ticker: str = None,
    mode: Literal["fast", "deep"] = "fast"
) -> CompanyResearchState:
    """
    Execute the complete research workflow for a company.
    
    Args:
        company_name: Name of the company to research
        ticker: Optional stock ticker symbol
        mode: Research mode ("fast" or "deep")
        
    Returns:
        Final CompanyResearchState with all results
    """
    logger.info(f"🚀 Starting research for {company_name} in {mode} mode")
    
    # Create initial state
    initial_state = create_initial_state(company_name, ticker, mode)
    
    # Create and compile workflow
    workflow = create_research_workflow(mode)
    app = workflow.compile()
    
    # Execute workflow
    try:
        # LangGraph will execute the workflow
        # It handles parallel execution and state updates automatically
        final_state = app.invoke(initial_state)
        
        # Add completion metadata
        from datetime import datetime
        final_state["end_time"] = datetime.now().isoformat()
        
        if final_state.get("start_time"):
            start = datetime.fromisoformat(final_state["start_time"])
            end = datetime.fromisoformat(final_state["end_time"])
            final_state["duration_seconds"] = (end - start).total_seconds()
        
        logger.info(f"✅ Research completed for {company_name}")
        logger.info(f"⏱️ Duration: {final_state.get('duration_seconds', 0):.2f} seconds")
        logger.info(f"📊 Completed nodes: {final_state.get('completed_nodes', [])}")
        logger.info(f"❌ Errors: {len(final_state.get('errors', []))}")
        logger.info(f"⚠️ Warnings: {len(final_state.get('warnings', []))}")
        
        return final_state
        
    except Exception as e:
        logger.exception(f"💥 Research workflow failed for {company_name}")
        initial_state.setdefault("errors", []).append(f"Workflow error: {str(e)}")
        return initial_state


# For backward compatibility with old API
class OrchestratorAgent:
    """
    Thin wrapper class for backward compatibility.
    
    Internally uses LangGraph workflow but exposes old interface.
    """
    
    def __init__(self):
        logger.info("🤖 Initialized OrchestratorAgent (LangGraph-based)")
    
    def execute(
        self,
        company_name: str,
        ticker: str = None,
        parallel: bool = True,  # Ignored, always uses LangGraph
        progress_callback=None  # Not yet implemented
    ) -> dict:
        """
        Execute research using LangGraph workflow.
        
        Args:
            company_name: Name of the company
            ticker: Optional ticker symbol
            parallel: Ignored (LangGraph handles parallelism)
            progress_callback: Not yet implemented
            
        Returns:
            Dictionary with research results (converted from state)
        """
        # Determine mode (default to fast for now)
        # TODO: Add mode parameter
        mode = "fast"
        
        # Execute workflow  
        final_state = execute_research(company_name, ticker, mode)
        
        # Convert state to old format for compatibility
        return {
            "company_name": company_name,
            "ticker": ticker,
            "timestamp": final_state.get("timestamp"),
            "profile": final_state.get("company_profile"),
            "financial": final_state.get("financial_data"),
            "news": final_state.get("news_data"),
            "sentiment": final_state.get("sentiment_data"),
            "competitive": final_state.get("competitive_data"),
            "synthesis": final_state.get("synthesis_result"),
            "reasoning_chains": final_state.get("reasoning_chains", {}),
            "trust_scores": final_state.get("trust_scores", {}),
            "sources": final_state.get("sources", {}),
            "completed_nodes": final_state.get("completed_nodes", []),
            "errors": final_state.get("errors", []),
            "warnings": final_state.get("warnings", []),
            "ambiguities": final_state.get("ambiguities", []),
            "duration_seconds": final_state.get("duration_seconds"),
            "status": "completed" if not final_state.get("errors") else "completed_with_errors"
        }
    
    def conduct_research(self, *args, **kwargs):
        """Alias for execute() for backward compatibility."""
        return self.execute(*args, **kwargs)
    
    def run(self, *args, **kwargs):
        """Alias for execute() for backward compatibility."""
        return self.execute(*args, **kwargs)
