"""
Unit tests for FactChecker Agent.

Tests cover:
- Agent initialization
- Citation identification (opponent and own)
- Verification with Perplexity
- Defense response generation
- Structured output parsing
- File updates
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from src.agents.factchecker import FactCheckerAgent
from src.agents.base import AgentContext
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
def factchecker_agent(mock_file_manager, test_config):
    """Create a factchecker agent instance."""
    return FactCheckerAgent(
        name="factchecker_a",
        team="a",
        file_manager=mock_file_manager,
        config=test_config
    )


class TestFactCheckerInitialization:
    """Test fact-checker agent initialization."""
    
    def test_creates_factchecker_agent(self, factchecker_agent):
        """Test creating a fact-checker agent."""
        assert factchecker_agent.name == "factchecker_a"
        assert factchecker_agent.team == "a"
        assert factchecker_agent.opponent_team == "b"
        assert factchecker_agent.role == "factchecker"
    
    def test_has_perplexity_client(self, factchecker_agent):
        """Test that fact-checker has Perplexity client."""
        assert factchecker_agent.perplexity is not None


class TestCitationIdentification:
    """Test identifying citations to verify or defend."""
    
    def test_get_opponent_recent_citations(self, factchecker_agent):
        """Test identifying opponent's recent citations."""
        context = AgentContext(
            debate_id="test",
            topic="test",
            phase="opening",
            round_number=1,
            current_state={
                "citation_pool": {
                    "citations": {
                        "team b": {
                            "b_1": {
                                "source_url": "http://example.com/b1",
                                "added_in_round": 1,
                                "verification": {}
                            },
                            "b_2": {
                                "source_url": "http://example.com/b2",
                                "added_in_round": 1,
                                "verification": {}
                            }
                        }
                    }
                }
            },
            instructions="Verify opponent citations"
        )
        
        citations = factchecker_agent._get_opponent_recent_citations(context)
        
        assert len(citations) == 2
        assert "b_1" in citations
        assert "b_2" in citations
    
    def test_get_opponent_citations_empty(self, factchecker_agent):
        """Test when opponent has no recent citations."""
        context = AgentContext(
            debate_id="test",
            topic="test",
            phase="opening",
            round_number=1,
            current_state={"citation_pool": {"citations": {}}},
            instructions="test"
        )
        
        citations = factchecker_agent._get_opponent_recent_citations(context)
        assert citations == {}
    
    def test_get_our_citations_needing_defense(self, factchecker_agent):
        """Test identifying our citations that need defense."""
        context = AgentContext(
            debate_id="test",
            topic="test",
            phase="rebuttal",
            round_number=2,
            current_state={
                "citation_pool": {
                    "citations": {
                        "team a": {
                            "a_1": {
                                "source_url": "http://example.com/a1",
                                "verification": {
                                    "adversary_comment": "Source is outdated",
                                    "proponent_response": None  # Need to respond
                                }
                            },
                            "a_2": {
                                "source_url": "http://example.com/a2",
                                "verification": {
                                    "adversary_comment": "Weak source",
                                    "proponent_response": "Already responded"  # No need
                                }
                            }
                        }
                    }
                }
            },
            instructions="Defend citations"
        )
        
        citations = factchecker_agent._get_our_citations_needing_defense(context)
        
        assert len(citations) == 1
        assert "a_1" in citations
        assert "a_2" not in citations  # Already has response


class TestVerificationParsing:
    """Test verification result parsing."""
    
    def test_parse_verification_fallback(self, factchecker_agent):
        """Test fallback parsing when JSON fails."""
        response = "Credibility score: 7. Correspondence score: 8. The source is reputable."
        
        verification = factchecker_agent._parse_verification_fallback(response)
        
        assert verification["source_credibility_score"] == 7
        assert verification["content_correspondence_score"] == 8
        assert "adversary_comment" in verification
        assert verification["verified_by"] == "factchecker_a"
    
    def test_parse_verification_fallback_clamps_scores(self, factchecker_agent):
        """Test that scores are clamped to 1-10 range."""
        response = "Credibility: 15. Correspondence: -5. Bad source."
        
        verification = factchecker_agent._parse_verification_fallback(response)
        
        # Should clamp to valid range
        assert 1 <= verification["source_credibility_score"] <= 10
        assert 1 <= verification["content_correspondence_score"] <= 10


@pytest.mark.asyncio
class TestFactCheckerExecution:
    """Test fact-checker turn execution (with mocks)."""
    
    async def test_execute_turn_with_mock_perplexity(self, factchecker_agent):
        """Test executing a turn with mocked Perplexity."""
        # Mock context with opponent citations
        context = AgentContext(
            debate_id="test",
            topic="test",
            phase="opening",
            round_number=1,
            current_state={
                "citation_pool": {
                    "citations": {
                        "team b": {
                            "b_1": {
                                "source_url": "http://example.com/b1",
                                "added_in_round": 1,
                                "verification": {}
                            }
                        }
                    }
                }
            },
            instructions="Verify opponent citations"
        )
        
        # Mock Perplexity response
        with patch.object(factchecker_agent.perplexity, 'chat', return_value='{"source_credibility_score": 8, "content_correspondence_score": 7, "adversary_comment": "Good source but minor issues"}'):
            response = await factchecker_agent.execute_turn(context)
        
        assert response.success is True
        assert "offense" in response.output
        assert len(response.file_updates) > 0
    
    async def test_execute_turn_handles_errors(self, factchecker_agent):
        """Test that errors are handled gracefully."""
        context = AgentContext(
            debate_id="test",
            topic="test",
            phase="opening",
            round_number=1,
            current_state={},
            instructions="test"
        )
        
        # Mock Perplexity to raise error
        with patch.object(factchecker_agent.perplexity, 'chat', side_effect=Exception("API Error")):
            response = await factchecker_agent.execute_turn(context)
        
        # Should still succeed (no citations to verify)
        assert response.success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
