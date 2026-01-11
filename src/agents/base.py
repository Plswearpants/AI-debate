"""
Agent Base Classes - Abstract base class and data structures for all agents.

This module provides:
- Agent abstract base class
- AgentContext (input to agents)
- AgentResponse (output from agents)
- FileUpdate (represents file operations)
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from enum import Enum


class FileUpdateOperation(Enum):
    """Types of file update operations."""
    APPEND_TURN = "append_turn"
    ADD_CITATION = "add_citation"
    UPDATE_VERIFICATION = "update_verification"
    UPDATE_DEBATE_LATENT = "update_debate_latent"
    ADD_CROWD_VOTE = "add_crowd_vote"


@dataclass
class FileUpdate:
    """Represents a file update operation."""
    file_type: str  # "history_chat", "citation_pool", etc.
    operation: FileUpdateOperation
    data: Dict[str, Any]
    path: Optional[List[str]] = None  # Path within JSON (e.g., ["team_notes", "a"])


@dataclass
class AgentContext:
    """Context passed to agent for each turn."""
    debate_id: str
    topic: str
    phase: str  # "opening", "rebuttal", "closing"
    round_number: int
    current_state: Dict[str, Any]  # Filtered state from files
    instructions: str  # Specific instructions for this turn
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentResponse:
    """Response from agent after executing a turn."""
    agent_name: str
    success: bool
    output: Dict[str, Any]  # Main output (statement, scores, analysis, etc.)
    file_updates: List[FileUpdate] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class Agent(ABC):
    """Abstract base class for all agents."""
    
    def __init__(self, name: str, role: str, file_manager):
        """
        Initialize agent.
        
        Args:
            name: Agent name (e.g., "debator_a", "judge")
            role: Agent role (e.g., "debator", "factchecker", "judge", "crowd")
            file_manager: FileManager instance for reading state
        """
        self.name = name
        self.role = role
        self.file_manager = file_manager
    
    @abstractmethod
    async def execute_turn(self, context: AgentContext) -> AgentResponse:
        """
        Execute agent's turn.
        
        Args:
            context: Contains current state, instructions, metadata
        
        Returns:
            Response containing output and file updates
        """
        pass
    
    def read_state(self) -> Dict[str, Any]:
        """
        Read current state from files (permission-filtered).
        
        Returns:
            Dictionary with filtered data from all files agent can access
        """
        state = {}
        
        # Try to read each file type
        file_types = ["history_chat", "citation_pool", "debate_latent", "crowd_opinion"]
        
        for file_type in file_types:
            try:
                data = self.file_manager.read_for_agent(self.name, file_type)
                if data:  # Only include if agent has access
                    state[file_type] = data
            except (ValueError, FileNotFoundError):
                # Agent doesn't have access to this file
                pass
        
        return state
    
    def create_response(
        self,
        success: bool,
        output: Dict[str, Any],
        file_updates: Optional[List[FileUpdate]] = None,
        errors: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> AgentResponse:
        """
        Helper method to create AgentResponse.
        
        Args:
            success: Whether the turn was successful
            output: Main output from the agent
            file_updates: List of file updates to apply
            errors: List of error messages
            metadata: Additional metadata
        
        Returns:
            AgentResponse object
        """
        return AgentResponse(
            agent_name=self.name,
            success=success,
            output=output,
            file_updates=file_updates or [],
            errors=errors or [],
            metadata=metadata or {}
        )
