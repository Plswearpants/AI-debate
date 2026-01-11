# AI Debate Platform - Architecture Design

**Last Updated**: January 2026  
**Status**: Foundation Complete + Deep Research Integrated ✅  
**Tests**: 97/97 passing ✅

---

## 🚀 Major Update: Deep Research Integration

We now use **Gemini Deep Research Agent** (`deep-research-pro-preview-12-2025`) instead of custom MCP research, achieving **Gemini 3 Pro-level research quality**.

**Benefits**:
- ✅ Same quality as Gemini 3 Pro Deep Search
- ✅ Comprehensive multi-source analysis  
- ✅ Built-in citation handling
- ✅ Simpler architecture (~200 lines of code removed)

---

## Core Principles

1. **Separation of Concerns**: File I/O, agent logic, and orchestration are distinct layers
2. **Permission Enforcement**: File access strictly controlled by agent roles
3. **Immutable State**: Agents read state, moderator writes state
4. **Clear Contracts**: Well-defined interfaces between components
5. **Structured Output**: Use JSON schemas for deterministic parsing (Interactions API)

---

## Architecture Layers

```
┌─────────────────────────────────────────────────────────┐
│                    Moderator Layer                      │
│              (Orchestration & State Machine)            │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                 Communication Protocol                  │
│          (Agent Messages, Turn Management)              │
└─────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
┌─────────────────┐ ┌─────────────┐ ┌─────────────────┐
│  Agent Interface│ │File Manager │ │ State Manager   │
│     Layer       │ │   Layer     │ │    Layer        │
└─────────────────┘ └─────────────┘ └─────────────────┘
            │               │               │
            └───────────────┼───────────────┘
                            ▼
                  ┌──────────────────┐
                  │   JSON Files     │
                  └──────────────────┘
```

---

## 1. File Manager Layer

### Responsibilities
- Read/write JSON files atomically
- Enforce permission rules per agent
- Validate data schemas
- Handle file locking for concurrent access

### Interface

```python
class FileManager:
    """Handles all file I/O with permission enforcement"""
    
    def __init__(self, debate_dir: str):
        self.debate_dir = Path(debate_dir)
        self.permissions = PermissionMatrix()
    
    def read_for_agent(self, agent_name: str, file_type: str) -> dict:
        """
        Read file with permission filtering for specific agent
        
        Args:
            agent_name: e.g., "debator_a", "factchecker_b", "judge"
            file_type: e.g., "history_chat", "citation_pool"
        
        Returns:
            Filtered data based on agent permissions
        """
        pass
    
    def write_by_moderator(self, file_type: str, data: dict) -> None:
        """
        Write file (only moderator can write)
        
        Args:
            file_type: Type of file to write
            data: Complete data to write
        """
        pass
    
    def append_turn(self, speaker: str, turn_data: dict) -> None:
        """Append a turn to history_chat"""
        pass
    
    def add_citation(self, team: str, citation_key: str, citation_data: dict) -> None:
        """Add citation to citation_pool"""
        pass
    
    def update_verification(self, team: str, citation_key: str, verification: dict) -> None:
        """Update verification scores in citation_pool"""
        pass
```

### Permission Matrix

```python
PERMISSIONS = {
    "debator_a": {
        "history_chat": ["public_transcript", "team_notes.a"],  # Can read
        "citation_pool": ["team a", "team b"],  # Can read all, write team a
        "debate_latent": ["all"],
        "crowd_opinion": []  # Cannot read
    },
    "debator_b": {
        "history_chat": ["public_transcript", "team_notes.b"],
        "citation_pool": ["team a", "team b"],
        "debate_latent": ["all"],
        "crowd_opinion": []
    },
    "factchecker_a": {
        "history_chat": ["public_transcript", "team_notes.a"],
        "citation_pool": ["team a", "team b"],  # Can read all, write scores
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
        "history_chat": ["public_transcript"],  # No team notes
        "citation_pool": ["team a", "team b"],
        "debate_latent": ["all"],
        "crowd_opinion": []
    },
    "crowd": {
        "history_chat": ["public_transcript"],
        "citation_pool": [], # can change to "all" for future tests
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
```

---

## 2. Agent Interface Layer

### Agent Base Class

```python
from abc import ABC, abstractmethod
from typing import Dict, Any, List

class Agent(ABC):
    """Base class for all agents"""
    
    def __init__(self, name: str, role: str, file_manager: FileManager):
        self.name = name
        self.role = role
        self.file_manager = file_manager
    
    @abstractmethod
    async def execute_turn(self, context: AgentContext) -> AgentResponse:
        """
        Execute agent's turn
        
        Args:
            context: Contains current state, previous messages, etc.
        
        Returns:
            Response containing output and file updates
        """
        pass
    
    def read_state(self) -> Dict[str, Any]:
        """Read current state from files (permission-filtered)"""
        return {
            "history_chat": self.file_manager.read_for_agent(self.name, "history_chat"),
            "citation_pool": self.file_manager.read_for_agent(self.name, "citation_pool"),
            "debate_latent": self.file_manager.read_for_agent(self.name, "debate_latent"),
        }
```

### Agent Context

```python
@dataclass
class AgentContext:
    """Context passed to agent for each turn"""
    debate_id: str
    topic: str
    phase: str  # "opening", "rebuttal", "closing"
    round_number: int
    current_state: Dict[str, Any]  # Filtered state
    instructions: str  # Specific instructions for this turn
    metadata: Dict[str, Any]  # Additional metadata
```

### Agent Response

```python
@dataclass
class AgentResponse:
    """Response from agent after turn"""
    agent_name: str
    success: bool
    output: Dict[str, Any]  # Main output (statement, scores, etc.)
    file_updates: List[FileUpdate]  # What to update in files
    errors: List[str]
    metadata: Dict[str, Any]

@dataclass
class FileUpdate:
    """Represents a file update operation"""
    file_type: str  # "history_chat", "citation_pool", etc.
    operation: str  # "append", "update", "add_citation"
    data: Dict[str, Any]
    path: Optional[List[str]]  # Path within JSON (e.g., ["team_notes", "a"])
```

---

## 3. Agent-Agent Communication Protocol

### Message Passing Architecture

```python
@dataclass
class AgentMessage:
    """Message passed between agents (via moderator)"""
    from_agent: str
    to_agent: str
    message_type: str  # "statement", "verification", "analysis", "vote"
    content: Dict[str, Any]
    timestamp: str
    metadata: Dict[str, Any]

class MessageBus:
    """Manages messages between agents"""
    
    def __init__(self):
        self.message_queue: List[AgentMessage] = []
    
    def send_message(self, message: AgentMessage) -> None:
        """Send message (actually just logs it)"""
        self.message_queue.append(message)
    
    def get_messages_for(self, agent_name: str) -> List[AgentMessage]:
        """Get all messages for specific agent"""
        return [m for m in self.message_queue if m.to_agent == agent_name]
```

### Turn Execution Flow

```
1. Moderator prepares context for Agent X
   ├─ Read current state (permission-filtered)
   ├─ Get relevant messages from MessageBus
   └─ Create AgentContext

2. Agent X executes turn
   ├─ Read state via file_manager
   ├─ Process with LLM
   ├─ Generate output
   └─ Return AgentResponse with file updates

3. Moderator processes response
   ├─ Validate response
   ├─ Apply file updates via file_manager
   ├─ Send messages to other agents
   └─ Update state machine

4. Repeat for next agent
```

---

## 4. State Manager Layer

### Responsibilities
- Track debate state (phase, round, turn)
- Manage state transitions
- Validate state changes

```python
from enum import Enum
from typing import Optional

class DebatePhase(Enum):
    INITIALIZATION = "initialization"
    OPENING = "opening"
    DEBATE_ROUNDS = "debate_rounds"
    CLOSING = "closing"
    COMPLETED = "completed"

class DebateState:
    """Tracks current debate state"""
    
    def __init__(self, debate_id: str, topic: str):
        self.debate_id = debate_id
        self.topic = topic
        self.phase = DebatePhase.INITIALIZATION
        self.round_number = 0
        self.turn_count = 0
        self.current_speaker: Optional[str] = None
        self.team_assignments = {}  # {stance: team}
        self.resource_multiplier = 1.0
    
    def transition_to(self, new_phase: DebatePhase) -> None:
        """Transition to new phase with validation"""
        valid_transitions = {
            DebatePhase.INITIALIZATION: [DebatePhase.OPENING],
            DebatePhase.OPENING: [DebatePhase.DEBATE_ROUNDS],
            DebatePhase.DEBATE_ROUNDS: [DebatePhase.CLOSING],
            DebatePhase.CLOSING: [DebatePhase.COMPLETED],
        }
        
        if new_phase not in valid_transitions.get(self.phase, []):
            raise InvalidStateTransition(f"Cannot transition from {self.phase} to {new_phase}")
        
        self.phase = new_phase
    
    def next_turn(self, speaker: str) -> None:
        """Advance to next turn"""
        self.current_speaker = speaker
        self.turn_count += 1
    
    def next_round(self) -> None:
        """Advance to next round"""
        self.round_number += 1
```

---

## 5. Integration: Putting It All Together

### Moderator Implementation

```python
class DebateModerator:
    """Orchestrates the entire debate"""
    
    def __init__(self, topic: str, config: Config):
        self.debate_id = str(uuid.uuid4())
        self.topic = topic
        self.config = config
        
        # Initialize layers
        self.debate_dir = Path(f"debates/{self.debate_id}")
        self.file_manager = FileManager(self.debate_dir)
        self.state = DebateState(self.debate_id, topic)
        self.message_bus = MessageBus()
        
        # Initialize agents
        self.agents = self._initialize_agents()
    
    def _initialize_agents(self) -> Dict[str, Agent]:
        """Create all agent instances"""
        return {
            "debator_a": DebatorAgent("debator_a", "a", self.file_manager, self.config),
            "debator_b": DebatorAgent("debator_b", "b", self.file_manager, self.config),
            "factchecker_a": FactCheckerAgent("factchecker_a", "a", self.file_manager, self.config),
            "factchecker_b": FactCheckerAgent("factchecker_b", "b", self.file_manager, self.config),
            "judge": JudgeAgent("judge", self.file_manager, self.config),
            "crowd": CrowdAgent("crowd", self.file_manager, self.config),
        }
    
    async def run_debate(self) -> str:
        """Execute full debate workflow"""
        try:
            await self._phase_0_initialization()
            await self._phase_1_opening()
            await self._phase_2_debate_rounds()
            await self._phase_3_closing()
            await self._generate_outputs()
            
            return self.debate_id
        except Exception as e:
            logger.error(f"Debate failed: {e}")
            raise
    
    async def execute_agent_turn(self, agent_name: str, instructions: str) -> AgentResponse:
        """Execute single agent turn"""
        agent = self.agents[agent_name]
        
        # 1. Prepare context
        context = AgentContext(
            debate_id=self.debate_id,
            topic=self.topic,
            phase=self.state.phase.value,
            round_number=self.state.round_number,
            current_state=agent.read_state(),
            instructions=instructions,
            metadata={}
        )
        
        # 2. Execute turn
        response = await agent.execute_turn(context)
        
        # 3. Apply updates
        if response.success:
            for update in response.file_updates:
                self._apply_file_update(update)
        
        # 4. Update state
        self.state.next_turn(agent_name)
        
        return response
    
    def _apply_file_update(self, update: FileUpdate) -> None:
        """Apply file update via file manager"""
        if update.operation == "append_turn":
            self.file_manager.append_turn(update.data["speaker"], update.data)
        elif update.operation == "add_citation":
            self.file_manager.add_citation(
                update.data["team"],
                update.data["key"],
                update.data["citation"]
            )
        elif update.operation == "update_verification":
            self.file_manager.update_verification(
                update.data["team"],
                update.data["key"],
                update.data["verification"]
            )
        # ... more operations
```

---

## Testing Strategy

### Test Levels

1. **Unit Tests**: Individual components
2. **Integration Tests**: Agent-file and agent-agent interactions
3. **End-to-End Tests**: Full debate flow

---

Next: Shall I create the detailed test plan document?
