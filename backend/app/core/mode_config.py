"""
Configuration for fast vs deep research modes.

Defines parameters that control the depth and breadth of research
for each agent based on the selected mode.
"""

from typing import TypedDict, Literal


class ModeConfig(TypedDict, total=False):
    """Configuration parameters for a research mode."""
    # Company Profile
    company_profile_max_sources: int
    company_profile_search_results: int
    company_profile_multi_language: bool
    
    # Financial Research
    financial_years_back: int
    financial_detailed_analysis: bool
    financial_max_sections: int
    
    # News Intelligence
    news_months_back: int
    news_max_articles: int
    news_detailed_events: bool
    
    # Sentiment Analysis
    sentiment_sample_size: int
    sentiment_detailed_analysis: bool
    
    # Competitive Intelligence
    competitive_max_competitors: int
    competitive_niche_markets: bool
    competitive_detailed_swot: bool
    
    # Synthesis
    synthesis_multi_pass: bool
    synthesis_fact_check: bool
    synthesis_max_iterations: int


# Fast mode configuration (~2-5 minutes)
FAST_MODE_CONFIG: ModeConfig = {
    # Company Profile: Quick lookup
    "company_profile_max_sources": 2,
    "company_profile_search_results": 5,
    "company_profile_multi_language": False,
    
    # Financial: Latest year only
    "financial_years_back": 1,
    "financial_detailed_analysis": False,
    "financial_max_sections": 3,
    
    # News: Recent headlines
    "news_months_back": 6,
    "news_max_articles": 20,
    "news_detailed_events": False,
    
    # Sentiment: Small sample
    "sentiment_sample_size": 50,
    "sentiment_detailed_analysis": False,
    
    # Competitive: Top competitors only
    "competitive_max_competitors": 5,
    "competitive_niche_markets": False,
    "competitive_detailed_swot": False,
    
    # Synthesis: Single pass
    "synthesis_multi_pass": False,
    "synthesis_fact_check": False,
    "synthesis_max_iterations": 1
}


# Deep mode configuration (~30-45 minutes)
DEEP_MODE_CONFIG: ModeConfig = {
    # Company Profile: Comprehensive research
    "company_profile_max_sources": 10,
    "company_profile_search_results": 20,
    "company_profile_multi_language": True,
    
    # Financial: Multi-year analysis
    "financial_years_back": 5,
    "financial_detailed_analysis": True,
    "financial_max_sections": 10,
    
    # News: Extended history
    "news_months_back": 36,
    "news_max_articles": 100,
    "news_detailed_events": True,
    
    # Sentiment: Large sample with analysis
    "sentiment_sample_size": 500,
    "sentiment_detailed_analysis": True,
    
    # Competitive: Exhaustive analysis
    "competitive_max_competitors": 15,
    "competitive_niche_markets": True,
    "competitive_detailed_swot": True,
    
    # Synthesis: Multi-pass with fact checking
    "synthesis_multi_pass": True,
    "synthesis_fact_check": True,
    "synthesis_max_iterations": 3
}


def get_mode_config(mode: Literal["fast", "deep"]) -> ModeConfig:
    """
    Get configuration for the specified research mode.
    
    Args:
        mode: Research mode ("fast" or "deep")
        
    Returns:
        ModeConfig dictionary
        
    Raises:
        ValueError: If mode is invalid
    """
    if mode == "fast":
        return FAST_MODE_CONFIG
    elif mode == "deep":
        return DEEP_MODE_CONFIG
    else:
        raise ValueError(f"Invalid mode: {mode}. Must be 'fast' or 'deep'")


def get_config_value(
    mode: Literal["fast", "deep"],
    key: str,
    default: any = None
) -> any:
    """
    Get a specific configuration value for a mode.
    
    Args:
        mode: Research mode
        key: Configuration key
        default: Default value if key not found
        
    Returns:
        Configuration value
    """
    config = get_mode_config(mode)
    return config.get(key, default)
