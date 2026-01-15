"""
Configuration management for the Deep Research Agent.
Handles environment variables, API keys, and system settings.
"""

import os
from pathlib import Path
from typing import List, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

# Load environment variables
load_dotenv()

class LLMConfig(BaseModel):
    """Configuration for LLM providers with fallback chain."""
    
    providers: List[str] = [
        "groq",
        "huggingface",
        "cohere",
        "gemini",
        "together"
    ]
    
    # API Keys
    google_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("GOOGLE_API_KEY"))
    groq_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("GROQ_API_KEY"))
    huggingface_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("HUGGINGFACE_API_KEY"))
    together_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("TOGETHER_API_KEY"))
    cohere_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("COHERE_API_KEY"))
    
    # Model selections
    huggingface_model: str = Field(default_factory=lambda: os.getenv("HF_MODEL", "mistralai/Mixtral-8x7B-Instruct-v0.1"))
    together_model: str = Field(default_factory=lambda: os.getenv("TOGETHER_MODEL", "meta-llama/Llama-3.3-70B-Instruct-Turbo"))
    
    # Retry settings
    max_retries_per_provider: int = 2
    fallback_enabled: bool = True
    timeout_seconds: int = 30


class DataSourceConfig(BaseModel):
    """Configuration for data sources."""
    
    # Reddit API
    reddit_client_id: Optional[str] = Field(default_factory=lambda: os.getenv("REDDIT_CLIENT_ID"))
    reddit_client_secret: Optional[str] = Field(default_factory=lambda: os.getenv("REDDIT_CLIENT_SECRET"))
    reddit_user_agent: str = Field(default_factory=lambda: os.getenv("REDDIT_USER_AGENT", "CompanyResearchAgent/1.0"))
    
    # Scraping & Search
    scrapingbee_api_key: Optional[str] = Field(default_factory=lambda: os.getenv("SCRAPINGBEE_API_KEY"))
    serpapi_key: Optional[str] = Field(default_factory=lambda: os.getenv("SERPAPI_KEY"))
    
    # SEC EDGAR
    sec_edgar_user_agent: str = "Company Research Agent research@example.com"


class ResearchConfig(BaseModel):
    """Configuration for research parameters."""
    
    time_horizon_months: int = Field(default_factory=lambda: int(os.getenv("RESEARCH_TIME_HORIZON_MONTHS", "12")))
    max_news_articles: int = Field(default_factory=lambda: int(os.getenv("MAX_NEWS_ARTICLES", "50")))
    max_social_posts: int = Field(default_factory=lambda: int(os.getenv("MAX_SOCIAL_POSTS", "100")))
    
    # Source priorities
    source_trust_levels: dict = {
        "primary": ["sec.gov", "investor.relations", "official_website"],
        "secondary": ["reuters.com", "bloomberg.com", "wsj.com", "wikipedia.org", "crunchbase.com"],
        "tertiary": ["reddit.com", "news.ycombinator.com", "glassdoor.com", "trustpilot.com"]
    }


class AgentConfig(BaseModel):
    """Configuration for agent behavior and retry logic."""
    
    max_retries: int = Field(default_factory=lambda: int(os.getenv("AGENT_MAX_RETRIES", "3")))
    retry_delay_seconds: float = Field(default_factory=lambda: float(os.getenv("AGENT_RETRY_DELAY", "1.0")))
    retry_backoff_multiplier: float = Field(default_factory=lambda: float(os.getenv("AGENT_RETRY_BACKOFF", "2.0")))
    timeout_seconds: int = Field(default_factory=lambda: int(os.getenv("AGENT_TIMEOUT", "60")))


class SystemConfig(BaseModel):
    """System-level configuration."""
    
    log_level: str = Field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    enable_caching: bool = Field(default_factory=lambda: os.getenv("ENABLE_CACHING", "true").lower() == "true")
    cache_dir: Path = Field(default_factory=lambda: Path(os.getenv("CACHE_DIR", "./cache")))
    output_dir: Path = Field(default_factory=lambda: Path(os.getenv("OUTPUT_DIR", "./reports")))
    
    def __init__(self, **data):
        super().__init__(**data)
        # Create directories if they don't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)


class Config:
    """Main configuration class combining all configs."""
    
    def __init__(self):
        self.llm = LLMConfig()
        self.data_sources = DataSourceConfig()
        self.research = ResearchConfig()
        self.agent = AgentConfig()
        self.system = SystemConfig()
    
    def get_available_llm_providers(self) -> List[str]:
        """Returns list of LLM providers with valid API keys."""
        available = []
        
        if self.llm.google_api_key:
            available.append("gemini")
        if self.llm.groq_api_key:
            available.append("groq")
        if self.llm.huggingface_api_key:
            available.append("huggingface")
        if self.llm.together_api_key:
            available.append("together")
        if self.llm.cohere_api_key:
            available.append("cohere")
        
        return available


# Global config instance
config = Config()
