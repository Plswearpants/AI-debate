"""
Unit tests for Debator Agent.

Tests cover:
- Agent initialization
- Citation extraction
- Response parsing
- Basic turn execution
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.agents.debator import DebatorAgent
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
def debator_agent(mock_file_manager, test_config):
    """Create a debator agent instance."""
    return DebatorAgent(
        name="debator_a",
        team="a",
        stance="for",
        file_manager=mock_file_manager,
        config=test_config
    )


class TestDebatorInitialization:
    """Test debator agent initialization."""
    
    def test_creates_debator_agent(self, debator_agent):
        """Test creating a debator agent."""
        assert debator_agent.name == "debator_a"
        assert debator_agent.team == "a"
        assert debator_agent.stance == "for"
        assert debator_agent.role == "debator"
    
    def test_has_gemini_client(self, debator_agent):
        """Test that debator has Gemini client."""
        assert debator_agent.gemini is not None
    
    def test_has_gemini_for_research(self, debator_agent):
        """Test that debator has Gemini client for research."""
        assert debator_agent.gemini is not None


class TestCitationExtraction:
    """Test citation extraction functionality."""
    
    def test_extract_citations_from_text(self, debator_agent):
        """Test extracting citation keys from text."""
        text = "This is a claim [a_1] and another [a_2] with more text [a_3]."
        citations = debator_agent._extract_citations(text)
        
        assert len(citations) == 3
        assert citations == ["a_1", "a_2", "a_3"]
    
    def test_extract_citations_no_duplicates(self, debator_agent):
        """Test that duplicate citations are removed."""
        text = "Claim [a_1] and another [a_1] and [a_2]."
        citations = debator_agent._extract_citations(text)
        
        assert len(citations) == 2
        assert citations == ["a_1", "a_2"]
    
    def test_extract_citations_team_specific(self, debator_agent):
        """Test that only own team's citations are extracted."""
        text = "My claim [a_1] and opponent's [b_1] and mine [a_2]."
        citations = debator_agent._extract_citations(text)
        
        # Should only extract a_X citations
        assert len(citations) == 2
        assert citations == ["a_1", "a_2"]
        assert "b_1" not in citations
    
    def test_extract_citations_empty_text(self, debator_agent):
        """Test extracting from text with no citations."""
        text = "No citations here"
        citations = debator_agent._extract_citations(text)
        
        assert citations == []


class TestResponseParsing:
    """Test response parsing."""
    
    def test_parse_response_with_supplementary(self, debator_agent):
        """Test parsing response with supplementary material."""
        response = """MAIN STATEMENT: This is the main argument [a_1].
        
SUPPLEMENTARY: Additional notes for the team."""
        
        main, supplementary = debator_agent._parse_response(response)
        
        assert "main argument" in main
        assert "[a_1]" in main
        assert "Additional notes" in supplementary
    
    def test_parse_response_no_supplementary(self, debator_agent):
        """Test parsing response without supplementary material."""
        response = "Just the main statement [a_1]."
        
        main, supplementary = debator_agent._parse_response(response)
        
        assert main == "Just the main statement [a_1]."
        assert supplementary == ""


class TestResearchQueryGeneration:
    """Test research query generation for Deep Research."""
    
    def test_build_research_query(self, debator_agent):
        """Test that research query is built properly."""
        topic = "Should we implement universal basic income?"
        
        query = debator_agent._build_research_query(topic)
        
        # Should include topic and stance
        assert topic in query
        assert debator_agent.stance in query
        assert "research" in query.lower() or "evidence" in query.lower()


class TestSystemPrompt:
    """Test system prompt generation."""
    
    def test_get_system_prompt_opening(self, debator_agent):
        """Test system prompt for opening statement."""
        prompt = debator_agent._get_system_prompt("opening")
        
        assert "debator_a" in prompt
        assert "opening" in prompt.lower()
        assert "citation" in prompt.lower()
    
    def test_get_system_prompt_rebuttal(self, debator_agent):
        """Test system prompt for rebuttal."""
        prompt = debator_agent._get_system_prompt("rebuttal")
        
        assert "rebuttal" in prompt.lower()
        assert "frontier" in prompt.lower()
    
    def test_get_system_prompt_closing(self, debator_agent):
        """Test system prompt for closing."""
        prompt = debator_agent._get_system_prompt("closing")
        
        assert "closing" in prompt.lower()
        assert "no new citations" in prompt.lower()


@pytest.mark.asyncio
class TestDebatorExecution:
    """Test debator turn execution (with mocks)."""
    
    async def test_execute_turn_unknown_phase_fails(self, debator_agent):
        """Test that unknown phase returns error."""
        context = AgentContext(
            debate_id="test",
            topic="test",
            phase="invalid_phase",
            round_number=1,
            current_state={},
            instructions="test"
        )
        
        response = await debator_agent.execute_turn(context)
        
        assert response.success is False
        assert len(response.errors) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
