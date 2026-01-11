# AI Debate Platform - Test Plan

## Test Strategy Overview

```
Unit Tests (Isolated)
    ↓
Integration Tests (Agent-File, Agent-Agent)
    ↓
End-to-End Tests (Full Debate Flow)
```

---

## 1. Unit Tests

### 1.1 File Manager Tests

**Test: Read with Permission Filtering**
```python
def test_file_manager_permission_filtering():
    """Test that agents only see what they're allowed to see"""
    
    # Setup
    fm = FileManager("test_debate")
    fm.write_by_moderator("history_chat", {
        "public_transcript": [{"statement": "public"}],
        "team_notes": {
            "a": [{"supplementary_material": "secret_a"}],
            "b": [{"supplementary_material": "secret_b"}]
        }
    })
    
    # Test: debator_a should see public + team_notes.a
    data_a = fm.read_for_agent("debator_a", "history_chat")
    assert "public_transcript" in data_a
    assert data_a["team_notes"]["a"] is not None
    assert "b" not in data_a["team_notes"]  # Should not see team b notes
    
    # Test: judge should only see public
    data_judge = fm.read_for_agent("judge", "history_chat")
    assert "public_transcript" in data_judge
    assert "team_notes" not in data_judge  # Should not see any team notes
```

**Test: Atomic Write Operations**
```python
def test_file_manager_atomic_writes():
    """Test that writes are atomic (no partial writes)"""
    
    fm = FileManager("test_debate")
    
    # Simulate write failure midway
    with pytest.raises(Exception):
        with fm._atomic_write("history_chat") as f:
            f.write('{"incomplete":')  # Invalid JSON
            raise Exception("Simulated failure")
    
    # File should not exist or be unchanged
    assert not fm.file_path("history_chat").exists() or \
           fm.read_for_agent("moderator", "history_chat") == {}
```

**Test: Citation Key Generation**
```python
def test_citation_key_generation():
    """Test sequential citation key generation"""
    
    fm = FileManager("test_debate")
    
    # Generate keys for team a
    key1 = fm.generate_citation_key("a")
    key2 = fm.generate_citation_key("a")
    key3 = fm.generate_citation_key("b")
    
    assert key1 == "a_1"
    assert key2 == "a_2"
    assert key3 == "b_1"
```

### 1.2 State Manager Tests

**Test: State Transitions**
```python
def test_state_transitions():
    """Test valid and invalid state transitions"""
    
    state = DebateState("test_id", "test topic")
    
    # Valid transition
    state.transition_to(DebatePhase.OPENING)
    assert state.phase == DebatePhase.OPENING
    
    # Invalid transition (skip phase)
    with pytest.raises(InvalidStateTransition):
        state.transition_to(DebatePhase.CLOSING)  # Can't skip debate_rounds
```

**Test: Turn Tracking**
```python
def test_turn_tracking():
    """Test turn counting and speaker tracking"""
    
    state = DebateState("test_id", "test topic")
    
    state.next_turn("debator_a")
    assert state.turn_count == 1
    assert state.current_speaker == "debator_a"
    
    state.next_turn("debator_b")
    assert state.turn_count == 2
    assert state.current_speaker == "debator_b"
```

### 1.3 Agent Base Tests

**Test: Agent State Reading**
```python
def test_agent_reads_filtered_state():
    """Test that agent reads permission-filtered state"""
    
    fm = FileManager("test_debate")
    agent = DebatorAgent("debator_a", "a", fm, config)
    
    # Setup state
    fm.write_by_moderator("history_chat", test_data)
    
    # Agent reads state
    state = agent.read_state()
    
    # Verify filtering
    assert "team_notes" in state["history_chat"]
    assert "a" in state["history_chat"]["team_notes"]
    assert "b" not in state["history_chat"]["team_notes"]
```

---

## 2. Integration Tests: Agent-File Interactions

### 2.1 Test: Debator Adds Citation

```python
@pytest.mark.asyncio
async def test_debator_adds_citation_to_pool():
    """Test that debator can add citation and it appears in citation_pool"""
    
    # Setup
    debate_dir = "test_debates/test_citation_add"
    fm = FileManager(debate_dir)
    fm.initialize_files(debate_id="test", topic="test topic")
    
    agent = DebatorAgent("debator_a", "a", fm, mock_config)
    
    # Create context
    context = AgentContext(
        debate_id="test",
        topic="Should we test?",
        phase="opening",
        round_number=1,
        current_state=agent.read_state(),
        instructions="Generate opening statement with 2 citations",
        metadata={}
    )
    
    # Execute turn
    response = await agent.execute_turn(context)
    
    # Verify response
    assert response.success == True
    assert len(response.file_updates) >= 2  # At least statement + citations
    
    # Apply updates
    moderator = DebateModerator("test", mock_config)
    for update in response.file_updates:
        moderator._apply_file_update(update)
    
    # Verify citation pool updated
    citation_pool = fm.read_for_agent("moderator", "citation_pool")
    assert "team a" in citation_pool["citations"]
    assert "a_1" in citation_pool["citations"]["team a"]
    assert citation_pool["citations"]["team a"]["a_1"]["added_by"] == "debator_a"
```

### 2.2 Test: FactChecker Verifies Citation

```python
@pytest.mark.asyncio
async def test_factchecker_verifies_citation():
    """Test that factchecker can read and update citation verification"""
    
    # Setup: Create citation pool with unverified citation
    fm = FileManager("test_debates/test_verification")
    fm.write_by_moderator("citation_pool", {
        "debate_id": "test",
        "citations": {
            "team a": {
                "a_1": {
                    "source_url": "http://example.com/source",
                    "added_by": "debator_a",
                    "verification": {
                        "source_credibility_score": None,
                        "content_correspondence_score": None,
                        "adversary_comment": None,
                        "verified_by": None
                    }
                }
            }
        }
    })
    
    # Create factchecker agent
    agent = FactCheckerAgent("factchecker_b", "b", fm, mock_config)
    
    # Create context
    context = AgentContext(
        debate_id="test",
        topic="test",
        phase="opening",
        round_number=1,
        current_state=agent.read_state(),
        instructions="Verify team a's citations",
        metadata={"citations_to_verify": ["a_1"]}
    )
    
    # Execute verification
    response = await agent.execute_turn(context)
    
    # Apply updates
    for update in response.file_updates:
        if update.operation == "update_verification":
            fm.update_verification(
                update.data["team"],
                update.data["key"],
                update.data["verification"]
            )
    
    # Verify citation pool updated
    citation_pool = fm.read_for_agent("moderator", "citation_pool")
    verification = citation_pool["citations"]["team a"]["a_1"]["verification"]
    
    assert verification["source_credibility_score"] is not None
    assert verification["content_correspondence_score"] is not None
    assert verification["verified_by"] == "factchecker_b"
    assert 1 <= verification["source_credibility_score"] <= 10
```

### 2.3 Test: Judge Reads and Updates Debate Latent

```python
@pytest.mark.asyncio
async def test_judge_updates_debate_latent():
    """Test that judge can analyze debate and update latent space"""
    
    # Setup: Create history with statements
    fm = FileManager("test_debates/test_judge")
    fm.write_by_moderator("history_chat", {
        "public_transcript": [
            {
                "turn_id": "turn_001",
                "speaker": "a",
                "agent": "debator_a",
                "statement": "UBI would reduce poverty [a_1]"
            },
            {
                "turn_id": "turn_002",
                "speaker": "b",
                "agent": "debator_b",
                "statement": "UBI would cause inflation [b_1]"
            }
        ]
    })
    
    # Create judge agent
    agent = JudgeAgent("judge", fm, mock_config)
    
    # Execute analysis
    context = AgentContext(
        debate_id="test",
        topic="Should we implement UBI?",
        phase="opening",
        round_number=1,
        current_state=agent.read_state(),
        instructions="Analyze opening statements and identify disagreement frontier",
        metadata={}
    )
    
    response = await agent.execute_turn(context)
    
    # Apply updates
    for update in response.file_updates:
        fm.write_by_moderator("debate_latent", update.data)
    
    # Verify debate_latent updated
    latent = fm.read_for_agent("moderator", "debate_latent")
    
    assert len(latent["round_history"]) == 1
    assert latent["round_history"][0]["round_number"] == 1
    assert len(latent["round_history"][0]["disagreement_frontier"]) > 0
    
    frontier = latent["round_history"][0]["disagreement_frontier"][0]
    assert "core_issue" in frontier
    assert "a_stance" in frontier
    assert "b_stance" in frontier
```

---

## 3. Integration Tests: Agent-Agent Interactions

### 3.1 Test: Debator → FactChecker Flow

```python
@pytest.mark.asyncio
async def test_debator_to_factchecker_flow():
    """Test complete flow: debator creates citations, factchecker verifies"""
    
    debate_dir = "test_debates/test_agent_flow"
    fm = FileManager(debate_dir)
    moderator = DebateModerator("Test topic", mock_config)
    moderator.debate_dir = debate_dir
    moderator.file_manager = fm
    
    # Step 1: Debator A creates statement with citations
    response_debator = await moderator.execute_agent_turn(
        "debator_a",
        "Generate opening statement with 2 citations"
    )
    
    assert response_debator.success
    assert len(response_debator.output["citations"]) >= 2
    
    # Step 2: FactChecker B verifies citations
    response_checker = await moderator.execute_agent_turn(
        "factchecker_b",
        "Verify all citations from team a"
    )
    
    assert response_checker.success
    
    # Step 3: Verify state consistency
    citation_pool = fm.read_for_agent("moderator", "citation_pool")
    
    for citation_key in response_debator.output["citations"]:
        citation = citation_pool["citations"]["team a"][citation_key]
        assert citation["verification"]["verified_by"] == "factchecker_b"
        assert citation["verification"]["source_credibility_score"] is not None
```

### 3.2 Test: Judge → Debator Frontier Targeting

```python
@pytest.mark.asyncio
async def test_judge_frontier_influences_debator():
    """Test that debators target the disagreement frontier identified by judge"""
    
    moderator = DebateModerator("Test topic", mock_config)
    
    # Setup: Run opening round
    await moderator._phase_1_opening()
    
    # Judge identifies frontier
    latent = moderator.file_manager.read_for_agent("moderator", "debate_latent")
    frontier_issues = [f["core_issue"] for f in latent["round_history"][-1]["disagreement_frontier"]]
    
    # Debator A generates rebuttal
    response = await moderator.execute_agent_turn(
        "debator_a",
        f"Generate rebuttal targeting these issues: {', '.join(frontier_issues)}"
    )
    
    # Verify statement addresses frontier
    statement = response.output["statement"]
    assert any(issue.lower() in statement.lower() for issue in frontier_issues)
```

### 3.3 Test: Cross-Team Citation Reference

```python
@pytest.mark.asyncio
async def test_cross_team_citation_reference():
    """Test that debators can reference opponent's citations in rebuttals"""
    
    fm = FileManager("test_debates/test_cross_ref")
    
    # Setup: Team A has citations
    fm.write_by_moderator("citation_pool", {
        "citations": {
            "team a": {
                "a_1": {
                    "source_url": "http://example.com/a1",
                    "added_by": "debator_a"
                }
            },
            "team b": {}
        }
    })
    
    # Debator B can read team A's citations
    debator_b = DebatorAgent("debator_b", "b", fm, mock_config)
    state = debator_b.read_state()
    
    assert "team a" in state["citation_pool"]["citations"]
    assert "a_1" in state["citation_pool"]["citations"]["team a"]
    
    # Debator B generates rebuttal referencing A's citation
    context = AgentContext(
        debate_id="test",
        topic="test",
        phase="rebuttal",
        round_number=2,
        current_state=state,
        instructions="Generate rebuttal addressing opponent's citation a_1",
        metadata={}
    )
    
    response = await debator_b.execute_turn(context)
    
    # Verify reference to a_1
    assert "a_1" in response.output["statement"]
```

---

## 4. End-to-End Tests

### 4.1 Test: Complete Opening Phase

```python
@pytest.mark.asyncio
async def test_complete_opening_phase():
    """Test full opening phase: both debators + factcheckers + judge + crowd"""
    
    moderator = DebateModerator(
        topic="Should we implement universal basic income?",
        config=test_config
    )
    
    # Execute opening phase
    await moderator._phase_0_initialization()
    await moderator._phase_1_opening()
    
    # Verify state
    assert moderator.state.phase == DebatePhase.DEBATE_ROUNDS
    assert moderator.state.round_number == 1
    
    # Verify files created and populated
    history = moderator.file_manager.read_for_agent("moderator", "history_chat")
    assert len(history["public_transcript"]) >= 2  # Both debators spoke
    
    citations = moderator.file_manager.read_for_agent("moderator", "citation_pool")
    assert len(citations["citations"]["team a"]) > 0
    assert len(citations["citations"]["team b"]) > 0
    
    latent = moderator.file_manager.read_for_agent("moderator", "debate_latent")
    assert len(latent["round_history"]) == 1
    assert len(latent["round_history"][0]["disagreement_frontier"]) > 0
    
    crowd = moderator.file_manager.read_for_agent("moderator", "crowd_opinion")
    assert len(crowd["voters"]) > 0
    assert len(crowd["voters"][0]["voting_record"]) == 2  # Vote 0 + Vote 1
```

### 4.2 Test: Complete Debate (Minimal)

```python
@pytest.mark.asyncio
@pytest.mark.slow
async def test_complete_minimal_debate():
    """Test full debate with 1 debate round (fastest E2E test)"""
    
    config = test_config.copy()
    config.num_debate_rounds = 1  # Just 1 round for testing
    config.crowd_size = 10  # Reduced crowd
    
    moderator = DebateModerator(
        topic="Should we test software?",
        config=config
    )
    
    # Run complete debate
    debate_id = await moderator.run_debate()
    
    # Verify completion
    assert moderator.state.phase == DebatePhase.COMPLETED
    assert moderator.state.round_number == 1
    
    # Verify all files exist
    debate_dir = Path(f"debates/{debate_id}")
    assert (debate_dir / "history_chat.json").exists()
    assert (debate_dir / "citation_pool.json").exists()
    assert (debate_dir / "debate_latent.json").exists()
    assert (debate_dir / "crowd_opinion.json").exists()
    
    # Verify outputs generated
    assert (debate_dir / "outputs" / "transcript_full.md").exists()
    assert (debate_dir / "outputs" / "citation_ledger.json").exists()
    assert (debate_dir / "outputs" / "debate_logic_map.json").exists()
    assert (debate_dir / "outputs" / "voter_sentiment_graph.csv").exists()
```

### 4.3 Test: Error Recovery

```python
@pytest.mark.asyncio
async def test_error_recovery_during_turn():
    """Test that system can recover from agent failures"""
    
    moderator = DebateModerator("test", test_config)
    
    # Inject failure in debator
    with patch.object(moderator.agents["debator_a"], "execute_turn") as mock:
        mock.side_effect = Exception("Simulated LLM API failure")
        
        # Attempt turn with retry logic
        response = await moderator.execute_agent_turn_with_retry(
            "debator_a",
            "Generate statement",
            max_retries=3
        )
        
        # Should eventually fail gracefully
        assert response.success == False
        assert len(response.errors) > 0
    
    # State should be consistent
    assert moderator.state.current_speaker == "debator_a"
    # Files should not be corrupted
    history = moderator.file_manager.read_for_agent("moderator", "history_chat")
    assert isinstance(history, dict)
```

---

## 5. Performance Tests

### 5.1 Test: Concurrent File Access

```python
@pytest.mark.asyncio
async def test_concurrent_read_access():
    """Test that multiple agents can read simultaneously"""
    
    fm = FileManager("test_debates/concurrent")
    fm.write_by_moderator("history_chat", large_test_data)
    
    # Simulate multiple agents reading concurrently
    async def read_task(agent_name):
        return fm.read_for_agent(agent_name, "history_chat")
    
    results = await asyncio.gather(
        read_task("debator_a"),
        read_task("debator_b"),
        read_task("judge"),
        read_task("crowd")
    )
    
    # All should succeed
    assert all(isinstance(r, dict) for r in results)
```

### 5.2 Test: Large Debate Scale

```python
@pytest.mark.asyncio
@pytest.mark.slow
async def test_large_scale_debate():
    """Test debate with many rounds and full crowd"""
    
    config = test_config.copy()
    config.num_debate_rounds = 5
    config.crowd_size = 100
    
    moderator = DebateModerator("Large test topic", config)
    
    start_time = time.time()
    await moderator.run_debate()
    duration = time.time() - start_time
    
    # Performance assertions
    assert duration < 600  # Should complete within 10 minutes
    
    # Verify all rounds executed
    history = moderator.file_manager.read_for_agent("moderator", "history_chat")
    assert len(history["public_transcript"]) >= 10  # 2 per round × 5 rounds
```

---

## Test Execution Plan

### Phase 1: Unit Tests (Week 1)
```bash
pytest tests/unit/ -v
```
- File manager tests
- State manager tests
- Agent base tests

### Phase 2: Integration Tests (Week 2)
```bash
pytest tests/integration/ -v
```
- Agent-file interaction tests
- Agent-agent communication tests

### Phase 3: End-to-End Tests (Week 3)
```bash
pytest tests/e2e/ -v --slow
```
- Complete debate flows
- Error recovery
- Performance tests

### Continuous Testing
```bash
# Fast tests (pre-commit)
pytest tests/ -m "not slow" -v

# Full test suite (CI/CD)
pytest tests/ -v --cov=src --cov-report=html
```

---

## Test Data Fixtures

### Fixture: Mock Config
```python
@pytest.fixture
def mock_config():
    return Config(
        claude_api_key="test_key",
        perplexity_api_key="test_key",
        lambda_endpoint="http://localhost:8000",
        num_debate_rounds=2,
        crowd_size=10
    )
```

### Fixture: Test Debate Directory
```python
@pytest.fixture
def test_debate_dir(tmp_path):
    debate_dir = tmp_path / "test_debate"
    debate_dir.mkdir()
    return debate_dir
```

### Fixture: Sample Debate State
```python
@pytest.fixture
def sample_debate_state():
    return {
        "history_chat": {
            "public_transcript": [...],
            "team_notes": {...}
        },
        "citation_pool": {...},
        "debate_latent": {...},
        "crowd_opinion": {...}
    }
```

---

## Success Criteria

### Unit Tests
- ✅ 100% coverage for file_manager
- ✅ 100% coverage for state_manager
- ✅ All permission rules enforced

### Integration Tests
- ✅ All agent-file interactions work correctly
- ✅ File updates are atomic and consistent
- ✅ Permission violations are caught

### End-to-End Tests
- ✅ Complete debate runs without errors
- ✅ All output artifacts generated correctly
- ✅ State transitions are valid throughout

---

Next: Ready to start implementing? Which component should we build first?
