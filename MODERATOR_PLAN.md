# Moderator Implementation Plan

**Purpose**: Orchestrate the entire debate workflow from topic input to final outputs  
**Complexity**: High - coordinates 6 agents across 4 phases  
**Estimated**: ~500 lines of code, ~2-3 hours

---

## 🎯 What the Moderator Does

### Core Responsibilities

1. **Initialization**
   - Create debate directory
   - Initialize all JSON files
   - Create all agent instances
   - Run Vote 0 (crowd votes on stance)
   - Assign teams based on vote
   - Calculate resource multiplier

2. **Phase Execution**
   - Execute Phase 0 (Initialization)
   - Execute Phase 1 (Opening)
   - Execute Phase 2 (Debate Rounds, configurable)
   - Execute Phase 3 (Closing)

3. **Agent Coordination**
   - Execute agent turns in correct sequence
   - Pass context to each agent
   - Collect agent responses
   - Apply file updates from agents
   - Update debate state after each turn

4. **State Management**
   - Track current phase, round, turn
   - Validate state transitions
   - Update metadata in JSON files
   - Handle errors and retry logic

5. **Output Generation**
   - Generate transcript_full.md
   - Generate citation_ledger.json
   - Generate debate_logic_map.json
   - Generate voter_sentiment_graph.csv

---

## 🏗️ Moderator Architecture

### Class Structure

```python
class DebateModerator:
    """Orchestrates the complete debate workflow."""
    
    def __init__(self, topic: str, config: Config):
        self.debate_id = str(uuid.uuid4())
        self.topic = topic
        self.config = config
        
        # Initialize managers
        self.debate_dir = Path(f"debates/{self.debate_id}")
        self.file_manager = FileManager(str(self.debate_dir))
        self.state = DebateState(self.debate_id, topic)
        
        # Initialize all agents
        self.agents = self._initialize_agents()
    
    async def run_debate(self) -> str:
        """Main entry point - runs complete debate."""
        await self._phase_0_initialization()
        await self._phase_1_opening()
        await self._phase_2_debate_rounds()
        await self._phase_3_closing()
        await self._generate_outputs()
        return self.debate_id
```

---

## 📋 Phase-by-Phase Workflow

### Phase 0: Initialization

**Goal**: Set up debate, assign teams, calculate resources

```python
async def _phase_0_initialization(self):
    """
    Initialize debate.
    
    Steps:
    1. Create debate directory
    2. Initialize all JSON files
    3. Run Vote 0 (crowd votes on stance preference)
    4. Determine team assignments (winner → team a)
    5. Calculate resource multiplier if bias > 60%
    6. Transition state to OPENING
    """
    
    # 1. Create directory and files
    self.debate_dir.mkdir(parents=True, exist_ok=True)
    self.file_manager.initialize_files(self.debate_id, self.topic)
    
    # 2. Run Vote 0 - crowd votes on stance
    vote_zero_context = AgentContext(
        debate_id=self.debate_id,
        topic=self.topic,
        phase="initialization",
        round_number=0,  # Vote 0
        current_state={},
        instructions="Vote on your initial stance preference"
    )
    
    vote_zero_response = await self.execute_agent_turn("crowd", vote_zero_context)
    
    # 3. Process Vote 0 results
    votes = vote_zero_response.output["votes"]
    avg_score = vote_zero_response.output["average_score"]
    
    # Scores > 50 = FOR, < 50 = AGAINST
    for_count = sum(1 for v in votes if v["score"] > 50)
    against_count = len(votes) - for_count
    
    # 4. Assign teams (winner becomes team a)
    self.state.assign_teams(
        for_stance="for",
        against_stance="against",
        vote_results={"for": for_count, "against": against_count}
    )
    
    # 5. Calculate resource multiplier
    self.state.calculate_resource_multiplier(
        vote_results={"for": for_count, "against": against_count},
        threshold=self.config.resource_multiplier_threshold
    )
    
    # 6. Transition to opening
    self.state.transition_to(DebatePhase.OPENING)
```

---

### Phase 1: Opening

**Goal**: Both debators present opening statements, get verified, analyzed, voted on

```python
async def _phase_1_opening(self):
    """
    Execute opening phase.
    
    Turn sequence:
    1. debator_a: Research + generate opening
    2. factchecker_b: Verify a's citations
    3. debator_b: Research + generate opening
    4. factchecker_a: Verify b's citations
    5. judge: Analyze both openings, map frontier
    6. crowd: Vote 1 (rate debate performance)
    """
    
    self.state.next_round()  # Round 1
    
    # Turn 1: debator_a opening
    await self.execute_agent_turn("debator_a", context={
        "phase": "opening",
        "round_number": 1,
        "instructions": "Generate your opening statement"
    })
    
    # Turn 2: factchecker_b verifies
    await self.execute_agent_turn("factchecker_b", context={
        "phase": "opening",
        "round_number": 1,
        "instructions": "Verify opponent's citations"
    })
    
    # Turn 3: debator_b opening
    await self.execute_agent_turn("debator_b", ...)
    
    # Turn 4: factchecker_a verifies
    await self.execute_agent_turn("factchecker_a", ...)
    
    # Turn 5: judge analyzes
    await self.execute_agent_turn("judge", ...)
    
    # Turn 6: crowd votes
    await self.execute_agent_turn("crowd", context={
        "round_number": 1,  # Vote 1
        "instructions": "Vote on debate performance"
    })
    
    # Transition to debate rounds
    self.state.transition_to(DebatePhase.DEBATE_ROUNDS)
```

---

### Phase 2: Debate Rounds

**Goal**: Iterative rebuttals with fact-checking, frontier updates, voting

```python
async def _phase_2_debate_rounds(self):
    """
    Execute debate rounds (default: 2).
    
    Each round:
    1. factchecker_a: Defense + Offense
    2. debator_a: Rebuttal targeting frontier
    3. factchecker_b: Defense + Offense
    4. debator_b: Rebuttal targeting frontier
    5. judge: Update frontier
    6. crowd: Vote on round
    """
    
    for round_num in range(2, 2 + self.config.num_debate_rounds):
        self.state.next_round()
        
        # Team a turn
        await self.execute_agent_turn("factchecker_a", context={
            "phase": "rebuttal",
            "round_number": round_num,
            "instructions": "Defend your citations and verify opponent's"
        })
        
        await self.execute_agent_turn("debator_a", context={
            "phase": "rebuttal",
            "round_number": round_num,
            "instructions": "Generate rebuttal targeting disagreement frontier"
        })
        
        # Team b turn
        await self.execute_agent_turn("factchecker_b", ...)
        await self.execute_agent_turn("debator_b", ...)
        
        # Evaluation
        await self.execute_agent_turn("judge", ...)
        await self.execute_agent_turn("crowd", ...)
    
    # Transition to closing
    self.state.transition_to(DebatePhase.CLOSING)
```

---

### Phase 3: Closing

**Goal**: Final verification, closing statements, final analysis and vote

```python
async def _phase_3_closing(self):
    """
    Execute closing phase.
    
    Sequence:
    1. factchecker_a: Final verification
    2. factchecker_b: Final verification
    3. debator_a: Closing statement (no new citations)
    4. debator_b: Closing statement (no new citations)
    5. judge: Final report
    6. crowd: Final vote
    """
    
    # Final fact-checking
    await self.execute_agent_turn("factchecker_a", ...)
    await self.execute_agent_turn("factchecker_b", ...)
    
    # Closing statements
    await self.execute_agent_turn("debator_a", context={
        "phase": "closing",
        "instructions": "Generate closing statement (no new citations)"
    })
    await self.execute_agent_turn("debator_b", ...)
    
    # Final evaluation
    await self.execute_agent_turn("judge", context={
        "instructions": "Provide final analysis and report"
    })
    
    await self.execute_agent_turn("crowd", context={
        "instructions": "Cast final vote"
    })
    
    # Transition to completed
    self.state.transition_to(DebatePhase.COMPLETED)
```

---

## 🔧 Core Methods

### 1. Agent Turn Execution

```python
async def execute_agent_turn(
    self,
    agent_name: str,
    context_params: Dict[str, Any]
) -> AgentResponse:
    """
    Execute a single agent turn.
    
    Steps:
    1. Get agent instance
    2. Prepare AgentContext
    3. Execute agent.execute_turn(context)
    4. Validate response
    5. Apply file updates
    6. Update state
    7. Log action
    
    Returns:
        AgentResponse from the agent
    """
    
    agent = self.agents[agent_name]
    
    # Build context
    context = AgentContext(
        debate_id=self.debate_id,
        topic=self.topic,
        phase=context_params.get("phase", self.state.phase.value),
        round_number=context_params.get("round_number", self.state.round_number),
        current_state=agent.read_state(),  # Permission-filtered!
        instructions=context_params.get("instructions", "")
    )
    
    # Execute turn
    print(f"🎯 Executing: {agent_name} (Round {context.round_number})")
    response = await agent.execute_turn(context)
    
    if not response.success:
        print(f"❌ {agent_name} failed: {response.errors}")
        raise Exception(f"Agent {agent_name} failed")
    
    # Apply file updates
    for update in response.file_updates:
        self._apply_file_update(update)
    
    # Update state
    self.state.next_turn(agent_name)
    
    print(f"✅ {agent_name} completed")
    
    return response
```

### 2. File Update Application

```python
def _apply_file_update(self, update: FileUpdate) -> None:
    """
    Apply file update from agent.
    
    Maps FileUpdateOperation to FileManager methods.
    """
    
    if update.operation == FileUpdateOperation.APPEND_TURN:
        # Add turn to history_chat
        speaker = update.data.get("speaker")
        self.file_manager.append_turn(speaker, update.data)
    
    elif update.operation == FileUpdateOperation.ADD_CITATION:
        # Add citation to citation_pool
        team = update.data["team"]
        key = update.data["key"]
        citation = update.data["citation"]
        self.file_manager.add_citation(team, key, citation)
    
    elif update.operation == FileUpdateOperation.UPDATE_VERIFICATION:
        # Update verification in citation_pool
        team = update.data["team"]
        key = update.data["key"]
        verification = update.data["verification"]
        self.file_manager.update_verification(team, key, verification)
    
    elif update.operation == FileUpdateOperation.UPDATE_DEBATE_LATENT:
        # Append to debate_latent round_history
        data = self.file_manager._read_json("debate_latent")
        data["round_history"].append(update.data)
        self.file_manager.write_by_moderator("debate_latent", data)
    
    elif update.operation == FileUpdateOperation.ADD_CROWD_VOTE:
        # Add vote round to crowd_opinion
        data = self.file_manager._read_json("crowd_opinion")
        # Update or append voting records for each voter
        # ... implementation details
```

### 3. Agent Initialization

```python
def _initialize_agents(self) -> Dict[str, Agent]:
    """
    Create all agent instances.
    
    Returns:
        Dictionary of {agent_name: agent_instance}
    """
    
    # Determine stances based on team assignments (after Vote 0)
    # For now, assume "for" is team a, "against" is team b
    
    agents = {
        "debator_a": DebatorAgent(
            name="debator_a",
            team="a",
            stance="for",  # Will be determined after Vote 0
            file_manager=self.file_manager,
            config=self.config
        ),
        "debator_b": DebatorAgent(
            name="debator_b",
            team="b",
            stance="against",
            file_manager=self.file_manager,
            config=self.config
        ),
        "factchecker_a": FactCheckerAgent(
            name="factchecker_a",
            team="a",
            file_manager=self.file_manager,
            config=self.config
        ),
        "factchecker_b": FactCheckerAgent(
            name="factchecker_b",
            team="b",
            file_manager=self.file_manager,
            config=self.config
        ),
        "judge": JudgeAgent(
            name="judge",
            file_manager=self.file_manager,
            config=self.config
        ),
        "crowd": CrowdAgent(
            name="crowd",
            file_manager=self.file_manager,
            config=self.config
        )
    }
    
    return agents
```

---

## 🔄 Turn Sequencing Logic

### Key Insight: Sequential Execution

All agent turns are **sequential** (not parallel):
- Agent A completes → Files updated → Agent B starts
- This ensures Agent B sees Agent A's output
- Simple to implement and debug
- Matches real debate flow

### Turn Dependencies

```
Phase 1 (Opening):
  debator_a → creates citations → factchecker_b can verify
  debator_b → creates citations → factchecker_a can verify
  both statements → judge can analyze → crowd can vote

Phase 2 (Rebuttal):
  factchecker_a → responds to criticism from factchecker_b
  debator_a → reads frontier from judge
  factchecker_b → verifies debator_a's new citations
  debator_b → reads frontier and debator_a's argument
  judge → analyzes new arguments
  crowd → votes on updated debate
```

**No deadlocks because turns are sequential!**

---

## 🎛️ Moderator Configuration

### What Can Be Tuned

```python
@dataclass
class ModeratorConfig:
    """Moderator-specific configuration."""
    
    # Debate settings
    num_debate_rounds: int = 2        # Phase 2 rounds
    enable_vote_zero: bool = True     # Team assignment
    enable_resource_multiplier: bool = True
    
    # Agent settings
    enable_factchecking: bool = True  # Can disable for faster testing
    enable_judging: bool = True
    enable_crowd_voting: bool = True
    
    # Error handling
    max_retries_per_turn: int = 3
    continue_on_agent_failure: bool = False  # Fail fast or continue?
    
    # Output settings
    generate_transcript: bool = True
    generate_ledger: bool = True
    generate_logic_map: bool = True
    generate_sentiment_graph: bool = True
```

---

## 🧪 Testing Strategy

### Unit Tests (`test_moderator.py`)

1. **Test initialization**
   - Creates debate directory
   - Initializes files
   - Creates all agents

2. **Test agent turn execution**
   - Builds context correctly
   - Calls agent
   - Applies file updates
   - Updates state

3. **Test file update application**
   - Each update operation type
   - Validates file contents after update

4. **Test phase transitions**
   - Valid transitions work
   - Invalid transitions blocked

### Integration Tests (`test_debate_integration.py`)

1. **Test Phase 0**
   - Vote 0 works
   - Team assignment logic
   - Resource multiplier calculation

2. **Test Phase 1**
   - Complete opening round
   - All agents execute in sequence
   - Files updated correctly

3. **Test agent communication via files**
   - debator_a creates citation
   - factchecker_b can read and verify it
   - judge sees both statements
   - crowd sees public transcript

### End-to-End Tests (`test_full_debate.py`)

1. **Test complete debate (mocked)**
   - All phases execute
   - All agents complete
   - All outputs generated
   - Takes ~1 minute with mocks

---

## 📊 State Management & Crash Recovery

### State Tracking

The Moderator tracks:
- `debate_id` - Unique identifier
- `phase` - Current phase (enum)
- `round_number` - Current round
- `turn_count` - Total turns executed
- `current_speaker` - Agent taking turn
- `team_assignments` - Which stance → which team
- `resource_multiplier` - Audience bias adjustment
- `completed_turns` - List of completed agent turns
- `total_cost` - Cumulative API cost

### State Persistence Strategies

#### Option 1: In-Memory Only (No Persistence)
**Pros**: Simple, no file I/O overhead  
**Cons**: Crash = lose all progress, re-run expensive API calls  
**Cost Impact**: 💰💰💰 If crash after 15 turns, lose ~$0.50+ in API calls

#### Option 2: Full Persistence After Every Turn
**Pros**: Can resume from exact point of failure  
**Cons**: Heavy I/O, slower execution  
**Cost Impact**: ✅ No wasted API calls

#### Option 3: Checkpoint Persistence (RECOMMENDED for Testing)
**Pros**: Balance between safety and performance  
**Cons**: May lose 1-2 turns if crash mid-checkpoint  
**Cost Impact**: ✅ Minimal waste (~$0.02 max)

**Strategy**: Save checkpoint after:
- Vote 0 completes (expensive Deep Research coming)
- Each debator turn (Deep Research = $0.08)
- Each phase transition
- Each round completes

### Checkpoint File Format

```json
{
  "debate_id": "abc-123",
  "checkpoint_version": "1.0",
  "timestamp": "2026-01-06T10:30:00Z",
  "state": {
    "phase": "debate_rounds",
    "round_number": 2,
    "turn_count": 15,
    "current_speaker": "debator_b",
    "team_assignments": {
      "team_a": {"stance": "for", "agents": ["debator_a", "factchecker_a"]},
      "team_b": {"stance": "against", "agents": ["debator_b", "factchecker_b"]}
    },
    "resource_multiplier": 1.2
  },
  "completed_turns": [
    {"turn": 1, "agent": "crowd", "action": "vote_zero", "cost": 0.02},
    {"turn": 2, "agent": "debator_a", "action": "opening", "cost": 0.08},
    {"turn": 3, "agent": "factchecker_b", "action": "verify", "cost": 0.15},
    // ... all completed turns
  ],
  "costs": {
    "total": 0.87,
    "by_agent": {
      "debator_a": 0.16,
      "debator_b": 0.16,
      "factchecker_a": 0.30,
      "factchecker_b": 0.15,
      "judge": 0.08,
      "crowd": 0.02
    }
  }
}
```

**File location**: `debates/{debate_id}/moderator_checkpoint.json`

### Resume Logic

```python
class DebateModerator:
    
    @classmethod
    async def resume_from_checkpoint(cls, debate_id: str) -> "DebateModerator":
        """
        Resume debate from checkpoint file.
        
        Steps:
        1. Load checkpoint file
        2. Validate checkpoint integrity
        3. Reconstruct moderator state
        4. Verify JSON files match checkpoint
        5. Continue from last completed turn
        """
        checkpoint_path = Path(f"debates/{debate_id}/moderator_checkpoint.json")
        
        if not checkpoint_path.exists():
            raise FileNotFoundError(f"No checkpoint found for debate {debate_id}")
        
        with open(checkpoint_path) as f:
            checkpoint = json.load(f)
        
        # Reconstruct moderator
        moderator = cls.__new__(cls)
        moderator.debate_id = debate_id
        moderator.state = DebateState.from_checkpoint(checkpoint["state"])
        moderator.completed_turns = checkpoint["completed_turns"]
        moderator.total_cost = checkpoint["costs"]["total"]
        
        # Reinitialize agents and file manager
        moderator.debate_dir = Path(f"debates/{debate_id}")
        moderator.file_manager = FileManager(str(moderator.debate_dir))
        moderator.agents = moderator._initialize_agents()
        
        print(f"✅ Resumed debate {debate_id}")
        print(f"   Last turn: {checkpoint['completed_turns'][-1]}")
        print(f"   Cost so far: ${checkpoint['costs']['total']:.2f}")
        
        return moderator
    
    def _save_checkpoint(self) -> None:
        """
        Save current state to checkpoint file.
        
        Called after:
        - Vote 0 completes
        - Each debator turn (expensive)
        - Each phase transition
        - Each round completes
        """
        checkpoint = {
            "debate_id": self.debate_id,
            "checkpoint_version": "1.0",
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "state": {
                "phase": self.state.phase.value,
                "round_number": self.state.round_number,
                "turn_count": self.state.turn_count,
                "current_speaker": self.state.current_speaker,
                "team_assignments": self.state.team_assignments,
                "resource_multiplier": self.state.resource_multiplier
            },
            "completed_turns": self.completed_turns,
            "costs": {
                "total": self.total_cost,
                "by_agent": self._calculate_cost_by_agent()
            }
        }
        
        checkpoint_path = self.debate_dir / "moderator_checkpoint.json"
        with open(checkpoint_path, 'w') as f:
            json.dump(checkpoint, f, indent=2)
    
    async def execute_agent_turn(
        self,
        agent_name: str,
        context_params: Dict[str, Any]
    ) -> AgentResponse:
        """Execute agent turn with checkpoint saving."""
        
        # Execute turn
        response = await self._execute_agent_turn_internal(agent_name, context_params)
        
        # Record completion
        self.completed_turns.append({
            "turn": self.state.turn_count,
            "agent": agent_name,
            "action": context_params.get("phase", ""),
            "cost": response.output.get("_cost_estimate", 0.0),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
        # Update total cost
        self.total_cost += response.output.get("_cost_estimate", 0.0)
        
        # Save checkpoint if expensive turn or phase boundary
        if self._should_checkpoint(agent_name, context_params):
            self._save_checkpoint()
            print(f"💾 Checkpoint saved (Cost: ${self.total_cost:.2f})")
        
        return response
    
    def _should_checkpoint(self, agent_name: str, context_params: Dict[str, Any]) -> bool:
        """
        Determine if we should save a checkpoint.
        
        Checkpoint triggers:
        - Vote 0 completes (before expensive Deep Research)
        - Debator turns (Deep Research = $0.08)
        - Phase transitions
        - Round completes
        """
        # Vote 0 just completed
        if context_params.get("round_number") == 0 and agent_name == "crowd":
            return True
        
        # Debator turn (expensive Deep Research)
        if "debator" in agent_name:
            return True
        
        # Phase transition
        phase = context_params.get("phase", "")
        if phase != self.state.phase.value:
            return True
        
        # Round boundary (judge just completed)
        if agent_name == "judge":
            return True
        
        return False
```

### Usage in Testing

```python
# Start new debate
moderator = DebateModerator(topic="Should UBI be implemented?", config=config)
await moderator.run_debate()

# If crash occurs...
# Resume from last checkpoint
moderator = await DebateModerator.resume_from_checkpoint("abc-123")
await moderator.run_debate()  # Continues from where it left off
```

### Testing the Resume Logic

```python
# test_moderator.py

@pytest.mark.asyncio
async def test_checkpoint_and_resume(mock_agents, tmp_path):
    """Test that debate can resume from checkpoint after simulated crash."""
    
    # Start debate
    moderator = DebateModerator(topic="Test topic", config=test_config)
    moderator.debate_dir = tmp_path / moderator.debate_id
    
    # Execute first 3 turns
    await moderator._phase_0_initialization()
    await moderator.execute_agent_turn("debator_a", {...})
    await moderator.execute_agent_turn("factchecker_b", {...})
    
    # Checkpoint should exist
    checkpoint_path = moderator.debate_dir / "moderator_checkpoint.json"
    assert checkpoint_path.exists()
    
    # Simulate crash - create new instance
    moderator2 = await DebateModerator.resume_from_checkpoint(moderator.debate_id)
    
    # Verify state matches
    assert moderator2.state.turn_count == moderator.state.turn_count
    assert moderator2.total_cost == moderator.total_cost
    assert len(moderator2.completed_turns) == len(moderator.completed_turns)
    
    # Continue debate
    await moderator2.execute_agent_turn("debator_b", {...})
    assert moderator2.state.turn_count == moderator.state.turn_count + 1
```

### Cost Savings Analysis

**Scenario: Crash after 15 turns (mid-debate)**

| Strategy | Turns Lost | Cost Wasted | Resume Time |
|----------|------------|-------------|-------------|
| No persistence | 15 | ~$0.50 | Must restart |
| Full persistence | 0 | $0.00 | Instant |
| Checkpoint (after expensive) | 0-1 | ~$0.02 | Instant |

**For testing phase, checkpoint strategy saves significant cost!**

### Implementation Complexity

**Estimated additional time**: +2 hours
- Checkpoint save/load: 1 hour
- Resume logic: 30 min
- Testing resume: 30 min

**Worth it?** ✅ **YES** - Saves money during testing, good practice for production

### Production Benefits

Even after testing, checkpoint persistence provides:
- **Crash recovery**: Don't lose debate if server crashes
- **Cost tracking**: See real-time spend per debate
- **Debugging**: Replay debate turn-by-turn
- **Audit trail**: Full history of agent actions

---

## 🚨 Error Handling

### Failure Scenarios

1. **Agent fails to execute**
   - Retry up to 3 times
   - If still fails, decide: abort or continue?

2. **File update fails**
   - Atomic writes should prevent corruption
   - Log error and retry

3. **State transition invalid**
   - Should never happen (indicates bug)
   - Fail fast with clear error

4. **API rate limit or timeout**
   - Exponential backoff in clients
   - Moderator waits and retries

### Recovery Strategy

```python
async def execute_agent_turn_with_retry(
    self,
    agent_name: str,
    context_params: Dict[str, Any],
    max_retries: int = 3
) -> AgentResponse:
    """Execute agent turn with retry logic."""
    
    for attempt in range(max_retries):
        try:
            return await self.execute_agent_turn(agent_name, context_params)
        except Exception as e:
            if attempt < max_retries - 1:
                print(f"⚠️  Retry {attempt + 1}/{max_retries} for {agent_name}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
            else:
                raise
```

---

## 📝 Output Generation

### After Debate Completes

```python
async def _generate_outputs(self):
    """
    Generate all final artifacts.
    
    Outputs:
    1. transcript_full.md - Human-readable debate
    2. citation_ledger.json - All citations + scores
    3. debate_logic_map.json - Frontier evolution
    4. voter_sentiment_graph.csv - Opinion shifts
    """
    
    output_dir = self.debate_dir / "outputs"
    output_dir.mkdir(exist_ok=True)
    
    # Read all files
    history = self.file_manager.read_for_agent("moderator", "history_chat")
    citations = self.file_manager.read_for_agent("moderator", "citation_pool")
    latent = self.file_manager.read_for_agent("moderator", "debate_latent")
    crowd = self.file_manager.read_for_agent("moderator", "crowd_opinion")
    
    # Generate each output (will implement generators later)
    # For now, just copy JSON files
    ...
```

---

## 🎯 Implementation Order

### Step 1: Basic Structure (30 min)
- DebateModerator class
- `__init__` method
- `_initialize_agents()` method
- Basic `run_debate()` skeleton

### Step 2: Agent Turn Execution (1 hour)
- `execute_agent_turn()` method
- `_apply_file_update()` method
- Context building
- Error handling

### Step 3: Phase 0 (30 min)
- `_phase_0_initialization()` method
- Vote 0 processing
- Team assignment
- Resource multiplier

### Step 4: Phase 1 (45 min)
- `_phase_1_opening()` method
- Turn sequencing
- All 6 agent turns

### Step 5: Phase 2 (45 min)
- `_phase_2_debate_rounds()` method
- Loop over rounds
- Turn sequencing per round

### Step 6: Phase 3 (30 min)
- `_phase_3_closing()` method
- Final turns
- State completion

### Step 7: Testing (1-2 hours)
- Unit tests
- Integration tests
- Mock complete debate

### Step 8: Output Generation (1 hour)
- Simple generators for 4 outputs
- Will refine later

**Total: ~6-7 hours**

---

## 💡 Key Design Decisions

### 1. Sequential vs Parallel
**Choice**: Sequential (simpler, matches debate flow)

### 2. State Persistence
**Choice**: In-memory for MVP (add persistence later if needed)

### 3. Error Handling
**Choice**: Fail fast (easier to debug)

### 4. Agent Creation
**Choice**: All agents created at start (vs lazy instantiation)

### 5. Stance Assignment
**Choice**: After Vote 0, update debator stances dynamically

---

## 🤔 Questions for You

Before I implement, any preferences on:

1. **Error handling**: Fail fast or try to continue?
2. **Logging**: Console output level? (verbose/minimal)
3. **Output generation**: Simple JSON copy for MVP, or rich formatting?
4. **State persistence**: In-memory only, or save to file?

**My recommendations**:
- Error handling: Fail fast (easier to debug)
- Logging: Verbose (we want to see what's happening)
- Outputs: Simple for MVP (refine later)
- State: In-memory (add persistence if needed)

**Should I proceed with these defaults?**
