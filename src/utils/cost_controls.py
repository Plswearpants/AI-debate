"""
Cost Controls - Monitor and contain Deep Research costs.

Based on comprehensive cost analysis, implements multiple knobs to prevent
runaway costs while maintaining debate quality.

Key insights from cost_analysis.md:
- 200k Token Cliff: Costs double after 200k tokens
- Grounding: $0.035 per search query
- Simple research: ~$0.12
- Complex research: ~$4.74
- Context Balloon: Costs compound as context grows
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class ResearchTier(Enum):
    """Research depth tiers with different cost profiles."""
    QUICK = "quick"           # Google Search only, ~$0.10
    STANDARD = "standard"     # Deep Research with limits, ~$1.00
    DEEP = "deep"            # Full Deep Research, ~$3.00
    EXHAUSTIVE = "exhaustive" # No limits, ~$5.00+


@dataclass
class CostBudget:
    """Cost budget for a debate or single research task."""
    
    # Per-research limits
    max_cost_per_research: float = 2.0  # Hard cap per Deep Research call
    max_grounding_queries: int = 20     # Limit search queries
    max_context_tokens: int = 180000    # Stay below 200k cliff
    max_output_tokens: int = 15000      # Limit thinking + synthesis
    max_research_time: int = 300        # 5 minutes max
    
    # Per-debate limits
    max_cost_per_debate: float = 5.0    # Total budget for entire debate
    max_deep_research_calls: int = 4    # Limit expensive research calls
    
    # Fallback thresholds
    use_quick_search_threshold: float = 1.0  # Switch to quick search if budget low
    
    @classmethod
    def conservative(cls) -> "CostBudget":
        """Conservative budget - prioritize cost savings."""
        return cls(
            max_cost_per_research=0.50,
            max_grounding_queries=10,
            max_context_tokens=100000,
            max_output_tokens=8000,
            max_research_time=180,  # 3 minutes
            max_cost_per_debate=2.0,
            max_deep_research_calls=2  # Opening only
        )
    
    @classmethod
    def balanced(cls) -> "CostBudget":
        """Balanced budget - good quality at reasonable cost."""
        return cls(
            max_cost_per_research=2.0,
            max_grounding_queries=20,
            max_context_tokens=180000,
            max_output_tokens=15000,
            max_research_time=300,  # 5 minutes
            max_cost_per_debate=5.0,
            max_deep_research_calls=4  # Opening + 1 rebuttal round
        )
    
    @classmethod
    def premium(cls) -> "CostBudget":
        """Premium budget - prioritize quality."""
        return cls(
            max_cost_per_research=5.0,
            max_grounding_queries=40,
            max_context_tokens=300000,
            max_output_tokens=30000,
            max_research_time=600,  # 10 minutes
            max_cost_per_debate=15.0,
            max_deep_research_calls=6  # Opening + all rebuttals
        )


class CostTracker:
    """Tracks costs in real-time during debate execution."""
    
    def __init__(self, budget: CostBudget):
        """
        Initialize cost tracker.
        
        Args:
            budget: Cost budget to enforce
        """
        self.budget = budget
        self.total_cost = 0.0
        self.research_count = 0
        self.deep_research_count = 0
        self.costs_by_phase = {
            "opening": 0.0,
            "rebuttal": 0.0,
            "closing": 0.0,
            "factchecking": 0.0,
            "judging": 0.0,
            "voting": 0.0
        }
    
    def can_afford_deep_research(self) -> bool:
        """Check if we can afford another Deep Research call."""
        if self.deep_research_count >= self.budget.max_deep_research_calls:
            return False
        
        remaining_budget = self.budget.max_cost_per_debate - self.total_cost
        if remaining_budget < self.budget.max_cost_per_research:
            return False
        
        return True
    
    def record_research_cost(
        self,
        cost: float,
        is_deep: bool = True,
        phase: str = "opening"
    ) -> None:
        """
        Record cost of a research operation.
        
        Args:
            cost: Estimated cost in USD
            is_deep: Whether this was Deep Research (vs quick search)
            phase: Debate phase
        """
        self.total_cost += cost
        self.research_count += 1
        if is_deep:
            self.deep_research_count += 1
        self.costs_by_phase[phase] += cost
    
    def get_remaining_budget(self) -> float:
        """Get remaining budget for the debate."""
        return max(0, self.budget.max_cost_per_debate - self.total_cost)
    
    def should_use_quick_search(self) -> bool:
        """Determine if we should fallback to quick search."""
        remaining = self.get_remaining_budget()
        return remaining < self.budget.use_quick_search_threshold
    
    def get_report(self) -> Dict[str, Any]:
        """Get cost report."""
        return {
            "total_cost": round(self.total_cost, 2),
            "remaining_budget": round(self.get_remaining_budget(), 2),
            "research_count": self.research_count,
            "deep_research_count": self.deep_research_count,
            "costs_by_phase": {k: round(v, 2) for k, v in self.costs_by_phase.items()},
            "budget_utilization": round((self.total_cost / self.budget.max_cost_per_debate) * 100, 1)
        }


def estimate_deep_research_cost(
    num_queries: int = 20,
    context_tokens: int = 150000,
    output_tokens: int = 10000,
    cached_reprocessing: int = 2000000
) -> float:
    """
    Estimate cost of a Deep Research operation.
    
    Based on cost_analysis.md pricing:
    - Grounding: $0.035 per query
    - Input tokens (≤200k): $2.00 / 1M
    - Input tokens (>200k): $4.00 / 1M
    - Output tokens (≤200k): $12.00 / 1M
    - Output tokens (>200k): $18.00 / 1M
    - Cached input: $0.40 / 1M
    
    Args:
        num_queries: Number of search queries
        context_tokens: Total context tokens ingested
        output_tokens: Total output tokens (thinking + report)
        cached_reprocessing: Equivalent cached tokens processed
    
    Returns:
        Estimated cost in USD
    """
    # Grounding cost
    grounding_cost = num_queries * 0.035
    
    # Input token cost (with 200k cliff)
    if context_tokens <= 200000:
        input_cost = (context_tokens / 1_000_000) * 2.00
    else:
        # First 200k at $2, rest at $4
        input_cost = (200_000 / 1_000_000) * 2.00 + ((context_tokens - 200_000) / 1_000_000) * 4.00
    
    # Output token cost (with 200k cliff)
    context_tier = "high" if context_tokens > 200000 else "low"
    output_rate = 18.00 if context_tier == "high" else 12.00
    output_cost = (output_tokens / 1_000_000) * output_rate
    
    # Cached reprocessing cost (stateful overhead)
    cache_rate = 0.40 if context_tokens > 200000 else 0.20
    cache_cost = (cached_reprocessing / 1_000_000) * cache_rate
    
    total = grounding_cost + input_cost + output_cost + cache_cost
    return round(total, 2)


# Pre-calculated cost estimates for common scenarios
COST_ESTIMATES = {
    ResearchTier.QUICK: 0.10,       # Google search only
    ResearchTier.STANDARD: 1.00,    # Limited Deep Research
    ResearchTier.DEEP: 3.00,        # Full Deep Research
    ResearchTier.EXHAUSTIVE: 5.00   # Unlimited Deep Research
}


def get_research_tier_for_budget(remaining_budget: float) -> ResearchTier:
    """
    Determine appropriate research tier based on remaining budget.
    
    Args:
        remaining_budget: Remaining debate budget in USD
    
    Returns:
        Appropriate research tier
    """
    if remaining_budget < 0.50:
        return ResearchTier.QUICK
    elif remaining_budget < 1.50:
        return ResearchTier.STANDARD
    elif remaining_budget < 4.00:
        return ResearchTier.DEEP
    else:
        return ResearchTier.EXHAUSTIVE
