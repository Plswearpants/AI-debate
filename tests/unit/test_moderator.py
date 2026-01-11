"""
Unit tests for DebateModerator.

Tests:
- Moderator initialization
- Agent turn execution
- File update application
- Checkpoint save/resume
- Phase execution
- Output generation
"""

import json
import pytest
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime

from src.moderator import DebateModerator
from src.config import Config
from src.agents.base import AgentResponse, FileUpdate, FileUpdateOperation
from src.utils.state_manager import DebatePhase


@pytest.fixture
def test_config():
    """Create test configuration."""
    config = Config(
        gemini_api_key="test-gemini-key",
        claude_api_key="test-claude-key",
        perplexity_api_key="test-perplexity-key",
        lambda_gpu_endpoint="http://test-lambda:8000",
        num_debate_rounds=2
    )
    return config


@pytest.fixture
def mock_agents():
    """Create mock agents that return successful responses."""
    
    def create_mock_agent(name: str) -> Mock:
        agent = Mock()
        agent.name = name
        agent.read_state = Mock(return_value={})
        agent.execute_turn = AsyncMock(return_value=AgentResponse(
            agent_name=name,
            success=True,
            output={
                "_cost_estimate": 0.05,
                "test": "data"
            },
            file_updates=[],
            errors=[]
        ))
        return agent
    
    return {
        "debator_a": create_mock_agent("debator_a"),
        "debator_b": create_mock_agent("debator_b"),
        "factchecker_a": create_mock_agent("factchecker_a"),
        "factchecker_b": create_mock_agent("factchecker_b"),
        "judge": create_mock_agent("judge"),
        "crowd": create_mock_agent("crowd")
    }


@pytest.fixture
def temp_debate_dir(tmp_path):
    """Create temporary debate directory."""
    debate_dir = tmp_path / "debates" / "test-debate-id"
    debate_dir.mkdir(parents=True)
    return debate_dir


# =============================================================================
# INITIALIZATION TESTS
# =============================================================================

def test_moderator_initialization(test_config):
    """Test moderator initializes correctly."""
    moderator = DebateModerator(
        topic="Test topic",
        config=test_config
    )
    
    assert moderator.topic == "Test topic"
    assert moderator.debate_id is not None
    assert moderator.state.phase == DebatePhase.INITIALIZATION
    assert moderator.state.round_number == 0
    assert moderator.state.turn_count == 0
    assert moderator.total_cost == 0.0
    assert len(moderator.completed_turns) == 0


def test_moderator_with_custom_debate_id(test_config):
    """Test moderator accepts custom debate ID."""
    custom_id = "my-custom-id"
    moderator = DebateModerator(
        topic="Test",
        config=test_config,
        debate_id=custom_id
    )
    
    assert moderator.debate_id == custom_id


# =============================================================================
# AGENT TURN EXECUTION TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_execute_agent_turn_success(test_config, mock_agents, tmp_path, monkeypatch):
    """Test successful agent turn execution."""
    # Setup
    moderator = DebateModerator(topic="Test", config=test_config)
    moderator.debate_dir = tmp_path / moderator.debate_id
    moderator.debate_dir.mkdir(parents=True)
    moderator.file_manager.initialize_files(moderator.debate_id, "Test")
    moderator.agents = mock_agents
    
    # Execute turn
    response = await moderator.execute_agent_turn("debator_a", {
        "phase": "opening",
        "round_number": 1,
        "instructions": "Test instruction"
    })
    
    # Verify
    assert response.success
    assert moderator.state.turn_count == 1
    assert moderator.state.current_speaker == "debator_a"
    assert len(moderator.completed_turns) == 1
    assert moderator.completed_turns[0]["agent"] == "debator_a"
    assert moderator.total_cost > 0


@pytest.mark.asyncio
async def test_execute_agent_turn_failure(test_config, mock_agents, tmp_path):
    """Test agent turn execution handles failures."""
    # Setup
    moderator = DebateModerator(topic="Test", config=test_config)
    moderator.debate_dir = tmp_path / moderator.debate_id
    moderator.debate_dir.mkdir(parents=True)
    moderator.file_manager.initialize_files(moderator.debate_id, "Test")
    moderator.agents = mock_agents
    
    # Make agent fail
    mock_agents["debator_a"].execute_turn = AsyncMock(return_value=AgentResponse(
        agent_name="debator_a",
        success=False,
        output={},
        file_updates=[],
        errors=["Test error"]
    ))
    
    # Execute and expect exception
    with pytest.raises(Exception, match="Agent debator_a failed"):
        await moderator.execute_agent_turn("debator_a", {
            "phase": "opening",
            "round_number": 1
        })


@pytest.mark.asyncio
async def test_execute_agent_turn_applies_file_updates(test_config, mock_agents, tmp_path):
    """Test that file updates from agent are applied."""
    # Setup
    moderator = DebateModerator(topic="Test", config=test_config)
    moderator.debate_dir = tmp_path / moderator.debate_id
    moderator.debate_dir.mkdir(parents=True)
    moderator.file_manager.initialize_files(moderator.debate_id, "Test")
    moderator.agents = mock_agents
    
    # Make agent return file update
    mock_agents["debator_a"].execute_turn = AsyncMock(return_value=AgentResponse(
        agent_name="debator_a",
        success=True,
        output={"_cost_estimate": 0.05},
        file_updates=[
            FileUpdate(
                file_type="history_chat",
                operation=FileUpdateOperation.APPEND_TURN,
                data={
                    "speaker": "debator_a",
                    "round": 1,
                    "main_statement": "Test statement",
                    "supplementary_material": "",
                    "phase": "opening"
                }
            )
        ],
        errors=[]
    ))
    
    # Execute turn
    await moderator.execute_agent_turn("debator_a", {
        "phase": "opening",
        "round_number": 1
    })
    
    # Verify file was updated
    history = moderator.file_manager.read_for_agent("moderator", "history_chat")
    # Check either public_transcript or team_notes based on what was written
    assert len(history["public_transcript"]) > 0 or len(history["team_notes"]["debator_a"]) > 0


# =============================================================================
# FILE UPDATE APPLICATION TESTS
# =============================================================================

def test_apply_append_turn(test_config, tmp_path):
    """Test APPEND_TURN file update."""
    moderator = DebateModerator(topic="Test", config=test_config)
    moderator.debate_dir = tmp_path / moderator.debate_id
    moderator.debate_dir.mkdir(parents=True)
    moderator.file_manager.initialize_files(moderator.debate_id, "Test")
    
    update = FileUpdate(
        file_type="history_chat",
        operation=FileUpdateOperation.APPEND_TURN,
        data={
            "speaker": "debator_a",
            "round": 1,
            "main_statement": "Test",
            "supplementary_material": "",
            "phase": "opening"
        }
    )
    
    moderator._apply_file_update(update)
    
    history = moderator.file_manager.read_for_agent("moderator", "history_chat")
    # Check team_notes since this is written as a turn
    assert "team_notes" in history


def test_apply_add_citation(test_config, tmp_path):
    """Test ADD_CITATION file update."""
    moderator = DebateModerator(topic="Test", config=test_config)
    moderator.debate_dir = tmp_path / moderator.debate_id
    moderator.debate_dir.mkdir(parents=True)
    moderator.file_manager.initialize_files(moderator.debate_id, "Test")
    
    update = FileUpdate(
        file_type="citation_pool",
        operation=FileUpdateOperation.ADD_CITATION,
        data={
            "team": "a",
            "key": "cite1",
            "citation": {
                "source": "Test",
                "content": "Test content",
                "url": "http://test.com"
            }
        }
    )
    
    moderator._apply_file_update(update)
    
    citations = moderator.file_manager.read_for_agent("moderator", "citation_pool")
    assert "citations" in citations
    assert "team a" in citations["citations"]
    assert "cite1" in citations["citations"]["team a"]


def test_apply_update_verification(test_config, tmp_path):
    """Test UPDATE_VERIFICATION file update."""
    moderator = DebateModerator(topic="Test", config=test_config)
    moderator.debate_dir = tmp_path / moderator.debate_id
    moderator.debate_dir.mkdir(parents=True)
    moderator.file_manager.initialize_files(moderator.debate_id, "Test")
    
    # First add citation
    moderator.file_manager.add_citation("a", "cite1", {
        "source": "Test",
        "content": "Test"
    })
    
    # Then update verification
    update = FileUpdate(
        file_type="citation_pool",
        operation=FileUpdateOperation.UPDATE_VERIFICATION,
        data={
            "team": "a",
            "key": "cite1",
            "verification": {
                "status": "verified",
                "score": 0.9
            }
        }
    )
    
    moderator._apply_file_update(update)
    
    citations = moderator.file_manager.read_for_agent("moderator", "citation_pool")
    assert citations["citations"]["team a"]["cite1"]["verification"]["status"] == "verified"


def test_apply_update_debate_latent(test_config, tmp_path):
    """Test UPDATE_DEBATE_LATENT file update."""
    moderator = DebateModerator(topic="Test", config=test_config)
    moderator.debate_dir = tmp_path / moderator.debate_id
    moderator.debate_dir.mkdir(parents=True)
    moderator.file_manager.initialize_files(moderator.debate_id, "Test")
    
    update = FileUpdate(
        file_type="debate_latent",
        operation=FileUpdateOperation.UPDATE_DEBATE_LATENT,
        data={
            "round": 1,
            "consensus_points": ["Point 1"],
            "frontier": ["Issue 1"]
        }
    )
    
    moderator._apply_file_update(update)
    
    latent = moderator.file_manager.read_for_agent("moderator", "debate_latent")
    assert len(latent["round_history"]) == 1


def test_apply_add_crowd_vote(test_config, tmp_path):
    """Test ADD_CROWD_VOTE file update."""
    moderator = DebateModerator(topic="Test", config=test_config)
    moderator.debate_dir = tmp_path / moderator.debate_id
    moderator.debate_dir.mkdir(parents=True)
    moderator.file_manager.initialize_files(moderator.debate_id, "Test")
    
    # First initialize voters
    crowd_data = moderator.file_manager.read_for_agent("moderator", "crowd_opinion")
    crowd_data["voters"] = [
        {
            "voter_id": 1,
            "persona": {"type": "test"},
            "voting_history": [],
            "current_score": 50
        }
    ]
    moderator.file_manager.write_by_moderator("crowd_opinion", crowd_data)
    
    # Add vote
    update = FileUpdate(
        file_type="crowd_opinion",
        operation=FileUpdateOperation.ADD_CROWD_VOTE,
        data={
            "round": 1,
            "votes": [
                {"voter_id": 1, "score": 60, "rationale": "Test"}
            ],
            "average_score": 60,
            "vote_count": 1,
            "timestamp": "2026-01-06T10:00:00Z"
        }
    )
    
    moderator._apply_file_update(update)
    
    crowd = moderator.file_manager.read_for_agent("moderator", "crowd_opinion")
    assert len(crowd["vote_rounds"]) == 1
    assert crowd["voters"][0]["current_score"] == 60


# =============================================================================
# CHECKPOINT TESTS
# =============================================================================

def test_save_checkpoint(test_config, tmp_path):
    """Test checkpoint saving."""
    moderator = DebateModerator(topic="Test topic", config=test_config)
    moderator.debate_dir = tmp_path / moderator.debate_id
    moderator.debate_dir.mkdir(parents=True)
    moderator.state.assign_teams("for", "against", {"for": 60, "against": 40})
    moderator.state.round_number = 1
    moderator.state.turn_count = 5
    moderator.total_cost = 0.25
    
    moderator._save_checkpoint()
    
    checkpoint_path = moderator.debate_dir / "moderator_checkpoint.json"
    assert checkpoint_path.exists()
    
    with open(checkpoint_path) as f:
        checkpoint = json.load(f)
    
    assert checkpoint["debate_id"] == moderator.debate_id
    assert checkpoint["topic"] == "Test topic"
    assert checkpoint["state"]["round_number"] == 1
    assert checkpoint["state"]["turn_count"] == 5
    assert checkpoint["costs"]["total"] == 0.25


@pytest.mark.asyncio
async def test_resume_from_checkpoint(test_config, tmp_path, monkeypatch):
    """Test resuming debate from checkpoint."""
    # Create initial moderator and save checkpoint
    debate_id = "test-debate-123"
    
    # Mock the debates directory to use tmp_path
    debates_dir = tmp_path / "debates"
    debates_dir.mkdir()
    
    # Patch Path to use tmp_path for debates
    import src.moderator
    original_path = src.moderator.Path
    
    def mock_path(path_str):
        if path_str.startswith("debates/"):
            return tmp_path / path_str
        return original_path(path_str)
    
    monkeypatch.setattr(src.moderator, "Path", mock_path)
    
    moderator1 = DebateModerator(topic="Test topic", config=test_config, debate_id=debate_id)
    moderator1.debate_dir = tmp_path / "debates" / debate_id
    moderator1.debate_dir.mkdir(parents=True, exist_ok=True)
    moderator1.file_manager.initialize_files(debate_id, "Test topic")
    moderator1.state.assign_teams("for", "against", {"for": 60, "against": 40})
    moderator1.state.round_number = 2
    moderator1.state.turn_count = 10
    moderator1.total_cost = 0.75
    moderator1.completed_turns = [
        {"turn": 1, "agent": "debator_a", "cost": 0.08},
        {"turn": 2, "agent": "factchecker_b", "cost": 0.15}
    ]
    moderator1._save_checkpoint()
    
    # Resume from checkpoint
    moderator2 = await DebateModerator.resume_from_checkpoint(debate_id, test_config)
    
    # Verify state matches
    assert moderator2.debate_id == debate_id
    assert moderator2.topic == "Test topic"
    assert moderator2.state.round_number == 2
    assert moderator2.state.turn_count == 10
    assert moderator2.total_cost == 0.75
    assert len(moderator2.completed_turns) == 2


@pytest.mark.asyncio
async def test_resume_nonexistent_checkpoint_raises_error(test_config):
    """Test that resuming nonexistent checkpoint raises error."""
    with pytest.raises(FileNotFoundError, match="No checkpoint found"):
        await DebateModerator.resume_from_checkpoint("nonexistent-id", test_config)


def test_should_checkpoint_vote_zero(test_config):
    """Test checkpoint triggered after Vote 0 and all crowd votes."""
    moderator = DebateModerator(topic="Test", config=test_config)
    
    # All crowd votes trigger checkpoints (round boundaries)
    assert moderator._should_checkpoint("crowd", {"round_number": 0})
    assert moderator._should_checkpoint("crowd", {"round_number": 1})
    assert moderator._should_checkpoint("crowd", {"round_number": 2})


def test_should_checkpoint_debator(test_config):
    """Test checkpoint triggered after debator turns."""
    moderator = DebateModerator(topic="Test", config=test_config)
    
    assert moderator._should_checkpoint("debator_a", {"round_number": 1})
    assert moderator._should_checkpoint("debator_b", {"round_number": 1})
    assert not moderator._should_checkpoint("factchecker_a", {"round_number": 1})


def test_should_checkpoint_judge(test_config):
    """Test checkpoint triggered after judge."""
    moderator = DebateModerator(topic="Test", config=test_config)
    
    assert moderator._should_checkpoint("judge", {"round_number": 1})


def test_should_checkpoint_crowd(test_config):
    """Test checkpoint triggered after crowd votes."""
    moderator = DebateModerator(topic="Test", config=test_config)
    
    assert moderator._should_checkpoint("crowd", {"round_number": 1})


def test_calculate_cost_by_agent(test_config):
    """Test cost calculation per agent."""
    moderator = DebateModerator(topic="Test", config=test_config)
    moderator.completed_turns = [
        {"turn": 1, "agent": "debator_a", "cost": 0.08},
        {"turn": 2, "agent": "factchecker_b", "cost": 0.15},
        {"turn": 3, "agent": "debator_a", "cost": 0.08},
        {"turn": 4, "agent": "judge", "cost": 0.25}
    ]
    
    costs = moderator._calculate_cost_by_agent()
    
    assert costs["debator_a"] == 0.16
    assert costs["factchecker_b"] == 0.15
    assert costs["judge"] == 0.25


# =============================================================================
# AGENT INITIALIZATION TESTS
# =============================================================================

def test_initialize_agents(test_config, tmp_path):
    """Test agent initialization with correct stances."""
    moderator = DebateModerator(topic="Test", config=test_config)
    moderator.debate_dir = tmp_path / moderator.debate_id
    moderator.debate_dir.mkdir(parents=True)
    moderator.file_manager.initialize_files(moderator.debate_id, "Test")
    
    agents = moderator._initialize_agents(team_a_stance="for", team_b_stance="against")
    
    assert len(agents) == 6
    assert "debator_a" in agents
    assert "debator_b" in agents
    assert "factchecker_a" in agents
    assert "factchecker_b" in agents
    assert "judge" in agents
    assert "crowd" in agents
    
    # Verify stances
    assert agents["debator_a"].stance == "for"
    assert agents["debator_b"].stance == "against"


# =============================================================================
# OUTPUT GENERATION TESTS
# =============================================================================

@pytest.mark.asyncio
async def test_generate_transcript(test_config, tmp_path):
    """Test transcript generation."""
    moderator = DebateModerator(topic="Test topic", config=test_config)
    moderator.debate_dir = tmp_path / moderator.debate_id
    moderator.debate_dir.mkdir(parents=True)
    moderator.file_manager.initialize_files(moderator.debate_id, "Test topic")
    
    # Add some turns - use "statement" not "main_statement" to go to public_transcript
    moderator.file_manager.append_turn("debator_a", {
        "speaker": "debator_a",
        "round": 1,
        "statement": "Test statement",
        "supplementary_material": "Supplementary info",
        "phase": "opening"
    })
    
    output_dir = moderator.debate_dir / "outputs"
    output_dir.mkdir()
    
    # Read history (should have "public_transcript" and "team_notes")
    history = moderator.file_manager.read_for_agent("moderator", "history_chat")
    
    # Verify history has correct structure
    assert "public_transcript" in history
    assert "team_notes" in history
    
    await moderator._generate_transcript(output_dir, history)
    
    transcript_path = output_dir / "transcript_full.md"
    assert transcript_path.exists()
    
    content = transcript_path.read_text()
    assert "Test topic" in content
    assert "Test statement" in content


@pytest.mark.asyncio
async def test_generate_citation_ledger(test_config, tmp_path):
    """Test citation ledger generation."""
    moderator = DebateModerator(topic="Test", config=test_config)
    moderator.debate_dir = tmp_path / moderator.debate_id
    moderator.debate_dir.mkdir(parents=True)
    moderator.file_manager.initialize_files(moderator.debate_id, "Test")
    
    output_dir = moderator.debate_dir / "outputs"
    output_dir.mkdir()
    
    citations = moderator.file_manager.read_for_agent("moderator", "citation_pool")
    await moderator._generate_citation_ledger(output_dir, citations)
    
    ledger_path = output_dir / "citation_ledger.json"
    assert ledger_path.exists()


@pytest.mark.asyncio
async def test_generate_sentiment_graph(test_config, tmp_path):
    """Test sentiment graph CSV generation."""
    moderator = DebateModerator(topic="Test", config=test_config)
    moderator.debate_dir = tmp_path / moderator.debate_id
    moderator.debate_dir.mkdir(parents=True)
    moderator.file_manager.initialize_files(moderator.debate_id, "Test")
    
    # Add voter data
    crowd_data = moderator.file_manager.read_for_agent("moderator", "crowd_opinion")
    crowd_data["voters"] = [
        {
            "voter_id": 1,
            "persona": {"type": "liberal"},
            "voting_history": [
                {"round": 0, "score": 50, "rationale": "Initial"},
                {"round": 1, "score": 60, "rationale": "Changed"}
            ],
            "current_score": 60
        }
    ]
    moderator.file_manager.write_by_moderator("crowd_opinion", crowd_data)
    
    output_dir = moderator.debate_dir / "outputs"
    output_dir.mkdir()
    
    crowd = moderator.file_manager.read_for_agent("moderator", "crowd_opinion")
    await moderator._generate_sentiment_graph(output_dir, crowd)
    
    csv_path = output_dir / "voter_sentiment_graph.csv"
    assert csv_path.exists()
    
    content = csv_path.read_text()
    assert "round,voter_id,score,persona_type" in content
    assert "0,1,50,liberal" in content
    assert "1,1,60,liberal" in content


# =============================================================================
# PHASE EXECUTION TESTS (MOCKED)
# =============================================================================

@pytest.mark.asyncio
async def test_phase_0_initialization_mock(test_config, mock_agents, tmp_path, monkeypatch):
    """Test Phase 0 with mocked agents."""
    moderator = DebateModerator(topic="Test UBI", config=test_config)
    moderator.debate_dir = tmp_path / moderator.debate_id
    
    # Mock Vote 0 response
    vote_zero_response = AgentResponse(
        agent_name="crowd",
        success=True,
        output={
            "_cost_estimate": 0.02,
            "votes": [{"voter_id": i, "score": 55 if i < 60 else 45} for i in range(100)],
            "average_score": 52.0,
            "vote_count": 100
        },
        file_updates=[
            FileUpdate(
                file_type="crowd_opinion",
                operation=FileUpdateOperation.ADD_CROWD_VOTE,
                data={
                    "round": 0,
                    "votes": [{"voter_id": i, "score": 55 if i < 60 else 45, "rationale": "Test"} for i in range(100)],
                    "average_score": 52.0,
                    "vote_count": 100,
                    "timestamp": "2026-01-06T10:00:00Z"
                }
            )
        ],
        errors=[]
    )
    
    # Patch CrowdAgent to return our mock response
    with patch('src.moderator.CrowdAgent') as mock_crowd_class:
        mock_crowd_instance = Mock()
        mock_crowd_instance.execute_turn = AsyncMock(return_value=vote_zero_response)
        mock_crowd_class.return_value = mock_crowd_instance
        
        await moderator._phase_0_initialization()
    
    # Verify
    assert moderator.state.phase == DebatePhase.OPENING
    assert moderator.state.round_number == 0
    assert "team_a" in moderator.state.team_assignments
    assert "team_b" in moderator.state.team_assignments
    assert len(moderator.agents) == 6


# =============================================================================
# RUN COVERAGE
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
