"""
Trust scoring system for source evaluation and contradiction resolution.

Implements a hierarchical trust model where sources are scored based on
their reliability, and conflicts are resolved using weighted voting.
"""

from typing import List, Dict, Any, Optional, Literal, Tuple
from urllib.parse import urlparse
import re


class TrustScorer:
    """
    Evaluates trust scores for data sources and resolves contradictions.
    
    Trust hierarchy:
    - 0.9-1.0: Official filings (SEC, SEDAR, Companies House), audited reports
    - 0.7-0.9: Major news outlets (Reuters, Bloomberg, FT, WSJ)
    - 0.5-0.7: General news, industry publications
    - 0.3-0.5: Blogs, unverified sources, social aggregates
    - 0.0-0.3: Individual social posts, rumors
    """
    
    # Source type trust scores
    SOURCE_TYPE_SCORES = {
        "filing": 1.0,  # Official regulatory filings
        "official": 0.95,  # Official company documents
        "research": 0.85,  # Research/analyst reports
        "news_tier1": 0.85,  # Top-tier news outlets
        "news_tier2": 0.65,  # General news outlets
        "blog": 0.4,  # Blogs and opinion pieces
        "social": 0.2,  # Social media
        "unknown": 0.5  # Default for unknown sources
    }
    
    # Domain-based trust mapping
    TRUSTED_DOMAINS = {
        # Regulatory/Official
        "sec.gov": ("filing", 1.0),
        "sedar.com": ("filing", 1.0),
        "companieshouse.gov.uk": ("filing", 1.0),
        "annualreports.com": ("official", 0.95),
        
        # Top-tier news
        "reuters.com": ("news_tier1", 0.90),
        "bloomberg.com": ("news_tier1", 0.90),
        "ft.com": ("news_tier1", 0.88),
        "wsj.com": ("news_tier1", 0.88),
        "economist.com": ("news_tier1", 0.85),
        "apnews.com": ("news_tier1", 0.85),
        "bbc.com": ("news_tier1", 0.83),
        
        # Second-tier news
        "cnbc.com": ("news_tier2", 0.75),
        "cnn.com": ("news_tier2", 0.70),
        "forbes.com": ("news_tier2", 0.70),
        "businessinsider.com": ("news_tier2", 0.65),
        "techcrunch.com": ("news_tier2", 0.68),
        "theverge.com": ("news_tier2", 0.65),
        
        # Reference
        "wikipedia.org": ("research", 0.75),
        "crunchbase.com": ("research", 0.75),
        "linkedin.com": ("official", 0.70),
        
        # Financial data
        "finance.yahoo.com": ("research", 0.75),
        "finance.google.com": ("research", 0.75),
        "marketwatch.com": ("news_tier2", 0.70),
        
        # Social (low trust)
        "twitter.com": ("social", 0.25),
        "x.com": ("social", 0.25),
        "reddit.com": ("social", 0.30),
        "facebook.com": ("social", 0.20),
    }
    
    def score_source(
        self,
        url: str,
        source_type: Optional[Literal["official", "filing", "news", "social", "research", "other"]] = None
    ) -> float:
        """
        Score a source URL based on trust hierarchy.
        
        Args:
            url: Source URL
            source_type: Optional explicit source type
            
        Returns:
            Trust score from 0.0 to 1.0
        """
        # Parse domain
        try:
            domain = urlparse(url).netloc.lower()
            # Remove www. prefix
            domain = re.sub(r'^www\.', '', domain)
        except:
            return self.SOURCE_TYPE_SCORES["unknown"]
        
        # Check known domains
        for trusted_domain, (dtype, score) in self.TRUSTED_DOMAINS.items():
            if trusted_domain in domain:
                return score
        
        # If source type provided, use that
        if source_type:
            if source_type == "filing":
                return self.SOURCE_TYPE_SCORES["filing"]
            elif source_type == "official":
                return self.SOURCE_TYPE_SCORES["official"]
            elif source_type == "news":
                return self.SOURCE_TYPE_SCORES["news_tier2"]
            elif source_type == "research":
                return self.SOURCE_TYPE_SCORES["research"]
            elif source_type == "social":
                return self.SOURCE_TYPE_SCORES["social"]
        
        # Default for unknown sources
        return self.SOURCE_TYPE_SCORES["unknown"]
    
    def resolve_contradiction(
        self,
        sources: List[Dict[str, Any]],
        values: List[Any]
    ) -> Tuple[Any, float, str]:
        """
        Resolve contradicting values using weighted voting by trust score.
        
        Args:
            sources: List of source dicts with 'url' and optional 'trust_score'
            values: Corresponding values from each source
            
        Returns:
            Tuple of (resolved_value, confidence, reasoning)
        """
        if not sources or not values or len(sources) != len(values):
            return None, 0.0, "No valid sources or values provided"
        
        if len(sources) == 1:
            trust_score = sources[0].get('trust_score', self.score_source(sources[0]['url']))
            return values[0], trust_score, f"Single source (trust: {trust_score:.2f})"
        
        # Score each source
        scored_sources = []
        for i, source in enumerate(sources):
            trust_score = source.get('trust_score')
            if trust_score is None:
                trust_score = self.score_source(source['url'], source.get('source_type'))
            
            scored_sources.append({
                'value': values[i],
                'source': source,
                'trust_score': trust_score
            })
        
        # Group by value
        value_groups: Dict[str, List[Dict]] = {}
        for item in scored_sources:
            key = str(item['value'])
            if key not in value_groups:
                value_groups[key] = []
            value_groups[key].append(item)
        
        # If all agree, high confidence
        if len(value_groups) == 1:
            avg_trust = sum(s['trust_score'] for s in scored_sources) / len(scored_sources)
            return (
                values[0],
                avg_trust,
                f"All {len(sources)} sources agree (avg trust: {avg_trust:.2f})"
            )
        
        # Weighted voting: sum trust scores for each value
        value_scores = {}
        for value_key, group in value_groups.items():
            total_trust = sum(item['trust_score'] for item in group)
            value_scores[value_key] = {
                'value': group[0]['value'],
                'total_trust': total_trust,
                'count': len(group),
                'sources': group
            }
        
        # Select value with highest total trust
        best_value_key = max(value_scores.keys(), key=lambda k: value_scores[k]['total_trust'])
        best = value_scores[best_value_key]
        
        # Calculate confidence based on margin
        total_trust_all = sum(v['total_trust'] for v in value_scores.values())
        confidence = best['total_trust'] / total_trust_all if total_trust_all > 0 else 0.5
        
        # Build reasoning
        other_values = [k for k in value_scores.keys() if k != best_value_key]
        reasoning = (
            f"Resolved '{best['value']}' from {len(value_groups)} conflicting values. "
            f"{best['count']} source(s) with total trust {best['total_trust']:.2f} vs "
            f"alternatives: {', '.join(other_values)}. Confidence: {confidence:.2f}"
        )
        
        return best['value'], confidence, reasoning
    
    def flag_low_confidence(
        self,
        value: Any,
        sources: List[Dict[str, Any]],
        threshold: float = 0.6
    ) -> bool:
        """
        Determine if a value should be flagged as low confidence.
        
        Args:
            value: The data value
            sources: Source dicts
            threshold: Trust threshold (default 0.6)
            
        Returns:
            True if should be flagged
        """
        if not sources:
            return True
        
        # Calculate average trust
        total_trust = 0.0
        for source in sources:
            trust_score = source.get('trust_score')
            if trust_score is None:
                trust_score = self.score_source(source['url'], source.get('source_type'))
            total_trust += trust_score
        
        avg_trust = total_trust / len(sources)
        return avg_trust < threshold
    
    def categorize_source(self, url: str) -> Tuple[str, float]:
        """
        Categorize a source and return its type and trust score.
        
        Args:
            url: Source URL
            
        Returns:
            Tuple of (source_type, trust_score)
        """
        try:
            domain = urlparse(url).netloc.lower()
            domain = re.sub(r'^www\.', '', domain)
        except:
            return ("unknown", self.SOURCE_TYPE_SCORES["unknown"])
        
        # Check known domains
        for trusted_domain, (dtype, score) in self.TRUSTED_DOMAINS.items():
            if trusted_domain in domain:
                return (dtype, score)
        
        # Heuristic categorization
        if any(filing in domain for filing in ['sec.gov', 'edgar', 'sedar', 'companieshouse']):
            return ("filing", self.SOURCE_TYPE_SCORES["filing"])
        
        if any(social in domain for social in ['twitter', 'facebook', 'reddit', 'instagram']):
            return ("social", self.SOURCE_TYPE_SCORES["social"])
        
        if 'blog' in domain or 'wordpress' in domain or 'medium.com' in domain:
            return ("blog", self.SOURCE_TYPE_SCORES["blog"])
        
        if 'news' in domain or 'times' in domain or 'post' in domain:
            return ("news_tier2", self.SOURCE_TYPE_SCORES["news_tier2"])
        
        return ("unknown", self.SOURCE_TYPE_SCORES["unknown"])
    
    def aggregate_trust_scores(
        self,
        sources: List[Dict[str, Any]]
    ) -> float:
        """
        Calculate aggregate trust score for a list of sources.
        
        Uses weighted average, giving more weight to higher-trust sources.
        
        Args:
            sources: List of source dicts
            
        Returns:
            Aggregate trust score
        """
        if not sources:
            return 0.0
        
        scores = []
        for source in sources:
            trust_score = source.get('trust_score')
            if trust_score is None:
                trust_score = self.score_source(source['url'], source.get('source_type'))
            scores.append(trust_score)
        
        # Weighted average (higher scores get more weight)
        total_weight = sum(s ** 2 for s in scores)  # Square to amplify high scores
        if total_weight == 0:
            return sum(scores) / len(scores)
        
        weighted_sum = sum(s ** 3 for s in scores)  # Cube for weighting
        return weighted_sum / total_weight


# Global instance
_trust_scorer = TrustScorer()


def get_trust_scorer() -> TrustScorer:
    """Get the global TrustScorer instance."""
    return _trust_scorer
