"""
Reasoning chain infrastructure for tracking agent decisions.

Provides utilities for agents to log their reasoning process,
making the multi-agent system transparent and debuggable.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from dataclasses import dataclass, asdict
import json


@dataclass
class ReasoningStep:
    """
    A single step in an agent's reasoning process.
    
    Captures what decision was made, why it was made, what alternatives
    were considered, and the confidence level.
    """
    decision: str  # What decision was made
    rationale: str  # Why this decision was made
    alternatives_considered: List[str]  # What other options were evaluated
    chosen_option: str  # Which option was selected
    confidence: float  # 0.0 to 1.0 confidence in this decision
    timestamp: Optional[str] = None  # ISO format timestamp
    
    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
        
        # Validate confidence
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for state storage."""
        return asdict(self)
    
    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"Decision: {self.decision}\n"
            f"Rationale: {self.rationale}\n"
            f"Considered: {', '.join(self.alternatives_considered)}\n"
            f"Chosen: {self.chosen_option}\n"
            f"Confidence: {self.confidence:.2f}"
        )


class ReasoningChain:
    """
    Accumulator for reasoning steps by an agent.
    
    Agents use this to track their decision-making process
    throughout their execution.
    """
    
    def __init__(self, agent_name: str):
        """
        Initialize reasoning chain.
        
        Args:
            agent_name: Name of the agent using this chain
        """
        self.agent_name = agent_name
        self.steps: List[ReasoningStep] = []
    
    def add_step(
        self,
        decision: str,
        rationale: str,
        alternatives_considered: List[str],
        chosen_option: str,
        confidence: float
    ) -> ReasoningStep:
        """
        Add a reasoning step to the chain.
        
        Args:
            decision: What decision was made  
            rationale: Why this decision was made
            alternatives_considered: What other options were evaluated
            chosen_option: Which option was selected
            confidence: 0.0 to 1.0 confidence in this decision
            
        Returns:
            The created ReasoningStep
        """
        step = ReasoningStep(
            decision=decision,
            rationale=rationale,
            alternatives_considered=alternatives_considered,
            chosen_option=chosen_option,
            confidence=confidence
        )
        self.steps.append(step)
        return step
    
    def add_disambiguation(
        self,
        ambiguous_entity: str,
        candidates: List[str],
        chosen: str,
        rationale: str,
        confidence: float = 0.8
    ) -> ReasoningStep:
        """
        Add a disambiguation reasoning step.
        
        Convenience method for entity disambiguation scenarios.
        
        Args:
            ambiguous_entity: The entity that needed disambiguation
            candidates: List of candidate interpretations
            chosen: The chosen interpretation
            rationale: Why this interpretation was chosen
            confidence: Confidence in the choice (default 0.8)
            
        Returns:
            The created ReasoningStep
        """
        return self.add_step(
            decision=f"Disambiguate '{ambiguous_entity}'",
            rationale=rationale,
            alternatives_considered=candidates,
            chosen_option=chosen,
            confidence=confidence
        )
    
    def add_source_selection(
        self,
        data_type: str,
        sources_considered: List[str],
        chosen_source: str,
        rationale: str,
        confidence: float = 0.9
    ) -> ReasoningStep:
        """
        Add a source selection reasoning step.
        
        Convenience method for source selection scenarios.
        
        Args:
            data_type: Type of data being sourced (e.g., "financial data")
            sources_considered: List of sources evaluated
            chosen_source: The chosen source
            rationale: Why this source was chosen
            confidence: Confidence in the choice (default 0.9)
            
        Returns:
            The created ReasoningStep
        """
        return self.add_step(
            decision=f"Select source for {data_type}",
            rationale=rationale,
            alternatives_considered=sources_considered,
            chosen_option=chosen_source,
            confidence=confidence
        )
    
    def add_contradiction_resolution(
        self,
        data_field: str,
        conflicting_values: List[str],
        resolved_value: str,
        rationale: str,
        confidence: float = 0.7
    ) -> ReasoningStep:
        """
        Add a contradiction resolution reasoning step.
        
        Convenience method for handling conflicting data.
        
        Args:
            data_field: Field with conflicting data
            conflicting_values: List of conflicting values found
            resolved_value: The resolved value
            rationale: How the contradiction was resolved
            confidence: Confidence in the resolution (default 0.7)
            
        Returns:
            The created ReasoningStep
        """
        return self.add_step(
            decision=f"Resolve contradiction for {data_field}",
            rationale=rationale,
            alternatives_considered=conflicting_values,
            chosen_option=resolved_value,
            confidence=confidence
        )
    
    def to_list(self) -> List[Dict[str, Any]]:
        """Convert all steps to list of dictionaries for state storage."""
        return [step.to_dict() for step in self.steps]
    
    def format_for_display(self) -> str:
        """
        Format the reasoning chain for human-readable display.
        
        Returns:
            Formatted string with all reasoning steps
        """
        if not self.steps:
            return f"No reasoning steps recorded for {self.agent_name}"
        
        output = [f"Reasoning Chain: {self.agent_name}", "=" * 60]
        
        for i, step in enumerate(self.steps, 1):
            output.append(f"\nStep {i}:")
            output.append(str(step))
            output.append("-" * 60)
        
        return "\n".join(output)
    
    def format_for_llm_context(self) -> str:
        """
        Format reasoning chain as context for LLM prompts.
        
        Returns:
            Formatted string suitable for LLM context
        """
        if not self.steps:
            return ""
        
        output = [f"{self.agent_name} Reasoning:"]
        
        for i, step in enumerate(self.steps, 1):
            output.append(
                f"{i}. {step.decision}: {step.rationale} "
                f"(Chose '{step.chosen_option}' from {step.alternatives_considered})"
            )
        
        return "\n".join(output)
    
    def get_average_confidence(self) -> float:
        """
        Calculate average confidence across all steps.
        
        Returns:
            Average confidence (0.0 if no steps)
        """
        if not self.steps:
            return 0.0
        return sum(step.confidence for step in self.steps) / len(self.steps)
    
    def get_low_confidence_steps(self, threshold: float = 0.6) -> List[ReasoningStep]:
        """
        Get steps with confidence below threshold.
        
        Args:
            threshold: Confidence threshold (default 0.6)
            
        Returns:
            List of low-confidence steps
        """
        return [step for step in self.steps if step.confidence < threshold]
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps({
            "agent_name": self.agent_name,
            "steps": self.to_list(),
            "average_confidence": self.get_average_confidence()
        }, indent=2)
    
    def __len__(self) -> int:
        """Return number of reasoning steps."""
        return len(self.steps)
    
    def __str__(self) -> str:
        """Human-readable representation."""
        return self.format_for_display()
