# AI Debate Platform — Debate Flow Schematics

This document describes the architecture and provides visual schematics of the debate flow. Use a Mermaid-compatible viewer (GitHub, VS Code, or [mermaid.live](https://mermaid.live)) to render the diagrams.

---

## 1. High-Level Architecture

The platform is organized in **layers**: the Moderator orchestrates everything; agents never talk to each other directly—they read/write through the Moderator and the File Manager.

```
┌─────────────────────────────────────────────────────────┐
│                    Moderator Layer                       │
│         (Orchestration, State Machine, Checkpoints)      │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                 Agent ↔ Moderator Protocol               │
│     AgentContext (in) → Agent → AgentResponse (out)       │
│     File updates applied only by Moderator               │
└─────────────────────────────────────────────────────────┘
                            │
            ┌───────────────┼───────────────┐
            ▼               ▼               ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│  Agent Layer    │ │  File Manager    │ │  State Manager   │
│  6 agent types  │ │  Permission-based│ │  Phase, round,   │
│  (read-only I/O)│ │  read/write JSON │ │  turn, teams     │
└─────────────────┘ └─────────────────┘ └─────────────────┘
                            │
                            ▼
                  ┌──────────────────┐
                  │  debates/{id}/    │
                  │  *.json files    │
                  └──────────────────┘
```

**Principles:**
- **Immutable state from agents’ perspective**: Agents only read (via `read_for_agent`). All writes go through the Moderator using `FileManager.write_by_moderator` or specific methods like `append_turn`, `add_citation`, etc.
- **Permission matrix**: Each agent sees only what it’s allowed to (e.g. judge sees `public_transcript` only; debators see their team’s notes; crowd does not see citation pool in default config).
- **Single writer**: Only the Moderator applies `FileUpdate` operations returned by agents.

---

## 2. Debate Phase State Machine

Phases advance strictly in order. No skipping or going back.

```mermaid
stateDiagram-v2
    [*] --> initialization
    initialization --> opening : Vote 0 done, teams assigned
    opening --> debate_rounds : Both openings + factcheck + judge
    debate_rounds --> closing : N rounds complete
    closing --> completed : Final judge + final crowd vote
    completed --> [*]
```

**Phase summary:**

| Phase | Purpose |
|-------|--------|
| **initialization** | Create debate dir, generate crowd personas, run **Vote 0** (stance preference), assign teams (winner → Team A), set resource multiplier, create all agents |
| **opening** | Round 1: Debator A → crowd vote → FactChecker B → Debator B → crowd vote → FactChecker A → Judge (frontier map) |
| **debate_rounds** | Rounds 2..N: For each round — FactChecker A → Debator A → crowd → FactChecker B → Debator B → crowd → Judge |
| **closing** | Final factcheck (both) → Debator A closing → crowd → Debator B closing → crowd → Judge final report → Final crowd vote |
| **completed** | Generate outputs (transcript, citation ledger, logic map, sentiment CSV) |

---

## 3. End-to-End Debate Flow (Sequence)

End-to-end flow from topic to outputs:

```mermaid
sequenceDiagram
    participant User
    participant run_debate as run_debate.py
    participant Mod as DebateModerator
    participant FM as FileManager
    participant Agents as Agents (debator_a/b, factchecker_a/b, judge, crowd)

    User->>run_debate: Topic + optional --predict-cost
    run_debate->>Mod: DebateModerator(topic, config)
    run_debate->>Mod: await run_debate()

    Note over Mod: Phase 0: Initialization
    Mod->>FM: initialize_files()
    Mod->>Agents: CrowdAgent (temp): Vote 0
    Agents-->>Mod: AgentResponse (ADD_CROWD_VOTE)
    Mod->>FM: apply file updates
    Mod->>Mod: assign_teams(), calculate_resource_multiplier()
    Mod->>Mod: _initialize_agents(team_a_stance, team_b_stance)
    Mod->>Mod: state.transition_to(OPENING)

    Note over Mod: Phase 1: Opening
    loop For each turn in opening sequence
        Mod->>Agents: execute_agent_turn(agent_name, context_params)
        Agents->>FM: read_for_agent(name, file_type)
        FM-->>Agents: filtered state
        Agents-->>Mod: AgentResponse (output + file_updates)
        Mod->>FM: _apply_file_update(update) for each update
        Mod->>Mod: state.next_turn(agent_name)
    end
    Mod->>Mod: state.transition_to(DEBATE_ROUNDS)

    Note over Mod: Phase 2: Debate Rounds (N rounds)
    loop Each round
        loop Turn order: factchecker_a, debator_a, crowd, factchecker_b, debator_b, crowd, judge
            Mod->>Agents: execute_agent_turn(...)
            Agents-->>Mod: AgentResponse
            Mod->>FM: apply updates, next_turn
        end
    end
    Mod->>Mod: state.transition_to(CLOSING)

    Note over Mod: Phase 3: Closing
    loop Closing sequence (factchecks, closings, votes, judge, final vote)
        Mod->>Agents: execute_agent_turn(...)
        Agents-->>Mod: AgentResponse
        Mod->>FM: apply updates
    end
    Mod->>Mod: state.transition_to(COMPLETED)

    Note over Mod: Output generation
    Mod->>FM: read_for_agent("moderator", ...)
    Mod->>Mod: _generate_transcript, _generate_citation_ledger, _generate_logic_map, _generate_sentiment_graph

    Mod-->>run_debate: debate_id
    run_debate-->>User: Print summary + output paths
```

---

## 4. Single-Turn Flow (Execute Agent Turn)

What happens on every `execute_agent_turn(agent_name, context_params)`:

```mermaid
sequenceDiagram
    participant Mod as DebateModerator
    participant Agent
    participant FM as FileManager
    participant LLM as OpenRouter / LLM API

    Mod->>Mod: Build instructions (incl. scoreboard for debators)
    Mod->>Agent: context = AgentContext(state=agent.read_state(), ...)
    Agent->>FM: read_for_agent(name, "history_chat" | "citation_pool" | "debate_latent" | "crowd_opinion")
    FM-->>Agent: Permission-filtered state
    Agent->>LLM: generate(...) [possibly multiple calls, e.g. Deep Research]
    LLM-->>Agent: model response(s)
    Agent->>Agent: Parse response, build FileUpdate list
    Agent-->>Mod: AgentResponse(success, output, file_updates, errors)
    Mod->>Mod: Validate response, log turn
    loop For each FileUpdate
        Mod->>FM: _apply_file_update(update) → append_turn / add_citation / update_verification / etc.
    end
    Mod->>Mod: state.next_turn(agent_name), completed_turns.append(...)
    Mod->>Mod: _save_checkpoint() if _should_checkpoint()
```

---

## 5. Opening Phase — Turn Order (Round 1)

Exact sequence in Phase 1:

```mermaid
flowchart LR
    subgraph Opening["Phase 1: Opening (Round 1)"]
        A1[debator_a opening]
        V1[crowd vote]
        F2[factchecker_b verify A]
        B1[debator_b opening]
        V2[crowd vote]
        F1[factchecker_a verify B]
        J1[judge analyze + frontier]
        A1 --> V1 --> F2 --> B1 --> V2 --> F1 --> J1
    end
```

---

## 6. Debate Round (Phase 2) — One Round

One full debate round (repeated `num_debate_rounds` times):

```mermaid
flowchart LR
    subgraph Round["One debate round (e.g. Round 2)"]
        FA[factchecker_a]
        DA[debator_a]
        VA[crowd vote]
        FB[factchecker_b]
        DB[debator_b]
        VB[crowd vote]
        J[judge update frontier]
        FA --> DA --> VA --> FB --> DB --> VB --> J
    end
```

---

## 7. Closing Phase — Turn Order

```mermaid
flowchart LR
    subgraph Closing["Phase 3: Closing"]
        F1[factchecker_a final]
        F2[factchecker_b final]
        A[debator_a closing]
        VA[crowd vote]
        B[debator_b closing]
        VB[crowd vote]
        J[judge final report]
        VF[crowd final vote]
        F1 --> F2 --> A --> VA --> B --> VB --> J --> VF
    end
```

---

## 8. Data Flow (Files and Permissions)

Agents read through the File Manager; only the Moderator writes.

```mermaid
flowchart TB
    subgraph Files["debates/{id}/"]
        HC[history_chat.json]
        CP[citation_pool.json]
        DL[debate_latent.json]
        CO[crowd_opinion.json]
        PER[personas.json]
    end

    subgraph Agents["Agents (read via read_for_agent)"]
        DA[debator_a]
        DB[debator_b]
        FA[factchecker_a]
        FB[factchecker_b]
        JU[judge]
        CR[crowd]
    end

    Mod[Moderator]
    Mod -->|write_by_moderator / append_turn / add_citation / etc.| HC
    Mod --> CP
    Mod --> DL
    Mod --> CO
    Mod --> PER

    DA -->|public_transcript + team_notes.a| HC
    DA -->|all teams| CP
    DA -->|all| DL
    DB -->|public_transcript + team_notes.b| HC
    DB --> CP
    DB --> DL
    FA -->|public + team_notes.a| HC
    FA --> CP
    FB -->|public + team_notes.b| HC
    FB --> CP
    JU -->|public_transcript only| HC
    JU --> CP
    JU --> DL
    CR -->|public_transcript| HC
    CR -->|all| DL
```

---

## 9. Checkpoint and Resume

Checkpoints are saved after expensive or critical steps so the debate can be resumed without re-running prior LLM calls.

```mermaid
flowchart LR
    subgraph CheckpointTriggers["When checkpoint is saved"]
        V0[After Vote 0]
        Deb[After each debator turn]
        Crowd[After each crowd vote]
        Judge[After each judge turn]
    end

    CP[moderator_checkpoint.json]
    V0 --> CP
    Deb --> CP
    Crowd --> CP
    Judge --> CP

    CP --> Resume[resume_debate.py / DebateModerator.resume_from_checkpoint]
    Resume --> Continue[Continue from next phase/turn]
```

---

## 10. Output Artifacts (After COMPLETED)

Generated under `debates/{id}/outputs/`:

| File | Source data | Description |
|------|-------------|-------------|
| `transcript_full.md` | history_chat | Human-readable transcript (public + optional team notes) |
| `citation_ledger.json` | citation_pool | All citations with verification scores |
| `debate_logic_map.json` | debate_latent | Frontier / round history from judge |
| `voter_sentiment_graph.csv` | crowd_opinion | Per-round, per-voter scores for sentiment analysis |

---

## Summary

- **One orchestrator**: `DebateModerator` runs the state machine and every agent turn.
- **Strict phase order**: initialization → opening → debate_rounds → closing → completed.
- **Turn order** is fixed per phase (see diagrams above); agents never speak out of order.
- **State lives in JSON files**; agents read via permission-aware `FileManager`, and only the Moderator writes.
- **Recovery**: checkpoints after Vote 0, debator turns, crowd votes, and judge turns enable resume via `resume_debate.py`.

Use these schematics for onboarding or to reason about changes to the debate flow (e.g. adding a phase or a new agent type).
