"""
Unit tests for State Manager.

Tests cover:
- State transitions
- Turn and round tracking
- Team assignments
- Resource multiplier calculation
- Serialization/deserialization
"""

import pytest
from src.utils.state_manager import DebateState, DebatePhase, InvalidStateTransition


class TestStateTransitions:
    """Test state transition logic."""
    
    def test_valid_transition_initialization_to_opening(self):
        """Test valid transition from initialization to opening."""
        state = DebateState("test_id", "test topic")
        assert state.phase == DebatePhase.INITIALIZATION
        
        state.transition_to(DebatePhase.OPENING)
        assert state.phase == DebatePhase.OPENING
    
    def test_valid_transition_full_flow(self):
        """Test complete valid transition flow."""
        state = DebateState("test_id", "test topic")
        
        state.transition_to(DebatePhase.OPENING)
        assert state.phase == DebatePhase.OPENING
        
        state.transition_to(DebatePhase.DEBATE_ROUNDS)
        assert state.phase == DebatePhase.DEBATE_ROUNDS
        
        state.transition_to(DebatePhase.CLOSING)
        assert state.phase == DebatePhase.CLOSING
        
        state.transition_to(DebatePhase.COMPLETED)
        assert state.phase == DebatePhase.COMPLETED
    
    def test_invalid_transition_skip_phase(self):
        """Test that skipping phases raises error."""
        state = DebateState("test_id", "test topic")
        
        with pytest.raises(InvalidStateTransition, match="Cannot transition"):
            state.transition_to(DebatePhase.CLOSING)  # Can't skip to closing
    
    def test_invalid_transition_backwards(self):
        """Test that going backwards raises error."""
        state = DebateState("test_id", "test topic")
        state.transition_to(DebatePhase.OPENING)
        
        with pytest.raises(InvalidStateTransition):
            state.transition_to(DebatePhase.INITIALIZATION)  # Can't go back
    
    def test_completed_is_terminal_state(self):
        """Test that completed state cannot transition."""
        state = DebateState("test_id", "test topic")
        state.phase = DebatePhase.COMPLETED
        
        with pytest.raises(InvalidStateTransition):
            state.transition_to(DebatePhase.OPENING)


class TestTurnTracking:
    """Test turn and round tracking."""
    
    def test_next_turn_increments_counter(self):
        """Test that next_turn increments turn count."""
        state = DebateState("test_id", "test topic")
        
        assert state.turn_count == 0
        assert state.current_speaker is None
        
        state.next_turn("debator_a")
        assert state.turn_count == 1
        assert state.current_speaker == "debator_a"
        
        state.next_turn("debator_b")
        assert state.turn_count == 2
        assert state.current_speaker == "debator_b"
    
    def test_next_round_increments_counter(self):
        """Test that next_round increments round count."""
        state = DebateState("test_id", "test topic")
        
        assert state.round_number == 0
        
        state.next_round()
        assert state.round_number == 1
        
        state.next_round()
        assert state.round_number == 2


class TestTeamAssignment:
    """Test team assignment logic."""
    
    def test_assign_teams_for_wins(self):
        """Test that winning 'for' stance becomes team a."""
        state = DebateState("test_id", "test topic")
        
        vote_results = {"for": 60, "against": 40}
        state.assign_teams("for stance", "against stance", vote_results)
        
        # Winner (for) becomes team_a
        assert state.team_assignments["team_a"]["stance"] == "for stance"
        assert state.team_assignments["team_b"]["stance"] == "against stance"
    
    def test_assign_teams_against_wins(self):
        """Test that winning 'against' stance becomes team a."""
        state = DebateState("test_id", "test topic")
        
        vote_results = {"for": 30, "against": 70}
        state.assign_teams("for stance", "against stance", vote_results)
        
        # Winner (against) becomes team_a
        assert state.team_assignments["team_a"]["stance"] == "against stance"
        assert state.team_assignments["team_b"]["stance"] == "for stance"
    
    def test_assign_teams_tie_randomizes(self):
        """Test that tie results in random assignment."""
        state = DebateState("test_id", "test topic")
        
        vote_results = {"for": 50, "against": 50}
        state.assign_teams("for stance", "against stance", vote_results)
        
        # Should have assignments (randomly assigned)
        assert "team_a" in state.team_assignments
        assert "team_b" in state.team_assignments
        # One team gets "for stance", the other gets "against stance"
        stances = {state.team_assignments["team_a"]["stance"], state.team_assignments["team_b"]["stance"]}
        assert stances == {"for stance", "against stance"}


class TestResourceMultiplier:
    """Test resource multiplier calculation."""
    
    def test_neutral_vote_no_multiplier(self):
        """Test that neutral vote (50-50) has no multiplier."""
        state = DebateState("test_id", "test topic")
        
        vote_results = {"for": 50, "against": 50}
        state.calculate_resource_multiplier(vote_results)
        
        assert state.resource_multiplier == 1.0
        assert state.audience_bias == 0.5
    
    def test_slight_bias_no_multiplier(self):
        """Test that slight bias (< 60%) has no multiplier."""
        state = DebateState("test_id", "test topic")
        
        vote_results = {"for": 55, "against": 45}
        state.calculate_resource_multiplier(vote_results)
        
        assert state.resource_multiplier == 1.0
        assert state.audience_bias == 0.55
    
    def test_strong_bias_applies_multiplier(self):
        """Test that strong bias (> 60%) applies 1.25x multiplier."""
        state = DebateState("test_id", "test topic")
        
        vote_results = {"for": 70, "against": 30}
        state.calculate_resource_multiplier(vote_results)
        
        assert state.resource_multiplier == 1.25
        assert state.audience_bias == 0.7
    
    def test_extreme_bias_applies_multiplier(self):
        """Test that extreme bias applies multiplier."""
        state = DebateState("test_id", "test topic")
        
        vote_results = {"for": 90, "against": 10}
        state.calculate_resource_multiplier(vote_results)
        
        assert state.resource_multiplier == 1.25
        assert state.audience_bias == 0.9
    
    def test_custom_threshold(self):
        """Test resource multiplier with custom threshold."""
        state = DebateState("test_id", "test topic")
        
        vote_results = {"for": 65, "against": 35}
        
        # With default threshold (0.6), should apply multiplier
        state.calculate_resource_multiplier(vote_results, threshold=0.6)
        assert state.resource_multiplier == 1.25
        
        # With higher threshold (0.7), should not apply
        state.calculate_resource_multiplier(vote_results, threshold=0.7)
        assert state.resource_multiplier == 1.0
    
    def test_get_underdog_team(self):
        """Test identifying the underdog team."""
        state = DebateState("test_id", "test topic")
        
        # No multiplier = no underdog
        assert state.get_underdog_team() is None
        
        # With multiplier, team b is underdog (winner is always team a)
        state.resource_multiplier = 1.25
        assert state.get_underdog_team() == "b"


class TestSerialization:
    """Test state serialization and deserialization."""
    
    def test_to_dict(self):
        """Test converting state to dictionary."""
        state = DebateState("test_id", "test topic")
        state.phase = DebatePhase.OPENING
        state.round_number = 1
        state.turn_count = 3
        state.current_speaker = "debator_a"
        state.team_assignments = {"for": "a", "against": "b"}
        state.resource_multiplier = 1.25
        state.audience_bias = 0.7
        
        data = state.to_dict()
        
        assert data["debate_id"] == "test_id"
        assert data["topic"] == "test topic"
        assert data["phase"] == "opening"
        assert data["round_number"] == 1
        assert data["turn_count"] == 3
        assert data["current_speaker"] == "debator_a"
        assert data["team_assignments"] == {"for": "a", "against": "b"}
        assert data["resource_multiplier"] == 1.25
        assert data["audience_bias"] == 0.7
    
    def test_from_dict(self):
        """Test creating state from dictionary."""
        data = {
            "debate_id": "test_id",
            "topic": "test topic",
            "phase": "opening",
            "round_number": 1,
            "turn_count": 3,
            "current_speaker": "debator_a",
            "team_assignments": {"for": "a", "against": "b"},
            "resource_multiplier": 1.25,
            "audience_bias": 0.7
        }
        
        state = DebateState.from_dict(data)
        
        assert state.debate_id == "test_id"
        assert state.topic == "test topic"
        assert state.phase == DebatePhase.OPENING
        assert state.round_number == 1
        assert state.turn_count == 3
        assert state.current_speaker == "debator_a"
        assert state.team_assignments == {"for": "a", "against": "b"}
        assert state.resource_multiplier == 1.25
        assert state.audience_bias == 0.7
    
    def test_round_trip_serialization(self):
        """Test that to_dict -> from_dict preserves state."""
        original = DebateState("test_id", "test topic")
        original.phase = DebatePhase.DEBATE_ROUNDS
        original.round_number = 2
        original.turn_count = 10
        original.team_assignments = {"for": "a", "against": "b"}
        
        data = original.to_dict()
        restored = DebateState.from_dict(data)
        
        assert restored.debate_id == original.debate_id
        assert restored.topic == original.topic
        assert restored.phase == original.phase
        assert restored.round_number == original.round_number
        assert restored.turn_count == original.turn_count


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
