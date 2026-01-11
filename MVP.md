# AI Debate Platform - MVP Specification

**Version:** 2.0  
**Author:** Dong Chen  
**Date:** January 2026  
**Status:** Engineering Ready

---

## Executive Summary

This project establishes the Minimum Viable Product (MVP) for an AI-driven debating platform designed to simulate high-fidelity, text-based argumentation between two agents (a and b) on complex social topics.

Unlike standard generative chat models, this system introduces:
- **Adversarial Verification**: Fact-checker agents aligned with each debater to ensure rigorous cross-examination
- **Latent Space Mapping**: A neutral "Judge" agent maps the logical evolution of the debate, preventing circular arguments
- **Dynamic Resource Allocation**: Adjusts time/word count based on pre-existing audience bias to ensure balanced, educational presentation of facts (akin to a presidential debate transcript)

---

## 1. Strategic Framework

### 1.1 Core Concept & Objectives

The system is built to achieve three primary goals:

1. **Rigorous Cross-Examination**
   - Moving beyond "chatbot vs. chatbot" by weaponizing fact-checkers to provide "ammunition" for rebuttals

2. **Logical Progression**
   - Using a neutral "Judge" to explicitly define the "Disagreement Frontier," forcing agents to move the argument forward rather than repeating talking points

3. **Bias Calibration**
   - Gamifying the context window to account for the inherent difficulty of defending minority opinions

### 1.2 System Configuration & "Knobs"

To simulate different debating environments, the system utilizes variable parameters:

#### A. Model Capacity Tuning (The "Intelligence" Knob)

- **Default**: Equal Capacity (e.g., Gemini 1.5 Pro vs. Gemini 1.5 Pro)
- **Asymmetric Scenarios**:
  - **David vs. Goliath**: High-Capacity Proponent vs. Lower-Capacity Opponent
  - **Checker Dominance**: Low-capacity debaters supported by high-capacity verification agents

#### B. Audience Calibration (The "Time" Knob)

The system assumes a "Pre-Survey" state to balance the playing field.

- **Input**: Audience lean (e.g., 70% favor a)
- **Logic**: Defending a minority opinion requires more nuance and evidence
- **Adjustment**:
  - If Audience Lean > 60% for one side, the opposing side receives a **1.25x multiplier** on word count limits and citation allowances
  - Neutral (45-55%): Resources remain 1:1

### 1.3 Topic Selection Framework

Topics are selected based on specific suitability criteria for AI argumentation:

- **Data Density**: Must have abundant statistical data (avoiding purely abstract philosophy)
- **Policy Granularity**: Focus on implementation trade-offs (costs, logistics, efficacy)
- **Stakeholder Balance**: Must have clear winners/losers on both sides to fuel the "Crowd" personas

---

## 2. Agent Ecosystem

### 2.1 Central Controller

**Moderator (System Script)**
- The orchestration engine
- Executes the workflow state machine
- Manages permissions
- Triggers agents
- Updates the current state
- Logs actions
- Strictly enforces the "Knobs" defined in Section 1.2

### 2.2 The Debating Teams

#### Team a (First Speaker - Determined by Vote 0)

- **debator_a**
  - The primary speaker
  - Responsible for drafting Opening, Rebuttal, and Closing statements
  - Must link claims to the citation ledger using keys (e.g., `[a_1]`)
  - Citations are generated sequentially (e.g., `a_1`, `a_2`, `a_3`...)
  - Can only add citations during their turn
  - No limit on number of citations (word count and time limits to be implemented later)

- **factchecker_a**
  - **Offense**: Scrutinizes Team b's sources on two distinct metrics (Credibility & Correspondence)
  - **Defense**: Responds to adversarial scores left by factchecker_b
  - **Note**: Fact checkers can only verify existing citations; they cannot add new citations. No timeout - sequential execution until completion.

#### Team b (Second Speaker)

- **debator_b**
  - The second speaker
  - Responds to the topic and a's arguments
  - Citations are generated sequentially (e.g., `b_1`, `b_2`, `b_3`...)
  - Can only add citations during their turn
  - No limit on number of citations (word count and time limits to be implemented later)

- **factchecker_b**
  - **Offense**: Scrutinizes Team a's sources on two distinct metrics
  - **Defense**: Responds to adversarial scores left by factchecker_a
  - **Note**: Fact checkers can only verify existing citations; they cannot add new citations. No timeout - sequential execution until completion.

### 2.3 The Evaluators

- **The Judge (Latent Space Cartographer)**
  - A neutral LLM-based analyst (no algorithmic determination)
  - Analyzes the state of the debate to output the "Disagreement Frontier" and "Consensus" at medium level of detail
  - Does not decide "who won," but rather "what is left to argue"
  - System prompt will contain detailed instructions for determining the disagreement frontier

- **The Crowd (Voting Swarm)**
  - A collection of N (e.g., 100) diverse LLM personas
  - Provides quantitative scoring (0-100) based on their specific system prompts (e.g., "Fiscal Conservative," "Progressive Reformer")
  - Personas persist across debates (implementation details to be handled later)

---

## 3. Data Infrastructure & Schemas

### 3.1 History Chat (`history_chat.json`)

The canonical transcript with separate public and private sections. Main statements are visible to all agents, while supplementary material is only visible to the corresponding team.

**Permissions**: Read (All for public_transcript, Team-specific for team_notes), Write (Moderator)

```json
{
  "debate_id": "uuid",
  "topic": "Should universal basic income be implemented?",
  "metadata": {
    "created_at": "2026-01-15T10:00:00Z",
    "phase": "Phase 2",
    "current_round": 2
  },
  "public_transcript": [
    {
      "turn_id": "turn_001",
      "round_number": 1,
      "round_label": "Opening",
      "phase": "Phase 1",
      "speaker": "a",
      "agent": "debator_a",
      "timestamp": "2026-01-15T10:00:00Z",
      "statement": "The economic impact is severe [a_1]...",
      "citations_used": ["a_1", "a_2"]
    },
    {
      "turn_id": "turn_002",
      "round_number": 1,
      "round_label": "Opening",
      "phase": "Phase 1",
      "speaker": "b",
      "agent": "debator_b",
      "timestamp": "2026-01-15T10:05:00Z",
      "statement": "The benefits outweigh the costs [b_1]...",
      "citations_used": ["b_1", "b_2"]
    }
  ],
  "team_notes": {
    "a": [
      {
        "turn_id": "turn_001",
        "round_number": 1,
        "supplementary_material": "XXX [a_11]...",
        "citations_used": ["a_11"],
        "timestamp": "2026-01-15T10:00:00Z"
      }
    ],
    "b": [
      {
        "turn_id": "turn_002",
        "round_number": 1,
        "supplementary_material": "YYY [b_11]...",
        "citations_used": ["b_11"],
        "timestamp": "2026-01-15T10:05:00Z"
      }
    ]
  }
}
```

**Visibility Rules**:
- `public_transcript`: Visible to all agents (debator_a, debator_b, factchecker_a, factchecker_b, Judge, Crowd)
- `team_notes.a`: Only visible to Team a (debator_a, factchecker_a)
- `team_notes.b`: Only visible to Team b (debator_b, factchecker_b)
- `supplementary_material` has no word limit but is not visible to the audience or opposing team

### 3.2 Citation Pool (`citation_pool.json`)

A transparent ledger of all claims and their verification status with enhanced structure for easy querying.

**Permissions**: Read (All agents), Write (debator_a, debator_b add items; factchecker_a, factchecker_b add scores)

```json
{
  "debate_id": "uuid",
  "citations": {
    "team a": {
      "a_1": {
        "source_url": "http://example.com/source1",
        "added_by": "debator_a",
        "added_in_turn": "turn_001",
        "added_in_round": 1,
        "added_at": "2026-01-15T10:00:00Z",
        "verification": {
          "source_credibility_score": 8,
          "content_correspondence_score": 9,
          "adversary_comment": "Source is reputable but outdated.",
          "proponent_response": "Data remains relevant.",
          "verified_by": "factchecker_b",
          "verified_at": "2026-01-15T10:05:00Z"
        }
      },
      "a_2": {
        "source_url": "http://example.com/source2",
        "added_by": "debator_a",
        "added_in_turn": "turn_001",
        "added_in_round": 1,
        "added_at": "2026-01-15T10:00:00Z",
        "verification": {
          "source_credibility_score": null,
          "content_correspondence_score": null,
          "adversary_comment": null,
          "proponent_response": null,
          "verified_by": null,
          "verified_at": null
        }
      }
    },
    "team b": {
      "b_1": {
        "source_url": "http://example.com/source3",
        "added_by": "debator_b",
        "added_in_turn": "turn_002",
        "added_in_round": 1,
        "added_at": "2026-01-15T10:05:00Z",
        "verification": {
          "source_credibility_score": 7,
          "content_correspondence_score": 8,
          "adversary_comment": "Methodology is questionable.",
          "proponent_response": "Peer-reviewed study.",
          "verified_by": "factchecker_a",
          "verified_at": "2026-01-15T10:10:00Z"
        }
      }
    }
  },
  "index_by_round": {
    "1": ["a_1", "a_2", "b_1"]
  }
}
```

**Notes**:
- Scores are on a scale of 1-10
- `verification` fields are `null` until a FactChecker verifies the citation
- Citations are organized by team (`citations.a`, `citations.b`) for easy team-specific queries
- `index_by_round` provides quick lookup capabilities for agents across all teams
- The `team` field is no longer needed in individual citations as it's implicit in the structure

### 3.3 Debate Latent Space (`debate_latent.json`)

The Judge's steering file. Defines the "topology" of the argument.

**Permissions**: Read (debator_a, debator_b, factchecker_a, factchecker_b, Crowd, Moderator), Write (Judge)

```json
{
  "round_history": [
    {
      "round_number": 1,
      "consensus": ["Both parties agree administrative costs are high."],
      "disagreement_frontier": [
        {
          "core_issue": "Impact on Innovation",
          "a_stance": "Consolidation spurs efficiency.",
          "b_stance": "Price controls stifle R&D."
        }
      ]
    }
  ]
}
```

### 3.4 Crowd Opinion (`crowd_opinion.json`)

Private score-keeping file tracking longitudinal opinion shifts.

**Permissions**: Read (Moderator ONLY), Write (Moderator)

```json
{
  "voters": [
    {
      "voter_id": "v_001",
      "persona": "Fiscal Conservative",
      "voting_record": [
        { "round_sequence": 0, "score": 30 },
        { "round_sequence": 1, "score": 45 }
      ]
    }
  ]
}
```

---

## 4. Operational Workflow

### 4.1 Phase 0: Initialization

1. **Moderator Action**: Select Topic, Split Stances (For/Against)
2. **Vote Zero**: 
   - Crowd votes on stance preference (baseline belief state of audiences)
   - Winner determined by majority (number of people that favor that stance)
   - Winner becomes Team a
   - If tied, randomize the initial speaker
3. **Resource Allocation**: Moderator applies "Time Knob" multiplier if bias > 60%

### 4.2 Phase 1: The Opening (Round 1)

Sequential turn-taking logic applies. a acts first on an empty state.

- **Turn 1: Team a**
  - **Research**: debator_a analyzes topic
  - **Action**: Submits `main_statement` and initial citations

- **Turn 2: Team b**
  - **Cross-Fire (factchecker_b)**: Scrutinizes a's Opening citations
  - **Action**: debator_b submits `main_statement` and initial citations

- **Turn 3: Judge & Crowd**
  - **Assessment**: Judge generates initial `debate_latent.json`; Crowd casts Vote 1

### 4.3 Phase 2: The Debate Rounds (2, 3...)

**Default**: 2 rounds (preset, configurable)

Standard Loop: **Verify Previous → Speak New**

- **Turn 1: Team a**
  - **Cross-Fire (factchecker_a)**:
    - **Defense**: Responds to scores left by factchecker_b (sequential, no timeout)
    - **Offense**: Scrutinizes b's most recent citations (sequential, no timeout)
  - **Statement**: debator_a submits argument targeting the Judge's "Disagreement Frontier"
  - **Note**: Timeouts apply only to main statements (for presentation purposes)

- **Turn 2: Team b**
  - **Cross-Fire (factchecker_b)**:
    - **Defense**: Responds to scores left by factchecker_a (sequential, no timeout)
    - **Offense**: Scrutinizes a's most recent citations (sequential, no timeout)
  - **Statement**: debator_b submits argument targeting the "Disagreement Frontier"
  - **Note**: Timeouts apply only to main statements (for presentation purposes)

- **Turn 3: Judge & Crowd**
  - **Update**: Judge updates map; Crowd casts votes

### 4.4 Phase 3: The Closing

- **Constraint**: No new citations allowed
- **Final Cross-Fire**: Both factcheckers verify the final round of arguments from Phase 2
- **Closing Statements**: debator_a and debator_b provide summaries. No new arguments
- **Final Verdict**: Judge Final Report + Crowd Final Vote

---

## 5. Final Output Artifacts

The system generates four distinct artifacts to serve different analytical needs:

1. **`transcript_full.md` (The Narrative)**
   - A human-readable Markdown transcript of the entire debate, formatted for publishing
   - Converts internal citation keys into hyperlinks

2. **`citation_ledger.json` (The Facts)**
   - The complete, raw JSON database containing every claim made and its rigorous verification status (Credibility & Correspondence scores)

3. **`debate_logic_map.json` (The Logic)**
   - A JSON array tracking how the argument's "Latent Space" evolved round-by-round
   - Visualizes how the consensus grew and the disagreement frontier narrowed

4. **`voter_sentiment_graph.csv` (The Score)**
   - A raw CSV dataset recording the quantitative scoring from the 100-persona crowd across all rounds
   - Enables time-series analysis

---
