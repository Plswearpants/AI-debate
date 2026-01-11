"""
Unit tests for Judge Agent.

Tests cover:
- Agent initialization
- Debate analysis
- Consensus identification
- Frontier mapping
- Structured output parsing
- File updates
"""

import pytest
import json
import re
from unittest.mock import Mock, patch
from datetime import datetime

from src.agents.judge import JudgeAgent
from src.agents.base import AgentContext, FileUpdateOperation
from src.config import Config


@pytest.fixture
def mock_file_manager():
    """Create a mock file manager."""
    return Mock()


@pytest.fixture
def test_config():
    """Create test configuration."""
    return Config.test_config()


@pytest.fixture
def judge_agent(mock_file_manager, test_config):
    """Create a judge agent instance."""
    return JudgeAgent(
        name="judge",
        file_manager=mock_file_manager,
        config=test_config
    )


class TestJudgeInitialization:
    """Test judge agent initialization."""
    
    def test_creates_judge_agent(self, judge_agent):
        """Test creating a judge agent."""
        assert judge_agent.name == "judge"
        assert judge_agent.role == "judge"
    
    def test_has_claude_client(self, judge_agent):
        """Test that judge has Claude client."""
        assert judge_agent.claude is not None


class TestSystemPrompt:
    """Test judge system prompt."""
    
    def test_system_prompt_emphasizes_neutrality(self, judge_agent):
        """Test that system prompt emphasizes neutral analysis."""
        prompt = judge_agent._get_system_prompt()
        prompt_lower = prompt.lower()
        
        assert "neutral" in prompt_lower
        assert "consensus" in prompt_lower
        assert "disagreement" in prompt_lower
        # Check for neutrality emphasis (not deciding winner)
        assert re.search(r'not.*(?:winning|decide)', prompt_lower) is not None


class TestAnalysisPromptBuilding:
    """Test building analysis prompts."""
    
    def test_build_analysis_prompt_with_transcript(self, judge_agent):
        """Test building prompt with debate transcript."""
        context = AgentContext(
            debate_id="test",
            topic="Should we implement UBI?",
            phase="opening",
            round_number=1,
            current_state={
                "history_chat": {
                    "public_transcript": [
                        {
                            "speaker": "a",
                            "statement": "UBI reduces poverty [a_1]",
                            "round_label": "Opening"
                        },
                        {
                            "speaker": "b",
                            "statement": "UBI causes inflation [b_1]",
                            "round_label": "Opening"
                        }
                    ]
                }
            },
            instructions="Analyze debate"
        )
        
        prompt = judge_agent._build_analysis_prompt(context)
        
        assert "Should we implement UBI?" in prompt
        assert "UBI reduces poverty" in prompt
        assert "UBI causes inflation" in prompt
        assert "Team a" in prompt or "Team b" in prompt
    
    def test_build_analysis_prompt_empty_transcript(self, judge_agent):
        """Test building prompt with no transcript yet."""
        context = AgentContext(
            debate_id="test",
            topic="Test topic",
            phase="opening",
            round_number=1,
            current_state={"history_chat": {"public_transcript": []}},
            instructions="Analyze"
        )
        
        prompt = judge_agent._build_analysis_prompt(context)
        
        assert "Test topic" in prompt
        assert "No statements yet" in prompt or "initial" in prompt.lower()


class TestLatentUpdate:
    """Test debate_latent file update creation."""
    
    def test_create_latent_update(self, judge_agent):
        """Test creating file update for debate_latent."""
        analysis = {
            "consensus": ["Both agree admin costs are high"],
            "disagreement_frontier": [
                {
                    "core_issue": "Impact on Innovation",
                    "a_stance": "Consolidation spurs efficiency",
                    "b_stance": "Price controls stifle R&D"
                }
            ]
        }
        
        update = judge_agent._create_latent_update(analysis, round_number=1)
        
        assert update.file_type == "debate_latent"
        assert update.operation == FileUpdateOperation.UPDATE_DEBATE_LATENT
        assert update.data["round_number"] == 1
        assert len(update.data["consensus"]) == 1
        assert len(update.data["disagreement_frontier"]) == 1


class TestFallbackParsing:
    """Test fallback parsing when JSON fails."""
    
    def test_parse_analysis_fallback_extracts_consensus(self, judge_agent):
        """Test extracting consensus from text."""
        response = """Consensus:
- Both sides agree that costs are high
- Both acknowledge implementation challenges

Disagreement Frontier:
- Issue: Economic impact
"""
        
        analysis = judge_agent._parse_analysis_fallback(response)
        
        assert "consensus" in analysis
        assert len(analysis["consensus"]) >= 1
        assert any("costs" in c.lower() for c in analysis["consensus"])
    
    def test_parse_analysis_fallback_extracts_frontier(self, judge_agent):
        """Test extracting frontier from text."""
        response = """Consensus: None

Disagreement Frontier:
Issue: Economic impact on jobs
Issue: Effect on innovation
"""
        
        analysis = judge_agent._parse_analysis_fallback(response)
        
        assert "disagreement_frontier" in analysis
        assert len(analysis["disagreement_frontier"]) >= 1


@pytest.mark.asyncio
class TestJudgeExecution:
    """Test judge turn execution (with mocks)."""
    
    async def test_execute_turn_with_mock_claude(self, judge_agent):
        """Test executing a turn with mocked Claude."""
        context = AgentContext(
            debate_id="test",
            topic="Test topic",
            phase="opening",
            round_number=1,
            current_state={
                "history_chat": {
                    "public_transcript": [
                        {"speaker": "a", "statement": "Argument A", "round_label": "Opening"},
                        {"speaker": "b", "statement": "Argument B", "round_label": "Opening"}
                    ]
                }
            },
            instructions="Analyze debate"
        )
        
        # Mock Claude response with valid JSON
        mock_response = json.dumps({
            "consensus": ["Both agree on the importance of evidence"],
            "disagreement_frontier": [
                {
                    "core_issue": "Economic feasibility",
                    "a_stance": "Cost-effective solution",
                    "b_stance": "Too expensive to implement"
                }
            ]
        })
        
        with patch.object(judge_agent.claude, 'generate', return_value=mock_response):
            response = await judge_agent.execute_turn(context)
        
        assert response.success is True
        assert "consensus" in response.output
        assert "disagreement_frontier" in response.output
        assert len(response.file_updates) == 1
        assert response.file_updates[0].file_type == "debate_latent"
    
    async def test_execute_turn_handles_errors(self, judge_agent):
        """Test that errors are handled gracefully."""
        context = AgentContext(
            debate_id="test",
            topic="test",
            phase="opening",
            round_number=1,
            current_state={},
            instructions="test"
        )
        
        # Mock Claude to raise error
        with patch.object(judge_agent.claude, 'generate', side_effect=Exception("API Error")):
            response = await judge_agent.execute_turn(context)
        
        assert response.success is False
        assert len(response.errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
