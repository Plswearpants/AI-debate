"""
Unit tests for Crowd Agent.

Tests cover:
- Agent initialization
- Persona loading and diversity
- Vote prompt building
- Vote parsing (structured and fallback)
- Batch voting
- File updates
"""

import pytest
import json
from unittest.mock import Mock, patch, AsyncMock

from src.agents.crowd import CrowdAgent
from src.agents.base import AgentContext, FileUpdateOperation
from src.config import Config


@pytest.fixture
def mock_file_manager():
    """Create a mock file manager."""
    return Mock()


@pytest.fixture
def test_config():
    """Create test configuration."""
    config = Config.test_config()
    config.crowd_size = 10  # Smaller for tests
    return config


@pytest.fixture
def crowd_agent(mock_file_manager, test_config):
    """Create a crowd agent instance."""
    return CrowdAgent(
        name="crowd",
        file_manager=mock_file_manager,
        config=test_config
    )


class TestCrowdInitialization:
    """Test crowd agent initialization."""
    
    def test_creates_crowd_agent(self, crowd_agent):
        """Test creating a crowd agent."""
        assert crowd_agent.name == "crowd"
        assert crowd_agent.role == "crowd"
    
    def test_has_lambda_client(self, crowd_agent):
        """Test that crowd has Lambda GPU client."""
        assert crowd_agent.lambda_client is not None
    
    def test_loads_personas(self, crowd_agent, test_config):
        """Test that personas are loaded."""
        assert len(crowd_agent.personas) == test_config.crowd_size
        assert all("id" in p for p in crowd_agent.personas)
        assert all("name" in p for p in crowd_agent.personas)
        assert all("description" in p for p in crowd_agent.personas)


class TestPersonaManagement:
    """Test persona loading and diversity."""
    
    def test_persona_diversity(self, crowd_agent):
        """Test that personas cover diverse types."""
        persona_types = {p.get("type") for p in crowd_agent.personas}
        
        # Should have multiple types
        assert len(persona_types) > 1
        # Common types should be present
        assert any(t in persona_types for t in ["political", "professional", "demographic"])
    
    def test_persona_ids_unique(self, crowd_agent):
        """Test that all persona IDs are unique."""
        ids = [p["id"] for p in crowd_agent.personas]
        assert len(ids) == len(set(ids))  # All unique
    
    def test_get_personas_summary(self, crowd_agent):
        """Test getting persona distribution summary."""
        summary = crowd_agent.get_personas_summary()
        
        assert "total_personas" in summary
        assert summary["total_personas"] == len(crowd_agent.personas)
        assert "by_type" in summary
        assert "sample_personas" in summary


class TestVotingPrompt:
    """Test voting prompt construction."""
    
    def test_build_voting_prompt_regular_vote(self, crowd_agent):
        """Test building prompt for regular vote (Vote 1+)."""
        persona = {
            "id": "v_001",
            "name": "Fiscal Conservative",
            "description": "Prioritizes low taxes and limited government"
        }
        
        context = AgentContext(
            debate_id="test",
            topic="Should we implement UBI?",
            phase="opening",
            round_number=1,
            current_state={
                "history_chat": {
                    "public_transcript": [
                        {"speaker": "a", "statement": "UBI reduces poverty [a_1]"},
                        {"speaker": "b", "statement": "UBI causes inflation [b_1]"}
                    ]
                }
            },
            instructions="Vote"
        )
        
        prompt = crowd_agent._build_voting_prompt(persona, context)
        
        assert persona["name"] in prompt
        assert "Should we implement UBI?" in prompt
        assert "UBI reduces poverty" in prompt or "Team a" in prompt
        assert "score" in prompt.lower()
        assert "0-100" in prompt
    
    def test_build_vote_zero_prompt(self, crowd_agent):
        """Test building Vote 0 prompt (stance preference)."""
        persona = {
            "id": "v_001",
            "name": "Progressive Activist",
            "description": "Supports social justice"
        }
        
        context = AgentContext(
            debate_id="test",
            topic="Should we implement universal basic income?",
            phase="initialization",
            round_number=0,  # Vote 0
            current_state={"history_chat": {"public_transcript": []}},
            instructions="Vote on initial stance"
        )
        
        prompt = crowd_agent._build_vote_zero_prompt(persona, context)
        
        assert persona["name"] in prompt
        assert context.topic in prompt
        assert "initial" in prompt.lower() or "before" in prompt.lower()
        assert "stance" in prompt.lower()
        assert "FOR" in prompt or "AGAINST" in prompt
        # Should NOT mention teams (teams don't exist yet)
        assert prompt.count("Team a") == 0 or "speak first as Team a" in prompt


class TestVoteParsing:
    """Test vote parsing."""
    
    def test_parse_vote_from_json(self, crowd_agent):
        """Test parsing valid JSON vote."""
        response = '{"score": 75, "reasoning": "Strong economic evidence"}'
        persona = {"id": "v_001", "name": "Test Persona"}
        
        vote = crowd_agent._parse_vote(response, persona)
        
        assert vote["voter_id"] == "v_001"
        assert vote["persona"] == "Test Persona"
        assert vote["score"] == 75
        assert "economic" in vote["reasoning"].lower()
    
    def test_parse_vote_fallback(self, crowd_agent):
        """Test fallback parsing when JSON fails."""
        response = "Score: 82. The arguments are convincing."
        persona = {"id": "v_002", "name": "Test"}
        
        vote = crowd_agent._parse_vote(response, persona)
        
        assert vote["score"] == 82
        assert "voter_id" in vote
    
    def test_parse_vote_clamps_score(self, crowd_agent):
        """Test that scores are clamped to 0-100 range."""
        response = '{"score": 150}'
        persona = {"id": "v_003", "name": "Test"}
        
        vote = crowd_agent._parse_vote(response, persona)
        
        assert 0 <= vote["score"] <= 100
        assert vote["score"] == 100  # Clamped from 150
    
    def test_parse_vote_default_score(self, crowd_agent):
        """Test default score when parsing fails completely."""
        response = "Invalid response with no score"
        persona = {"id": "v_004", "name": "Test"}
        
        vote = crowd_agent._parse_vote(response, persona)
        
        # Should default to neutral (50)
        assert vote["score"] == 50


class TestCrowdUpdate:
    """Test crowd_opinion file updates."""
    
    def test_create_crowd_update(self, crowd_agent):
        """Test creating file update for crowd_opinion."""
        votes = [
            {"voter_id": "v_001", "persona": "Test 1", "score": 75, "reasoning": "Good"},
            {"voter_id": "v_002", "persona": "Test 2", "score": 45, "reasoning": "Weak"}
        ]
        
        update = crowd_agent._create_crowd_update(votes, round_number=1)
        
        assert update.file_type == "crowd_opinion"
        assert update.operation == FileUpdateOperation.ADD_CROWD_VOTE
        assert update.data["round_number"] == 1
        assert len(update.data["votes"]) == 2


@pytest.mark.asyncio
class TestCrowdExecution:
    """Test crowd turn execution (with mocks)."""
    
    async def test_execute_turn_with_mock_lambda(self, crowd_agent):
        """Test executing voting turn with mocked Lambda GPU."""
        context = AgentContext(
            debate_id="test",
            topic="Test topic",
            phase="opening",
            round_number=1,
            current_state={
                "history_chat": {
                    "public_transcript": [
                        {"speaker": "a", "statement": "Argument A"},
                        {"speaker": "b", "statement": "Argument B"}
                    ]
                }
            },
            instructions="Vote on debate"
        )
        
        # Mock Lambda GPU to return JSON votes
        mock_responses = [
            '{"score": 75, "reasoning": "Strong evidence"}',
            '{"score": 45, "reasoning": "Weak arguments"}',
            '{"score": 60, "reasoning": "Balanced"}',
            '{"score": 55, "reasoning": "Neutral"}',
            '{"score": 70, "reasoning": "Convincing"}',
            '{"score": 40, "reasoning": "Not convinced"}',
            '{"score": 65, "reasoning": "Good points"}',
            '{"score": 50, "reasoning": "Undecided"}',
            '{"score": 80, "reasoning": "Excellent"}',
            '{"score": 35, "reasoning": "Poor logic"}'
        ]
        
        with patch.object(crowd_agent.lambda_client, 'generate_batch', return_value=mock_responses):
            response = await crowd_agent.execute_turn(context)
        
        assert response.success is True
        assert "votes" in response.output
        assert len(response.output["votes"]) == 10
        assert "average_score" in response.output
        assert 0 <= response.output["average_score"] <= 100
        assert len(response.file_updates) == 1
    
    async def test_execute_turn_handles_errors(self, crowd_agent):
        """Test that errors are handled gracefully."""
        context = AgentContext(
            debate_id="test",
            topic="test",
            phase="opening",
            round_number=1,
            current_state={},
            instructions="test"
        )
        
        # Mock Lambda to raise error
        with patch.object(crowd_agent.lambda_client, 'generate_batch', side_effect=Exception("GPU Error")):
            response = await crowd_agent.execute_turn(context)
        
        assert response.success is False
        assert len(response.errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
