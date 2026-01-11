"""
Unit tests for Agent Base Classes.

Tests cover:
- AgentContext creation
- AgentResponse creation
- FileUpdate structure
- Agent read_state functionality
"""

import pytest
from unittest.mock import Mock, MagicMock
from src.agents.base import (
    Agent, AgentContext, AgentResponse, FileUpdate, FileUpdateOperation
)


class TestAgentContext:
    """Test AgentContext dataclass."""
    
    def test_create_agent_context(self):
        """Test creating an AgentContext."""
        context = AgentContext(
            debate_id="test_123",
            topic="Should we test?",
            phase="opening",
            round_number=1,
            current_state={"test": "data"},
            instructions="Generate opening statement",
            metadata={"extra": "info"}
        )
        
        assert context.debate_id == "test_123"
        assert context.topic == "Should we test?"
        assert context.phase == "opening"
        assert context.round_number == 1
        assert context.current_state == {"test": "data"}
        assert context.instructions == "Generate opening statement"
        assert context.metadata == {"extra": "info"}
    
    def test_agent_context_default_metadata(self):
        """Test that metadata defaults to empty dict."""
        context = AgentContext(
            debate_id="test",
            topic="test",
            phase="opening",
            round_number=1,
            current_state={},
            instructions="test"
        )
        
        assert context.metadata == {}


class TestAgentResponse:
    """Test AgentResponse dataclass."""
    
    def test_create_agent_response(self):
        """Test creating an AgentResponse."""
        file_update = FileUpdate(
            file_type="history_chat",
            operation=FileUpdateOperation.APPEND_TURN,
            data={"statement": "test"}
        )
        
        response = AgentResponse(
            agent_name="debator_a",
            success=True,
            output={"statement": "My argument"},
            file_updates=[file_update],
            errors=[],
            metadata={"tokens": 500}
        )
        
        assert response.agent_name == "debator_a"
        assert response.success is True
        assert response.output["statement"] == "My argument"
        assert len(response.file_updates) == 1
        assert response.file_updates[0].operation == FileUpdateOperation.APPEND_TURN
        assert response.errors == []
        assert response.metadata["tokens"] == 500
    
    def test_agent_response_defaults(self):
        """Test AgentResponse default values."""
        response = AgentResponse(
            agent_name="test",
            success=True,
            output={}
        )
        
        assert response.file_updates == []
        assert response.errors == []
        assert response.metadata == {}


class TestFileUpdate:
    """Test FileUpdate dataclass."""
    
    def test_create_file_update(self):
        """Test creating a FileUpdate."""
        update = FileUpdate(
            file_type="citation_pool",
            operation=FileUpdateOperation.ADD_CITATION,
            data={"team": "a", "key": "a_1", "citation": {}},
            path=["citations", "team a"]
        )
        
        assert update.file_type == "citation_pool"
        assert update.operation == FileUpdateOperation.ADD_CITATION
        assert update.data["team"] == "a"
        assert update.path == ["citations", "team a"]
    
    def test_file_update_operations_enum(self):
        """Test FileUpdateOperation enum values."""
        assert FileUpdateOperation.APPEND_TURN.value == "append_turn"
        assert FileUpdateOperation.ADD_CITATION.value == "add_citation"
        assert FileUpdateOperation.UPDATE_VERIFICATION.value == "update_verification"
        assert FileUpdateOperation.UPDATE_DEBATE_LATENT.value == "update_debate_latent"
        assert FileUpdateOperation.ADD_CROWD_VOTE.value == "add_crowd_vote"


class MockAgent(Agent):
    """Mock agent for testing."""
    
    async def execute_turn(self, context: AgentContext) -> AgentResponse:
        """Mock implementation."""
        return self.create_response(
            success=True,
            output={"test": "output"}
        )


class TestAgentBase:
    """Test Agent base class functionality."""
    
    def test_agent_initialization(self):
        """Test creating an agent."""
        mock_fm = Mock()
        agent = MockAgent("debator_a", "debator", mock_fm)
        
        assert agent.name == "debator_a"
        assert agent.role == "debator"
        assert agent.file_manager == mock_fm
    
    def test_read_state(self):
        """Test agent reads filtered state from files."""
        mock_fm = Mock()
        mock_fm.read_for_agent.side_effect = [
            {"public_transcript": []},  # history_chat
            {"citations": {}},          # citation_pool
            {"round_history": []},      # debate_latent
            {}                          # crowd_opinion (no access)
        ]
        
        agent = MockAgent("debator_a", "debator", mock_fm)
        state = agent.read_state()
        
        assert "history_chat" in state
        assert "citation_pool" in state
        assert "debate_latent" in state
        # crowd_opinion shouldn't be included (empty dict)
    
    def test_read_state_handles_permission_errors(self):
        """Test that read_state gracefully handles permission errors."""
        mock_fm = Mock()
        mock_fm.read_for_agent.side_effect = ValueError("No permission")
        
        agent = MockAgent("test_agent", "test", mock_fm)
        state = agent.read_state()
        
        # Should return empty dict, not crash
        assert state == {}
    
    def test_create_response_helper(self):
        """Test create_response helper method."""
        mock_fm = Mock()
        agent = MockAgent("debator_a", "debator", mock_fm)
        
        response = agent.create_response(
            success=True,
            output={"statement": "test"},
            file_updates=[],
            errors=["minor error"],
            metadata={"info": "test"}
        )
        
        assert response.agent_name == "debator_a"
        assert response.success is True
        assert response.output["statement"] == "test"
        assert response.errors == ["minor error"]
        assert response.metadata["info"] == "test"
    
    def test_create_response_defaults(self):
        """Test create_response with minimal arguments."""
        mock_fm = Mock()
        agent = MockAgent("test", "test", mock_fm)
        
        response = agent.create_response(success=True, output={})
        
        assert response.file_updates == []
        assert response.errors == []
        assert response.metadata == {}
    
    @pytest.mark.asyncio
    async def test_execute_turn_abstract_method(self):
        """Test that execute_turn works in concrete implementation."""
        mock_fm = Mock()
        agent = MockAgent("test", "test", mock_fm)
        
        context = AgentContext(
            debate_id="test",
            topic="test",
            phase="opening",
            round_number=1,
            current_state={},
            instructions="test"
        )
        
        response = await agent.execute_turn(context)
        
        assert isinstance(response, AgentResponse)
        assert response.success is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
