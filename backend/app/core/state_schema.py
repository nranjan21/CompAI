"""
State schema for the company research workflow.

Defines the shared state structure that flows through all LangGraph nodes.
Every agent reads from and writes to this state, ensuring data consistency and traceability.
"""

from typing import TypedDict, Optional, List, Dict, Any, Literal, Annotated
import operator
from datetime import datetime


def merge_dicts(a: Dict[str, Any], b: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two dictionaries, giving priority to b for shared keys."""
    res = a.copy()
    res.update(b)
    return res


class Source(TypedDict):
    """Metadata for a single data source."""
    url: str
    title: Optional[str]
    source_type: Literal["official", "filing", "news", "social", "research", "other"]
    access_date: str  # ISO format
    page_numbers: Optional[str]  # e.g., "L45-L47" for citations
    trust_score: float  # 0.0 to 1.0


class TrustedValue(TypedDict):
    """A data value with source tracking and trust scoring."""
    value: Any
    sources: List[Source]
    trust_score: float  # Overall confidence in this value
    reasoning: Optional[str]  # Why this value was selected (esp. for contradictions)


class ReasoningStep(TypedDict):
    """A single reasoning step taken by an agent."""
    decision: str  # What decision was made
    rationale: str  # Why this decision was made
    alternatives_considered: List[str]  # What other options were considered
    chosen_option: str  # Which option was selected
    confidence: float  # 0.0 to 1.0 confidence in this decision
    timestamp: str  # ISO format


class CompanyProfile(TypedDict, total=False):
    """Structured company profile data."""
    company_name: TrustedValue
    ticker: Optional[TrustedValue]
    website: Optional[TrustedValue]
    industry: Optional[TrustedValue]
    sector: Optional[TrustedValue]
    founded: Optional[TrustedValue]
    headquarters: Optional[TrustedValue]
    employees: Optional[TrustedValue]
    description: Optional[TrustedValue]
    history: Optional[TrustedValue]  # New: Historical context
    products: Optional[List[str]]
    key_people: Optional[List[Dict[str, str]]]


class FinancialData(TypedDict, total=False):
    """Financial metrics and analysis."""
    fiscal_year: TrustedValue
    revenue: Optional[TrustedValue]
    net_income: Optional[TrustedValue]
    total_assets: Optional[TrustedValue]
    total_liabilities: Optional[TrustedValue]
    key_metrics: Optional[Dict[str, TrustedValue]]
    financial_health: Optional[TrustedValue]
    growth_rates: Optional[Dict[str, TrustedValue]]
    anomalies: Optional[List[Dict[str, Any]]]  # New: Detected anomalies
    risks: Optional[List[str]]
    pdf_path: Optional[str]
    historical_data: Optional[List[Dict[str, Any]]] # New: Historical financial data


class NewsArticle(TypedDict):
    """A single news article."""
    date: str
    title: str
    summary: str
    source: Source
    category: Optional[str]
    significance_score: Optional[float]


class NewsData(TypedDict, total=False):
    """News and media research results."""
    articles: List[NewsArticle]
    total_articles: int
    date_range: Dict[str, str]  # start_date, end_date
    categories: Dict[str, int]  # category -> count
    timeline: List[Dict[str, Any]]  # Major events chronologically
    sentiment_distribution: Optional[Dict[str, float]]


class SentimentData(TypedDict, total=False):
    """Public and social sentiment analysis."""
    overall_sentiment: TrustedValue  # e.g., "positive", "negative", "neutral"
    sentiment_score: Optional[float]  # -1.0 to 1.0
    sentiment_distribution: Dict[str, float]  # positive, negative, neutral percentages
    themes: List[Dict[str, Any]]  # Emerging themes
    representative_quotes: List[Dict[str, str]]  # With sources
    noise_filtered: int  # Number of items filtered as noise


class Competitor(TypedDict):
    """Information about a competitor."""
    name: str
    description: Optional[str]
    market_position: Optional[str]
    reasoning: Optional[str]  # Why identified as competitor


class CompetitiveData(TypedDict, total=False):
    """Market and competitive intelligence."""
    competitors: List[Competitor]
    market_size: Optional[TrustedValue]
    market_trends: Optional[List[str]]
    swot: Optional[Dict[str, List[str]]]  # strengths, weaknesses, opportunities, threats
    positioning: Optional[str]


class CompanyResearchState(TypedDict, total=False):
    """
    The complete state for company research workflow.
    
    This state is passed through all LangGraph nodes and accumulates
    data from each agent, along with reasoning chains and source tracking.
    """
    # Core metadata
    company_name: str
    ticker: Optional[str]
    mode: Literal["fast", "deep"]  # Research mode
    timestamp: str  # ISO format
    
    # Agent outputs
    company_profile: Optional[CompanyProfile]
    financial_data: Optional[FinancialData]
    news_data: Optional[NewsData]
    sentiment_data: Optional[SentimentData]
    competitive_data: Optional[CompetitiveData]
    
    # Synthesis result
    synthesis_result: Optional[str]  # Final Markdown report
    
    # Reasoning chains - maps agent name to list of reasoning steps
    reasoning_chains: Annotated[Dict[str, List[ReasoningStep]], merge_dicts]
    
    # Source tracking - maps data field to sources
    sources: Annotated[Dict[str, List[Source]], merge_dicts]
    
    # Trust scores - maps data field to overall trust score
    trust_scores: Annotated[Dict[str, float], merge_dicts]
    
    # Error tracking
    errors: Annotated[List[str], operator.add]
    warnings: Annotated[List[str], operator.add]
    ambiguities: Annotated[List[Dict[str, Any]], operator.add]
    
    # Progress tracking
    completed_nodes: Annotated[List[str], operator.add]
    current_node: Optional[str]
    
    # Metadata
    start_time: Optional[str]
    end_time: Optional[str]
    duration_seconds: Optional[float]


def create_initial_state(
    company_name: str,
    ticker: Optional[str] = None,
    mode: Literal["fast", "deep"] = "deep"
) -> CompanyResearchState:
    """
    Create an initial state for the research workflow.
    
    Args:
        company_name: Name of the company to research
        ticker: Optional stock ticker
        mode: Research mode (fast or deep)
        
    Returns:
        Initialized CompanyResearchState
    """
    return CompanyResearchState(
        company_name=company_name,
        ticker=ticker,
        mode=mode,
        timestamp=datetime.now().isoformat(),
        reasoning_chains={},
        sources={},
        trust_scores={},
        errors=[],
        warnings=[],
        ambiguities=[],
        completed_nodes=[],
        current_node=None,
        start_time=datetime.now().isoformat()
    )


def validate_state(state: CompanyResearchState) -> List[str]:
    """
    Validate the state structure.
    
    Args:
        state: State to validate
        
    Returns:
        List of validation errors (empty if valid)
    """
    errors = []
    
    # Check required fields
    if not state.get("company_name"):
        errors.append("company_name is required")
    
    if state.get("mode") not in ["fast", "deep", None]:
        errors.append("mode must be 'fast' or 'deep'")
    
    # Validate trust scores are in range
    for key, score in state.get("trust_scores", {}).items():
        if not (0.0 <= score <= 1.0):
            errors.append(f"trust_score for {key} must be between 0.0 and 1.0, got {score}")
    
    # Validate reasoning steps have required fields
    for agent_name, steps in state.get("reasoning_chains", {}).items():
        for i, step in enumerate(steps):
            if not step.get("decision"):
                errors.append(f"reasoning_chains[{agent_name}][{i}] missing 'decision'")
            if "confidence" in step and not (0.0 <= step["confidence"] <= 1.0):
                errors.append(f"reasoning_chains[{agent_name}][{i}] confidence must be 0.0-1.0")
    
    return errors
