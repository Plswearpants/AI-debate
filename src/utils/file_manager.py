"""
File Manager - Handles all file I/O with permission enforcement for the AI Debate Platform.

This module provides:
- Atomic read/write operations for JSON files
- Permission-based filtering of data per agent
- Citation management (generation, addition, updates)
- Thread-safe file operations
"""

import json
import os
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from threading import Lock


# Permission Matrix - defines what each agent can read
PERMISSIONS = {
    "debator_a": {
        "history_chat": ["public_transcript", "team_notes.a"],
        "citation_pool": ["team a", "team b"],
        "debate_latent": ["all"],
        "crowd_opinion": []
    },
    "debator_b": {
        "history_chat": ["public_transcript", "team_notes.b"],
        "citation_pool": ["team a", "team b"],
        "debate_latent": ["all"],
        "crowd_opinion": []
    },
    "factchecker_a": {
        "history_chat": ["public_transcript", "team_notes.a"],
        "citation_pool": ["team a", "team b"],
        "debate_latent": ["all"],
        "crowd_opinion": []
    },
    "factchecker_b": {
        "history_chat": ["public_transcript", "team_notes.b"],
        "citation_pool": ["team a", "team b"],
        "debate_latent": ["all"],
        "crowd_opinion": []
    },
    "judge": {
        "history_chat": ["public_transcript"],
        "citation_pool": ["team a", "team b"],
        "debate_latent": ["all"],
        "crowd_opinion": []
    },
    "crowd": {
        "history_chat": ["public_transcript"],
        "citation_pool": [],  # can change to "all" for future tests
        "debate_latent": ["all"],
        "crowd_opinion": []
    },
    "moderator": {
        "history_chat": ["all"],
        "citation_pool": ["all"],
        "debate_latent": ["all"],
        "crowd_opinion": ["all"]
    }
}


class FileManager:
    """Manages all file I/O operations with permission enforcement."""
    
    def __init__(self, debate_dir: str):
        """
        Initialize FileManager for a specific debate.
        
        Args:
            debate_dir: Path to the debate directory
        """
        self.debate_dir = Path(debate_dir)
        self.debate_dir.mkdir(parents=True, exist_ok=True)
        
        # Citation counters for sequential key generation
        self.citation_counters = {"a": 0, "b": 0}
        self.counter_lock = Lock()
        
        # File paths
        self.files = {
            "history_chat": self.debate_dir / "history_chat.json",
            "citation_pool": self.debate_dir / "citation_pool.json",
            "debate_latent": self.debate_dir / "debate_latent.json",
            "crowd_opinion": self.debate_dir / "crowd_opinion.json"
        }
    
    def initialize_files(self, debate_id: str, topic: str) -> None:
        """
        Initialize all JSON files with empty structures.
        
        Args:
            debate_id: Unique identifier for the debate
            topic: The debate topic
        """
        # Initialize history_chat.json
        history_chat = {
            "debate_id": debate_id,
            "topic": topic,
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "phase": "initialization",
                "current_round": 0
            },
            "public_transcript": [],
            "team_notes": {
                "a": [],
                "b": []
            }
        }
        self.write_by_moderator("history_chat", history_chat)
        
        # Initialize citation_pool.json
        citation_pool = {
            "debate_id": debate_id,
            "citations": {
                "team a": {},
                "team b": {}
            },
            "index_by_round": {}
        }
        self.write_by_moderator("citation_pool", citation_pool)
        
        # Initialize debate_latent.json
        debate_latent = {
            "debate_id": debate_id,
            "round_history": []
        }
        self.write_by_moderator("debate_latent", debate_latent)
        
        # Initialize crowd_opinion.json
        crowd_opinion = {
            "debate_id": debate_id,
            "voters": []
        }
        self.write_by_moderator("crowd_opinion", crowd_opinion)
    
    def read_for_agent(self, agent_name: str, file_type: str) -> Dict[str, Any]:
        """
        Read file with permission filtering for specific agent.
        
        Args:
            agent_name: Name of the agent (e.g., "debator_a", "judge")
            file_type: Type of file to read ("history_chat", "citation_pool", etc.)
        
        Returns:
            Filtered data based on agent permissions
        
        Raises:
            ValueError: If agent_name or file_type is invalid
            FileNotFoundError: If the file doesn't exist
        """
        if agent_name not in PERMISSIONS:
            raise ValueError(f"Unknown agent: {agent_name}")
        
        if file_type not in PERMISSIONS[agent_name]:
            raise ValueError(f"Invalid file type: {file_type}")
        
        # Read raw data
        data = self._read_json(file_type)
        
        # Apply permission filtering
        permissions = PERMISSIONS[agent_name][file_type]
        
        if "all" in permissions:
            return data
        
        if not permissions:  # Empty list means no access
            return {}
        
        # Filter based on specific permissions
        return self._filter_data(data, file_type, permissions)
    
    def write_by_moderator(self, file_type: str, data: Dict[str, Any]) -> None:
        """
        Write file (only moderator can write).
        
        Args:
            file_type: Type of file to write
            data: Complete data to write
        
        Raises:
            ValueError: If file_type is invalid
        """
        if file_type not in self.files:
            raise ValueError(f"Invalid file type: {file_type}")
        
        self._write_json(file_type, data)
    
    def append_turn(self, speaker: str, turn_data: Dict[str, Any]) -> None:
        """
        Append a turn to history_chat.
        
        Args:
            speaker: Team identifier ("a" or "b")
            turn_data: Turn data to append
        """
        data = self._read_json("history_chat")
        
        # Determine if this goes to public_transcript or team_notes
        if "statement" in turn_data:
            # Main statement goes to public transcript
            data["public_transcript"].append(turn_data)
        
        if "supplementary_material" in turn_data:
            # Supplementary material goes to team notes
            team_key = speaker.lower()
            if team_key not in data["team_notes"]:
                data["team_notes"][team_key] = []
            data["team_notes"][team_key].append(turn_data)
        
        self._write_json("history_chat", data)
    
    def generate_citation_key(self, team: str) -> str:
        """
        Generate sequential citation key for a team.
        
        Args:
            team: Team identifier ("a" or "b")
        
        Returns:
            Citation key (e.g., "a_1", "b_2")
        """
        with self.counter_lock:
            self.citation_counters[team] += 1
            return f"{team}_{self.citation_counters[team]}"
    
    def add_citation(self, team: str, citation_key: str, citation_data: Dict[str, Any]) -> None:
        """
        Add citation to citation_pool.
        
        Args:
            team: Team identifier ("a" or "b")
            citation_key: Citation key (e.g., "a_1")
            citation_data: Citation data
        """
        data = self._read_json("citation_pool")
        
        team_key = f"team {team}"
        if team_key not in data["citations"]:
            data["citations"][team_key] = {}
        
        # Initialize verification if not present
        if "verification" not in citation_data:
            citation_data["verification"] = {
                "source_credibility_score": None,
                "content_correspondence_score": None,
                "adversary_comment": None,
                "proponent_response": None,
                "verified_by": None,
                "verified_at": None
            }
        
        data["citations"][team_key][citation_key] = citation_data
        
        # Update round index
        round_num = str(citation_data.get("added_in_round", 0))
        if round_num not in data["index_by_round"]:
            data["index_by_round"][round_num] = []
        if citation_key not in data["index_by_round"][round_num]:
            data["index_by_round"][round_num].append(citation_key)
        
        self._write_json("citation_pool", data)
    
    def update_verification(self, team: str, citation_key: str, verification: Dict[str, Any]) -> None:
        """
        Update verification scores in citation_pool.
        
        Args:
            team: Team identifier ("a" or "b")
            citation_key: Citation key to update
            verification: Verification data
        """
        data = self._read_json("citation_pool")
        
        team_key = f"team {team}"
        if team_key in data["citations"] and citation_key in data["citations"][team_key]:
            data["citations"][team_key][citation_key]["verification"].update(verification)
            self._write_json("citation_pool", data)
        else:
            raise ValueError(f"Citation {citation_key} not found for {team_key}")
    
    def file_path(self, file_type: str) -> Path:
        """Get the file path for a given file type."""
        return self.files.get(file_type)
    
    # Private methods
    
    def _read_json(self, file_type: str) -> Dict[str, Any]:
        """Read JSON file."""
        file_path = self.files[file_type]
        
        if not file_path.exists():
            return {}
        
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _write_json(self, file_type: str, data: Dict[str, Any]) -> None:
        """Write JSON file atomically."""
        file_path = self.files[file_type]
        
        # Write to temporary file first
        temp_path = file_path.with_suffix('.tmp')
        
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomic rename
            temp_path.replace(file_path)
        except Exception as e:
            # Clean up temp file if something went wrong
            if temp_path.exists():
                temp_path.unlink()
            raise e
    
    def _filter_data(self, data: Dict[str, Any], file_type: str, permissions: List[str]) -> Dict[str, Any]:
        """Filter data based on permissions."""
        if file_type == "history_chat":
            return self._filter_history_chat(data, permissions)
        elif file_type == "citation_pool":
            return self._filter_citation_pool(data, permissions)
        else:
            # For other files, either all or nothing
            return data if permissions else {}
    
    def _filter_history_chat(self, data: Dict[str, Any], permissions: List[str]) -> Dict[str, Any]:
        """Filter history_chat based on permissions."""
        filtered = {
            "debate_id": data.get("debate_id"),
            "topic": data.get("topic"),
            "metadata": data.get("metadata")
        }
        
        if "public_transcript" in permissions:
            filtered["public_transcript"] = data.get("public_transcript", [])
        
        # Handle team notes
        filtered["team_notes"] = {}
        for perm in permissions:
            if perm.startswith("team_notes."):
                team = perm.split(".")[-1]
                if "team_notes" in data and team in data["team_notes"]:
                    filtered["team_notes"][team] = data["team_notes"][team]
        
        return filtered
    
    def _filter_citation_pool(self, data: Dict[str, Any], permissions: List[str]) -> Dict[str, Any]:
        """Filter citation_pool based on permissions."""
        filtered = {
            "debate_id": data.get("debate_id"),
            "citations": {}
        }
        
        for perm in permissions:
            # Permission already includes "team " prefix (e.g., "team a")
            if perm in data.get("citations", {}):
                filtered["citations"][perm] = data["citations"][perm]
        
        # Include round index if any citations are visible
        if filtered["citations"]:
            filtered["index_by_round"] = data.get("index_by_round", {})
        
        return filtered
