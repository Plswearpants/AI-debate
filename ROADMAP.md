# AI Debate Platform - Implementation Roadmap

## Overview

This roadmap follows a **bottom-up** approach: build and test foundational components first, then integrate them into the complete system.

---

## Phase 1: Foundation (Week 1)

### Goal: Core infrastructure with file management and state tracking

### 1.1 Project Setup
- [ ] Create project structure
- [ ] Setup virtual environment
- [ ] Install dependencies (`requirements.txt`)
- [ ] Configure `.env` for API keys
- [ ] Setup pytest and coverage tools

### 1.2 File Manager Implementation
**File**: `src/utils/file_manager.py`

- [ ] Implement basic JSON read/write
- [ ] Implement permission matrix
- [ ] Implement `read_for_agent()` with filtering
- [ ] Implement `write_by_moderator()`
- [ ] Implement atomic write operations
- [ ] Implement helper methods:
  - [ ] `append_turn()`
  - [ ] `add_citation()`
  - [ ] `update_verification()`

**Tests**: `tests/unit/test_file_manager.py`
- [ ] Test permission filtering
- [ ] Test atomic writes
- [ ] Test citation key generation
- [ ] Test concurrent reads

**Deliverable**: Working file manager with 100% test coverage

### 1.3 State Manager Implementation
**File**: `src/utils/state_manager.py`

- [ ] Implement `DebateState` class
- [ ] Implement state transitions
- [ ] Implement turn/round tracking
- [ ] Add validation for state changes

**Tests**: `tests/unit/test_state_manager.py`
- [ ] Test state transitions
- [ ] Test turn tracking
- [ ] Test invalid transitions

**Deliverable**: Working state manager with validation

### 1.4 Configuration Management
**File**: `src/config.py`

- [ ] Define `Config` dataclass
- [ ] Load from `.env` file
- [ ] Validate configuration
- [ ] Add configuration presets (test, dev, prod)

---

## Phase 2: Agent Foundation (Week 2)

### Goal: Agent base classes and file interaction

### 2.1 Agent Base Class
**File**: `src/agents/base.py`

- [ ] Implement `Agent` abstract base class
- [ ] Implement `AgentContext` dataclass
- [ ] Implement `AgentResponse` dataclass
- [ ] Implement `FileUpdate` dataclass
- [ ] Implement `read_state()` method

**Tests**: `tests/unit/test_agent_base.py`
- [ ] Test agent reads filtered state
- [ ] Test response structure
- [ ] Test file update structure

### 2.2 LLM Clients
**Files**: `src/clients/`

- [ ] Implement `claude_client.py` (Anthropic API)
- [ ] Implement `perplexity_client.py` (Perplexity API)
- [ ] Implement `openai_client.py` (OpenAI API for judge)
- [ ] Implement `lambda_client.py` (Lambda GPU endpoint)
- [ ] Add retry logic and error handling
- [ ] Add response caching for testing

**Tests**: `tests/unit/test_llm_clients.py`
- [ ] Test API calls (mocked)
- [ ] Test retry logic
- [ ] Test error handling

### 2.3 MCP Client
**File**: `src/clients/mcp_client.py`

- [ ] Implement MCP browser integration
- [ ] Implement `search()` method
- [ ] Implement `read_page()` method
- [ ] Implement `navigate()` method
- [ ] Add caching for repeated searches

**Tests**: `tests/unit/test_mcp_client.py`
- [ ] Test search functionality
- [ ] Test page reading
- [ ] Test error handling

**Deliverable**: All API clients working with mocks

---

## Phase 3: Agent Implementation (Week 3)

### Goal: Implement all agent types with their specific logic

### 3.1 Debator Agent
**File**: `src/agents/debator.py`

- [ ] Implement `DebatorAgent` class
- [ ] Implement `deep_research()` using MCP
- [ ] Implement `generate_statement()` using Claude
- [ ] Implement citation extraction and registration
- [ ] Add system prompt template

**File**: `src/prompts/debator_system.txt`
- [ ] Craft system prompt for debators
- [ ] Include citation format instructions
- [ ] Include stance-specific instructions

**Tests**: `tests/integration/test_debator_agent.py`
- [ ] Test research phase (mocked MCP)
- [ ] Test statement generation
- [ ] Test citation addition to pool
- [ ] Test opening vs rebuttal vs closing

**Deliverable**: Working debator that researches and generates statements

### 3.2 FactChecker Agent
**File**: `src/agents/factchecker.py`

- [ ] Implement `FactCheckerAgent` class
- [ ] Implement `verify_citation()` using Perplexity
- [ ] Implement offense (scrutinize opponent)
- [ ] Implement defense (respond to adversary scores)
- [ ] Add system prompt template

**File**: `src/prompts/factchecker_system.txt`
- [ ] Craft system prompt for fact checkers
- [ ] Include scoring rubric (1-10 scale)
- [ ] Include verification guidelines

**Tests**: `tests/integration/test_factchecker_agent.py`
- [ ] Test citation verification
- [ ] Test score parsing
- [ ] Test defense responses
- [ ] Test update to citation pool

**Deliverable**: Working fact checker that verifies and scores

### 3.3 Judge Agent
**File**: `src/agents/judge.py`

- [ ] Implement `JudgeAgent` class
- [ ] Implement `analyze_debate()` method
- [ ] Implement consensus identification
- [ ] Implement disagreement frontier extraction
- [ ] Add system prompt template

**File**: `src/prompts/judge_system.txt`
- [ ] Craft system prompt for judge
- [ ] Include analysis framework
- [ ] Include JSON output format

**Tests**: `tests/integration/test_judge_agent.py`
- [ ] Test debate analysis
- [ ] Test consensus extraction
- [ ] Test frontier identification
- [ ] Test update to debate_latent

**Deliverable**: Working judge that analyzes and maps debate

### 3.4 Crowd Agent
**File**: `src/agents/crowd.py`

- [ ] Implement `CrowdAgent` class
- [ ] Implement `vote_on_debate()` method
- [ ] Implement batch inference to Lambda
- [ ] Load 100 personas from JSON
- [ ] Implement vote aggregation

**File**: `src/prompts/crowd_personas.json`
- [ ] Define 100 diverse personas
- [ ] Include ideological spectrum
- [ ] Include professional backgrounds
- [ ] Include demographic diversity

**Tests**: `tests/integration/test_crowd_agent.py`
- [ ] Test batch voting
- [ ] Test vote aggregation
- [ ] Test persona diversity
- [ ] Test update to crowd_opinion

**Deliverable**: Working crowd with 100 personas

---

## Phase 4: Orchestration (Week 4)

### Goal: Build the moderator that orchestrates the full debate

### 4.1 Moderator Core
**File**: `src/moderator.py`

- [ ] Implement `DebateModerator` class
- [ ] Implement `execute_agent_turn()` method
- [ ] Implement `_apply_file_update()` method
- [ ] Implement turn sequencing logic
- [ ] Add logging and progress tracking

**Tests**: `tests/integration/test_moderator.py`
- [ ] Test agent turn execution
- [ ] Test file update application
- [ ] Test error handling

### 4.2 Phase 0: Initialization
**Method**: `_phase_0_initialization()`

- [ ] Create debate directory
- [ ] Initialize all JSON files
- [ ] Implement Vote Zero (crowd votes on stance)
- [ ] Assign Team a/b based on majority
- [ ] Calculate resource multiplier

**Tests**: `tests/e2e/test_phase_0.py`
- [ ] Test directory creation
- [ ] Test Vote Zero
- [ ] Test team assignment
- [ ] Test resource multiplier calculation

### 4.3 Phase 1: Opening
**Method**: `_phase_1_opening()`

- [ ] Turn 1: debator_a generates opening
- [ ] Turn 2: factchecker_b verifies a's citations
- [ ] Turn 3: debator_b generates opening
- [ ] Turn 4: factchecker_a verifies b's citations
- [ ] Turn 5: judge analyzes openings
- [ ] Turn 6: crowd votes (Vote 1)

**Tests**: `tests/e2e/test_phase_1.py`
- [ ] Test complete opening phase
- [ ] Test all files updated correctly
- [ ] Test state transitions

### 4.4 Phase 2: Debate Rounds
**Method**: `_phase_2_debate_rounds()`

- [ ] Implement round loop (default: 2 rounds)
- [ ] Turn 1: factchecker_a defense + offense
- [ ] Turn 2: debator_a rebuttal targeting frontier
- [ ] Turn 3: factchecker_b defense + offense
- [ ] Turn 4: debator_b rebuttal targeting frontier
- [ ] Turn 5: judge updates frontier
- [ ] Turn 6: crowd votes

**Tests**: `tests/e2e/test_phase_2.py`
- [ ] Test multiple rounds
- [ ] Test frontier targeting
- [ ] Test fact checker cross-fire

### 4.5 Phase 3: Closing
**Method**: `_phase_3_closing()`

- [ ] Turn 1: factchecker_a/b final verification
- [ ] Turn 2: debator_a closing statement
- [ ] Turn 3: debator_b closing statement
- [ ] Turn 4: judge final report
- [ ] Turn 5: crowd final vote
- [ ] Enforce no new citations

**Tests**: `tests/e2e/test_phase_3.py`
- [ ] Test closing phase
- [ ] Test citation constraint enforcement
- [ ] Test final outputs

---

## Phase 5: Output Generation (Week 5)

### Goal: Generate all final artifacts

### 5.1 Transcript Generator
**File**: `src/outputs/transcript_generator.py`

- [ ] Implement `generate_transcript()` method
- [ ] Convert citation keys to hyperlinks
- [ ] Format as readable Markdown
- [ ] Include metadata header

**Tests**: `tests/unit/test_transcript_generator.py`
- [ ] Test Markdown formatting
- [ ] Test citation link conversion
- [ ] Test output file creation

### 5.2 Ledger Generator
**File**: `src/outputs/ledger_generator.py`

- [ ] Implement `generate_ledger()` method
- [ ] Format citation_pool as final JSON
- [ ] Add summary statistics

**Tests**: `tests/unit/test_ledger_generator.py`
- [ ] Test JSON formatting
- [ ] Test statistics calculation

### 5.3 Logic Map Generator
**File**: `src/outputs/logic_map_generator.py`

- [ ] Implement `generate_logic_map()` method
- [ ] Format debate_latent as final JSON
- [ ] Visualize frontier evolution

**Tests**: `tests/unit/test_logic_map_generator.py`
- [ ] Test JSON formatting
- [ ] Test frontier tracking

### 5.4 Sentiment Graph Generator
**File**: `src/outputs/sentiment_generator.py`

- [ ] Implement `generate_sentiment_graph()` method
- [ ] Convert crowd_opinion to CSV
- [ ] Calculate aggregate statistics

**Tests**: `tests/unit/test_sentiment_generator.py`
- [ ] Test CSV formatting
- [ ] Test statistics calculation

---

## Phase 6: Integration & Testing (Week 6)

### Goal: End-to-end testing and refinement

### 6.1 Full Debate E2E Test
- [ ] Run complete debate with real APIs (mocked initially)
- [ ] Verify all outputs generated correctly
- [ ] Test error recovery
- [ ] Test performance with full crowd

### 6.2 System Prompt Tuning
- [ ] Test debate quality
- [ ] Refine agent prompts based on outputs
- [ ] Ensure agents follow instructions
- [ ] Ensure citation format compliance

### 6.3 Error Handling
- [ ] Add retry logic for API failures
- [ ] Add graceful degradation
- [ ] Add comprehensive logging
- [ ] Add progress indicators

### 6.4 Performance Optimization
- [ ] Profile bottlenecks
- [ ] Optimize file I/O
- [ ] Optimize LLM calls (caching, batching)
- [ ] Optimize Lambda GPU inference

---

## Phase 7: Deployment & Infrastructure (Week 7)

### Goal: Deploy crowd on Lambda GPU and finalize

### 7.1 Lambda GPU Setup
- [ ] Deploy Llama 3.1 8B on Lambda GPU
- [ ] Setup vLLM for fast inference
- [ ] Test batch inference
- [ ] Monitor costs

### 7.2 Main Entry Point
**File**: `main.py`

- [ ] Implement CLI interface
- [ ] Add topic input
- [ ] Add configuration options
- [ ] Add progress display
- [ ] Add result summary

### 7.3 Documentation
- [ ] Update README with usage instructions
- [ ] Document API configuration
- [ ] Add example outputs
- [ ] Add troubleshooting guide

### 7.4 First Real Debate
- [ ] Pick a test topic
- [ ] Run complete debate
- [ ] Review outputs
- [ ] Refine based on results

---

## Incremental Milestones

### Milestone 1: File System Works (End of Week 1)
✅ Can read/write JSON with permissions
✅ All unit tests pass

### Milestone 2: Agents Can Execute Turns (End of Week 3)
✅ Each agent type can execute its specific task
✅ Integration tests pass

### Milestone 3: Opening Phase Works (Mid Week 4)
✅ Can run Phase 0 and Phase 1 successfully
✅ All files updated correctly

### Milestone 4: Full Debate Works (End of Week 4)
✅ Can run complete debate from start to finish
✅ All outputs generated

### Milestone 5: Production Ready (End of Week 7)
✅ Deployed on Lambda GPU
✅ Real debates producing quality output
✅ Error handling robust

---

## Success Metrics

### Code Quality
- [ ] 80%+ test coverage
- [ ] All tests passing
- [ ] No linter errors
- [ ] Type hints throughout

### Debate Quality
- [ ] Coherent arguments
- [ ] Real citations with URLs
- [ ] Valid verification scores
- [ ] Clear frontier identification
- [ ] Diverse crowd opinions

### Performance
- [ ] Complete debate in < 10 minutes
- [ ] Cost < $2 per debate
- [ ] No API failures with retry logic

---

## Next Immediate Steps

**Ready to start building?**

1. **Create project structure** (5 min)
2. **Setup requirements.txt** (5 min)
3. **Implement FileManager** (2-3 hours)
4. **Write file manager tests** (1-2 hours)
5. **Test until green** ✅

**Should I start with Step 1?**
