"""
State Manager - Tracks debate state and manages state transitions.

This module provides:
- Debate state tracking (phase, round, turn)
- State transition validation
- Resource allocation tracking
- Turn sequencing
"""

from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


class DebatePhase(Enum):
    """Enum for debate phases."""
    INITIALIZATION = "initialization"
    OPENING = "opening"
    DEBATE_ROUNDS = "debate_rounds"
    CLOSING = "closing"
    COMPLETED = "completed"


class InvalidStateTransition(Exception):
    """Raised when an invalid state transition is attempted."""
    pass


@dataclass
class DebateState:
    """Tracks the current state of a debate."""
    
    debate_id: str
    topic: str
    phase: DebatePhase = DebatePhase.INITIALIZATION
    round_number: int = 0
    turn_count: int = 0
    current_speaker: Optional[str] = None
    team_assignments: Dict[str, str] = field(default_factory=dict)  # {stance: team}
    resource_multiplier: float = 1.0
    audience_bias: float = 0.5  # 0.0 to 1.0 (0.5 = neutral)
    
    # Valid state transitions
    VALID_TRANSITIONS = {
        DebatePhase.INITIALIZATION: [DebatePhase.OPENING],
        DebatePhase.OPENING: [DebatePhase.DEBATE_ROUNDS],
        DebatePhase.DEBATE_ROUNDS: [DebatePhase.CLOSING],
        DebatePhase.CLOSING: [DebatePhase.COMPLETED],
        DebatePhase.COMPLETED: []  # Terminal state
    }
    
    def transition_to(self, new_phase: DebatePhase) -> None:
        """
        Transition to a new phase with validation.
        
        Args:
            new_phase: The phase to transition to
        
        Raises:
            InvalidStateTransition: If the transition is not allowed
        """
        valid_next_phases = self.VALID_TRANSITIONS.get(self.phase, [])
        
        if new_phase not in valid_next_phases:
            raise InvalidStateTransition(
                f"Cannot transition from {self.phase.value} to {new_phase.value}. "
                f"Valid next phases: {[p.value for p in valid_next_phases]}"
            )
        
        self.phase = new_phase
    
    def next_turn(self, speaker: str) -> None:
        """
        Advance to the next turn.
        
        Args:
            speaker: The agent name taking the turn
        """
        self.current_speaker = speaker
        self.turn_count += 1
    
    def next_round(self) -> None:
        """Advance to the next round."""
        self.round_number += 1
    
    def assign_teams(self, for_stance: str, against_stance: str, vote_results: Dict[str, int]) -> None:
        """
        Assign teams based on Vote Zero results.
        
        Winner gets team "a", loser gets team "b".
        
        Args:
            for_stance: Description of the "for" position
            against_stance: Description of the "against" position
            vote_results: Dict with vote counts, e.g., {"for": 60, "against": 40}
        """
        if vote_results["for"] > vote_results["against"]:
            # "for" wins -> team a, "against" -> team b
            self.team_assignments = {
                "team_a": {
                    "stance": for_stance,
                    "agents": ["debator_a", "factchecker_a"]
                },
                "team_b": {
                    "stance": against_stance,
                    "agents": ["debator_b", "factchecker_b"]
                }
            }
        elif vote_results["against"] > vote_results["for"]:
            # "against" wins -> team a, "for" -> team b
            self.team_assignments = {
                "team_a": {
                    "stance": against_stance,
                    "agents": ["debator_a", "factchecker_a"]
                },
                "team_b": {
                    "stance": for_stance,
                    "agents": ["debator_b", "factchecker_b"]
                }
            }
        else:
            # Tie - randomize
            import random
            if random.random() > 0.5:
                self.team_assignments = {
                    "team_a": {
                        "stance": for_stance,
                        "agents": ["debator_a", "factchecker_a"]
                    },
                    "team_b": {
                        "stance": against_stance,
                        "agents": ["debator_b", "factchecker_b"]
                    }
                }
            else:
                self.team_assignments = {
                    "team_a": {
                        "stance": against_stance,
                        "agents": ["debator_a", "factchecker_a"]
                    },
                    "team_b": {
                        "stance": for_stance,
                        "agents": ["debator_b", "factchecker_b"]
                    }
                }
    
    def calculate_resource_multiplier(self, vote_results: Dict[str, int], threshold: float = 0.6) -> None:
        """
        Calculate and set resource multiplier based on audience bias.
        
        Args:
            vote_results: Dict with vote counts
            threshold: Bias threshold (default 0.6 = 60%)
        """
        total_votes = sum(vote_results.values())
        if total_votes == 0:
            self.resource_multiplier = 1.0
            self.audience_bias = 0.5
            return
        
        # Calculate bias as percentage for the winning side
        max_votes = max(vote_results.values())
        bias = max_votes / total_votes
        self.audience_bias = bias
        
        # Apply multiplier if bias exceeds threshold
        if bias > threshold:
            # The underdog gets 1.25x resources
            self.resource_multiplier = 1.25
        else:
            self.resource_multiplier = 1.0
    
    def get_underdog_team(self) -> Optional[str]:
        """
        Get the team that should receive resource multiplier.
        
        Returns:
            Team identifier ("a" or "b") or None if no multiplier
        """
        if self.resource_multiplier == 1.0:
            return None
        
        # The team with fewer votes is the underdog
        # We assigned the winner as team "a", so team "b" is underdog
        return "b"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return {
            "debate_id": self.debate_id,
            "topic": self.topic,
            "phase": self.phase.value,
            "round_number": self.round_number,
            "turn_count": self.turn_count,
            "current_speaker": self.current_speaker,
            "team_assignments": self.team_assignments,
            "resource_multiplier": self.resource_multiplier,
            "audience_bias": self.audience_bias
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DebateState":
        """Create DebateState from dictionary."""
        state = cls(
            debate_id=data["debate_id"],
            topic=data["topic"]
        )
        state.phase = DebatePhase(data["phase"])
        state.round_number = data["round_number"]
        state.turn_count = data["turn_count"]
        state.current_speaker = data["current_speaker"]
        state.team_assignments = data["team_assignments"]
        state.resource_multiplier = data["resource_multiplier"]
        state.audience_bias = data["audience_bias"]
        return state
    
    @classmethod
    def from_checkpoint(cls, checkpoint_state: Dict[str, Any]) -> "DebateState":
        """
        Create DebateState from checkpoint file format.
        
        Args:
            checkpoint_state: State dict from checkpoint file
            
        Returns:
            Reconstructed DebateState
        """
        # Note: checkpoint doesn't include debate_id and topic, so we need
        # to pass those separately. For now, use placeholder.
        state = cls(
            debate_id=checkpoint_state.get("debate_id", "unknown"),
            topic=checkpoint_state.get("topic", "unknown")
        )
        state.phase = DebatePhase(checkpoint_state["phase"])
        state.round_number = checkpoint_state["round_number"]
        state.turn_count = checkpoint_state["turn_count"]
        state.current_speaker = checkpoint_state.get("current_speaker")
        state.team_assignments = checkpoint_state["team_assignments"]
        state.resource_multiplier = checkpoint_state["resource_multiplier"]
        state.audience_bias = checkpoint_state.get("audience_bias", 0.5)
        return state
