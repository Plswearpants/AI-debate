"""
Unit tests for FileManager.

Tests cover:
- Permission-based filtering
- Atomic write operations
- Citation key generation
- File operations (read/write/append/update)
- Error handling
"""

import pytest
import json
from pathlib import Path
from datetime import datetime

from src.utils.file_manager import FileManager, PERMISSIONS


@pytest.fixture
def temp_debate_dir(tmp_path):
    """Create a temporary debate directory."""
    debate_dir = tmp_path / "test_debate"
    debate_dir.mkdir()
    return debate_dir


@pytest.fixture
def file_manager(temp_debate_dir):
    """Create a FileManager instance."""
    return FileManager(str(temp_debate_dir))


class TestInitialization:
    """Test FileManager initialization."""
    
    def test_creates_debate_directory(self, tmp_path):
        """Test that FileManager creates the debate directory."""
        debate_dir = tmp_path / "new_debate"
        assert not debate_dir.exists()
        
        fm = FileManager(str(debate_dir))
        assert debate_dir.exists()
    
    def test_initializes_files(self, file_manager, temp_debate_dir):
        """Test that initialize_files creates all required files."""
        debate_id = "test_123"
        topic = "Should we test?"
        
        file_manager.initialize_files(debate_id, topic)
        
        # Check all files exist
        assert (temp_debate_dir / "history_chat.json").exists()
        assert (temp_debate_dir / "citation_pool.json").exists()
        assert (temp_debate_dir / "debate_latent.json").exists()
        assert (temp_debate_dir / "crowd_opinion.json").exists()
        
        # Check history_chat structure
        history = file_manager._read_json("history_chat")
        assert history["debate_id"] == debate_id
        assert history["topic"] == topic
        assert "metadata" in history
        assert "public_transcript" in history
        assert "team_notes" in history
        assert "a" in history["team_notes"]
        assert "b" in history["team_notes"]


class TestPermissionFiltering:
    """Test permission-based filtering."""
    
    def test_debator_a_sees_own_team_notes(self, file_manager):
        """Test that debator_a can see team a notes but not team b."""
        file_manager.initialize_files("test", "test topic")
        
        # Add data
        data = file_manager._read_json("history_chat")
        data["team_notes"]["a"] = [{"material": "secret_a"}]
        data["team_notes"]["b"] = [{"material": "secret_b"}]
        file_manager.write_by_moderator("history_chat", data)
        
        # Read as debator_a
        filtered = file_manager.read_for_agent("debator_a", "history_chat")
        
        assert "team_notes" in filtered
        assert "a" in filtered["team_notes"]
        assert "b" not in filtered["team_notes"]
        assert filtered["team_notes"]["a"][0]["material"] == "secret_a"
    
    def test_debator_b_sees_own_team_notes(self, file_manager):
        """Test that debator_b can see team b notes but not team a."""
        file_manager.initialize_files("test", "test topic")
        
        # Add data
        data = file_manager._read_json("history_chat")
        data["team_notes"]["a"] = [{"material": "secret_a"}]
        data["team_notes"]["b"] = [{"material": "secret_b"}]
        file_manager.write_by_moderator("history_chat", data)
        
        # Read as debator_b
        filtered = file_manager.read_for_agent("debator_b", "history_chat")
        
        assert "team_notes" in filtered
        assert "b" in filtered["team_notes"]
        assert "a" not in filtered["team_notes"]
        assert filtered["team_notes"]["b"][0]["material"] == "secret_b"
    
    def test_judge_only_sees_public_transcript(self, file_manager):
        """Test that judge can only see public transcript, not team notes."""
        file_manager.initialize_files("test", "test topic")
        
        # Add data
        data = file_manager._read_json("history_chat")
        data["public_transcript"] = [{"statement": "public"}]
        data["team_notes"]["a"] = [{"material": "secret_a"}]
        data["team_notes"]["b"] = [{"material": "secret_b"}]
        file_manager.write_by_moderator("history_chat", data)
        
        # Read as judge
        filtered = file_manager.read_for_agent("judge", "history_chat")
        
        assert "public_transcript" in filtered
        assert len(filtered["public_transcript"]) == 1
        assert filtered["public_transcript"][0]["statement"] == "public"
        # Team notes should either not exist or be empty
        assert "team_notes" not in filtered or not filtered["team_notes"]
    
    def test_moderator_sees_everything(self, file_manager):
        """Test that moderator can see all data."""
        file_manager.initialize_files("test", "test topic")
        
        # Add data
        data = file_manager._read_json("history_chat")
        data["public_transcript"] = [{"statement": "public"}]
        data["team_notes"]["a"] = [{"material": "secret_a"}]
        data["team_notes"]["b"] = [{"material": "secret_b"}]
        file_manager.write_by_moderator("history_chat", data)
        
        # Read as moderator
        filtered = file_manager.read_for_agent("moderator", "history_chat")
        
        assert "public_transcript" in filtered
        assert "team_notes" in filtered
        assert "a" in filtered["team_notes"]
        assert "b" in filtered["team_notes"]
    
    def test_crowd_cannot_see_crowd_opinion(self, file_manager):
        """Test that crowd agents cannot read crowd_opinion file."""
        file_manager.initialize_files("test", "test topic")
        
        # Crowd has empty permissions for crowd_opinion
        filtered = file_manager.read_for_agent("crowd", "crowd_opinion")
        
        # Should return empty dict (no access)
        assert filtered == {}
    
    def test_invalid_agent_raises_error(self, file_manager):
        """Test that invalid agent name raises ValueError."""
        file_manager.initialize_files("test", "test topic")
        
        with pytest.raises(ValueError, match="Unknown agent"):
            file_manager.read_for_agent("invalid_agent", "history_chat")
    
    def test_invalid_file_type_raises_error(self, file_manager):
        """Test that invalid file type raises ValueError."""
        with pytest.raises(ValueError, match="Invalid file type"):
            file_manager.read_for_agent("debator_a", "invalid_file")


class TestCitationManagement:
    """Test citation-related functionality."""
    
    def test_generate_citation_key_sequential(self, file_manager):
        """Test that citation keys are generated sequentially."""
        key1 = file_manager.generate_citation_key("a")
        key2 = file_manager.generate_citation_key("a")
        key3 = file_manager.generate_citation_key("b")
        key4 = file_manager.generate_citation_key("a")
        
        assert key1 == "a_1"
        assert key2 == "a_2"
        assert key3 == "b_1"
        assert key4 == "a_3"
    
    def test_add_citation(self, file_manager):
        """Test adding a citation to the pool."""
        file_manager.initialize_files("test", "test topic")
        
        citation_data = {
            "source_url": "http://example.com",
            "added_by": "debator_a",
            "added_in_turn": "turn_001",
            "added_in_round": 1,
            "added_at": datetime.now().isoformat()
        }
        
        file_manager.add_citation("a", "a_1", citation_data)
        
        # Verify citation was added
        pool = file_manager._read_json("citation_pool")
        assert "team a" in pool["citations"]
        assert "a_1" in pool["citations"]["team a"]
        assert pool["citations"]["team a"]["a_1"]["source_url"] == "http://example.com"
        
        # Verify verification structure was initialized
        assert "verification" in pool["citations"]["team a"]["a_1"]
        assert pool["citations"]["team a"]["a_1"]["verification"]["source_credibility_score"] is None
    
    def test_add_citation_updates_round_index(self, file_manager):
        """Test that adding citation updates the round index."""
        file_manager.initialize_files("test", "test topic")
        
        citation_data = {
            "source_url": "http://example.com",
            "added_by": "debator_a",
            "added_in_turn": "turn_001",
            "added_in_round": 1,
            "added_at": datetime.now().isoformat()
        }
        
        file_manager.add_citation("a", "a_1", citation_data)
        
        pool = file_manager._read_json("citation_pool")
        assert "1" in pool["index_by_round"]
        assert "a_1" in pool["index_by_round"]["1"]
    
    def test_update_verification(self, file_manager):
        """Test updating verification scores."""
        file_manager.initialize_files("test", "test topic")
        
        # Add citation
        citation_data = {
            "source_url": "http://example.com",
            "added_by": "debator_a",
            "added_in_turn": "turn_001",
            "added_in_round": 1
        }
        file_manager.add_citation("a", "a_1", citation_data)
        
        # Update verification
        verification = {
            "source_credibility_score": 8,
            "content_correspondence_score": 9,
            "adversary_comment": "Good source",
            "verified_by": "factchecker_b",
            "verified_at": datetime.now().isoformat()
        }
        file_manager.update_verification("a", "a_1", verification)
        
        # Verify update
        pool = file_manager._read_json("citation_pool")
        ver = pool["citations"]["team a"]["a_1"]["verification"]
        assert ver["source_credibility_score"] == 8
        assert ver["content_correspondence_score"] == 9
        assert ver["adversary_comment"] == "Good source"
        assert ver["verified_by"] == "factchecker_b"
    
    def test_update_verification_nonexistent_citation_raises_error(self, file_manager):
        """Test that updating nonexistent citation raises ValueError."""
        file_manager.initialize_files("test", "test topic")
        
        verification = {"source_credibility_score": 8}
        
        with pytest.raises(ValueError, match="Citation .* not found"):
            file_manager.update_verification("a", "a_999", verification)


class TestFileOperations:
    """Test file read/write/append operations."""
    
    def test_atomic_write(self, file_manager, temp_debate_dir):
        """Test that writes are atomic (temp file is used)."""
        file_manager.initialize_files("test", "test topic")
        
        data = {"test": "data"}
        file_manager.write_by_moderator("history_chat", data)
        
        # Temp file should not exist after successful write
        temp_file = temp_debate_dir / "history_chat.json.tmp"
        assert not temp_file.exists()
        
        # Data should be written
        written_data = file_manager._read_json("history_chat")
        assert written_data["test"] == "data"
    
    def test_append_turn_to_public_transcript(self, file_manager):
        """Test appending a turn with statement to public transcript."""
        file_manager.initialize_files("test", "test topic")
        
        turn_data = {
            "turn_id": "turn_001",
            "speaker": "a",
            "agent": "debator_a",
            "statement": "My argument...",
            "citations_used": ["a_1", "a_2"]
        }
        
        file_manager.append_turn("a", turn_data)
        
        history = file_manager._read_json("history_chat")
        assert len(history["public_transcript"]) == 1
        assert history["public_transcript"][0]["statement"] == "My argument..."
    
    def test_append_supplementary_material_to_team_notes(self, file_manager):
        """Test appending supplementary material to team notes."""
        file_manager.initialize_files("test", "test topic")
        
        turn_data = {
            "turn_id": "turn_001",
            "supplementary_material": "Internal notes...",
            "citations_used": ["a_11"]
        }
        
        file_manager.append_turn("a", turn_data)
        
        history = file_manager._read_json("history_chat")
        assert len(history["team_notes"]["a"]) == 1
        assert history["team_notes"]["a"][0]["supplementary_material"] == "Internal notes..."
    
    def test_read_nonexistent_file_returns_empty_dict(self, file_manager):
        """Test that reading nonexistent file returns empty dict."""
        result = file_manager._read_json("history_chat")
        assert result == {}
    
    def test_file_path_method(self, file_manager, temp_debate_dir):
        """Test file_path method returns correct path."""
        path = file_manager.file_path("history_chat")
        assert path == temp_debate_dir / "history_chat.json"


class TestCitationPoolFiltering:
    """Test citation pool permission filtering."""
    
    def test_debators_see_all_citations(self, file_manager):
        """Test that debators can see both teams' citations."""
        file_manager.initialize_files("test", "test topic")
        
        # Add citations for both teams
        file_manager.add_citation("a", "a_1", {"source_url": "http://a.com", "added_in_round": 1})
        file_manager.add_citation("b", "b_1", {"source_url": "http://b.com", "added_in_round": 1})
        
        # Read as debator_a
        filtered = file_manager.read_for_agent("debator_a", "citation_pool")
        
        assert "team a" in filtered["citations"]
        assert "team b" in filtered["citations"]
        assert "a_1" in filtered["citations"]["team a"]
        assert "b_1" in filtered["citations"]["team b"]
    
    def test_crowd_cannot_see_citations(self, file_manager):
        """Test that crowd has no access to citation_pool."""
        file_manager.initialize_files("test", "test topic")
        
        file_manager.add_citation("a", "a_1", {"source_url": "http://a.com", "added_in_round": 1})
        
        # Read as crowd
        filtered = file_manager.read_for_agent("crowd", "citation_pool")
        
        # Should return empty (no permissions)
        assert filtered == {}


class TestThreadSafety:
    """Test thread safety of citation counter."""
    
    def test_citation_counter_thread_safe(self, file_manager):
        """Test that citation counter is thread-safe."""
        import threading
        
        keys = []
        
        def generate_keys():
            for _ in range(10):
                key = file_manager.generate_citation_key("a")
                keys.append(key)
        
        # Create multiple threads generating keys
        threads = [threading.Thread(target=generate_keys) for _ in range(5)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        
        # All keys should be unique
        assert len(keys) == 50  # 5 threads × 10 keys
        assert len(set(keys)) == 50  # All unique
        
        # Keys should be in format a_1 through a_50
        expected = {f"a_{i}" for i in range(1, 51)}
        assert set(keys) == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
