"""
Debate Moderator - Orchestrates the complete debate workflow.

The Moderator is the "brain" of the debate platform:
- Coordinates 6 agents across 4 phases
- Manages state transitions and turn sequencing
- Applies file updates from agents
- Provides crash recovery via checkpoints
- Generates final outputs

Author: AI Debate Platform Team
Date: January 2026
"""

import asyncio
import json
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.agents.base import Agent, AgentContext, AgentResponse, FileUpdate, FileUpdateOperation
from src.agents.crowd import CrowdAgent
from src.agents.debator import DebatorAgent
from src.agents.factchecker import FactCheckerAgent
from src.agents.judge import JudgeAgent
from src.config import Config
from src.utils.file_manager import FileManager
from src.utils.state_manager import DebatePhase, DebateState
from src.utils.debate_logger import DebateLogger
from src.utils.raw_data_logger import RawDataLogger


class DebateModerator:
    """
    Orchestrates the complete debate workflow.
    
    Responsibilities:
    - Initialize debate and all agents
    - Execute phases in correct sequence
    - Coordinate agent turns
    - Apply file updates
    - Save checkpoints for crash recovery
    - Generate final outputs
    """
    
    def __init__(self, topic: str, config: Config, debate_id: Optional[str] = None):
        """
        Initialize a new debate.
        
        Args:
            topic: The debate topic/resolution
            config: Configuration object with API keys and settings
            debate_id: Optional debate ID (for resume), generates new if None
        """
        self.debate_id = debate_id or str(uuid.uuid4())
        self.topic = topic
        self.config = config
        
        # Setup directories and managers
        self.debate_dir = Path(f"debates/{self.debate_id}")
        self.file_manager = FileManager(str(self.debate_dir))
        
        # Initialize loggers
        self.logger = DebateLogger(self.debate_id, self.debate_dir)
        self.raw_data_logger = RawDataLogger(self.debate_id, str(self.debate_dir))
        
        # Initialize state
        self.state = DebateState(self.debate_id, topic)
        
        # Track execution
        self.completed_turns: List[Dict[str, Any]] = []
        self.total_cost: float = 0.0
        
        # Agents (initialized after Vote 0 determines stances)
        self.agents: Dict[str, Agent] = {}
    
    async def run_debate(self) -> str:
        """
        Execute the complete debate workflow.
        
        Phases:
        0. Initialization - Vote 0, team assignment, resource allocation
        1. Opening - Both sides present opening statements
        2. Debate Rounds - Iterative rebuttals (default: 2 rounds)
        3. Closing - Final statements and evaluation
        
        Returns:
            debate_id for accessing outputs
        """
        print(f"\n{'='*60}")
        print(f"🎭 DEBATE STARTING")
        print(f"{'='*60}")
        print(f"Topic: {self.topic}")
        print(f"Debate ID: {self.debate_id}")
        print(f"{'='*60}\n")
        
        self.logger.log_moderator_action(
            action="debate_started",
            details={
                "topic": self.topic,
                "debate_id": self.debate_id,
                "config": {
                    "num_rounds": self.config.num_debate_rounds,
                    "crowd_size": self.config.crowd_size
                }
            }
        )
        
        try:
            # Execute phases based on current state
            # Skip phases that have already been completed (for resume)
            phase_order = ["initialization", "opening", "debate_rounds", "closing", "completed"]
            current_phase_index = phase_order.index(self.state.phase.value)
            
            # Phase 0: Initialization
            if current_phase_index < 1:
                await self._phase_0_initialization()
            
            # Phase 1: Opening
            if current_phase_index < 2:
                await self._phase_1_opening()
            
            # Phase 2: Debate Rounds
            if current_phase_index < 3:
                await self._phase_2_debate_rounds()
            
            # Phase 3: Closing
            if current_phase_index < 4:
                await self._phase_3_closing()
            
            # Generate outputs (always run if phase is completed)
            await self._generate_outputs()
            
            print(f"\n{'='*60}")
            print(f"✅ DEBATE COMPLETED")
            print(f"{'='*60}")
            print(f"Total Turns: {self.state.turn_count}")
            print(f"Total Cost: ${self.total_cost:.2f}")
            print(f"Outputs: debates/{self.debate_id}/outputs/")
            print(f"{'='*60}\n")
            
            return self.debate_id
            
        except Exception as e:
            print(f"\n❌ Debate failed: {e}")
            print(f"💾 Checkpoint saved at: debates/{self.debate_id}/moderator_checkpoint.json")
            print(f"Resume with: DebateModerator.resume_from_checkpoint('{self.debate_id}')")
            raise
    
    @classmethod
    async def resume_from_checkpoint(cls, debate_id: str, config: Config) -> "DebateModerator":
        """
        Resume debate from checkpoint file.
        
        Used to recover from crashes without re-running expensive API calls.
        
        Args:
            debate_id: ID of debate to resume
            config: Configuration object
            
        Returns:
            DebateModerator instance ready to continue
            
        Raises:
            FileNotFoundError: If checkpoint doesn't exist
        """
        checkpoint_path = Path(f"debates/{debate_id}/moderator_checkpoint.json")
        
        if not checkpoint_path.exists():
            raise FileNotFoundError(
                f"No checkpoint found for debate {debate_id}\n"
                f"Expected: {checkpoint_path}"
            )
        
        print(f"\n{'='*60}")
        print(f"♻️  RESUMING FROM CHECKPOINT")
        print(f"{'='*60}")
        
        with open(checkpoint_path) as f:
            checkpoint = json.load(f)
        
        # Reconstruct moderator state
        moderator = cls.__new__(cls)
        moderator.debate_id = debate_id
        moderator.topic = checkpoint["topic"]
        moderator.config = config
        
        # Reconstruct state
        moderator.state = DebateState.from_checkpoint(checkpoint["state"])
        moderator.completed_turns = checkpoint["completed_turns"]
        moderator.total_cost = checkpoint["costs"]["total"]
        
        # Reinitialize managers and agents
        moderator.debate_dir = Path(f"debates/{debate_id}")
        moderator.file_manager = FileManager(str(moderator.debate_dir))
        
        # Initialize loggers
        moderator.logger = DebateLogger(moderator.debate_id, moderator.debate_dir)
        moderator.raw_data_logger = RawDataLogger(moderator.debate_id, str(moderator.debate_dir))
        
        moderator.agents = moderator._initialize_agents(
            team_a_stance=checkpoint["state"]["team_assignments"]["team_a"]["stance"],
            team_b_stance=checkpoint["state"]["team_assignments"]["team_b"]["stance"]
        )
        
        last_turn = checkpoint["completed_turns"][-1] if checkpoint["completed_turns"] else None
        print(f"Topic: {moderator.topic}")
        print(f"Last turn: {last_turn['agent'] if last_turn else 'None'}")
        print(f"Turn count: {moderator.state.turn_count}")
        print(f"Cost so far: ${moderator.total_cost:.2f}")
        print(f"{'='*60}\n")
        
        return moderator
    
    # ========================================================================
    # PHASE EXECUTION
    # ========================================================================
    
    async def _phase_0_initialization(self) -> None:
        """
        Phase 0: Initialize debate.
        
        Steps:
        1. Create debate directory and JSON files
        2. Generate topic-relevant crowd personas via LLM
        3. Run Vote 0 (crowd votes on stance preference)
        4. Determine team assignments (winner → team a)
        5. Calculate resource multiplier if bias exists
        6. Initialize all agents with assigned stances
        7. Transition to OPENING phase
        """
        print(f"\n{'='*60}")
        print(f"📋 PHASE 0: INITIALIZATION")
        print(f"{'='*60}\n")
        
        # 1. Create directory and initialize files
        self.debate_dir.mkdir(parents=True, exist_ok=True)
        self.file_manager.initialize_files(self.debate_id, self.topic)
        print("✅ Debate files initialized")
        
        # 2. Generate topic-relevant personas
        print("🧑‍🤝‍🧑 Generating crowd personas...")
        personas = await self._generate_crowd_personas(self.topic, self.config.crowd_size)
        print(f"✅ Generated {len(personas)} personas with topic-relevant dimensions")
        
        # Store personas in crowd_opinion for persistence
        crowd_data = self.file_manager._read_json("crowd_opinion")
        crowd_data["personas"] = personas
        self.file_manager.write_by_moderator("crowd_opinion", crowd_data)
        
        # 3. Run Vote 0 with generated personas
        temp_crowd = CrowdAgent(
            name="crowd",
            file_manager=self.file_manager,
            config=self.config,
            raw_data_logger=self.raw_data_logger,
            personas=personas
        )
        
        vote_zero_context = AgentContext(
            debate_id=self.debate_id,
            topic=self.topic,
            phase="initialization",
            round_number=0,
            current_state={},
            instructions="Vote on your initial stance preference (FOR or AGAINST)"
        )
        
        print("🗳️  Running Vote 0 (stance preference)...")
        vote_zero_response = await temp_crowd.execute_turn(vote_zero_context)
        
        if not vote_zero_response.success:
            raise Exception(f"Vote 0 failed: {vote_zero_response.errors}")
        
        for update in vote_zero_response.file_updates:
            self._apply_file_update(update)
        
        # Initialize journals with life experience intros
        crowd_data = self.file_manager._read_json("crowd_opinion")
        for voter in crowd_data.get("voters", []):
            persona = next((p for p in personas if p["id"] == voter["voter_id"]), None)
            if persona:
                life_exp = persona.get("life_experience", persona.get("description", ""))
                baseline_score = voter.get("voting_history", [{}])[0].get("score", "?") if voter.get("voting_history") else "?"
                voter["journal"] = f"## About Me\n{life_exp}\n\n## Initial Stance (Score: {baseline_score})\n{voter.get('voting_history', [{}])[0].get('rationale', '')}"
        self.file_manager.write_by_moderator("crowd_opinion", crowd_data)
        
        # 4. Process Vote 0 results
        votes = vote_zero_response.output["votes"]
        avg_score = vote_zero_response.output["average_score"]
        
        for_count = sum(1 for v in votes if v["score"] > 50)
        against_count = len(votes) - for_count
        
        print(f"   FOR: {for_count} votes")
        print(f"   AGAINST: {against_count} votes")
        print(f"   Average score: {avg_score:.1f}")
        
        # 5. Assign teams
        self.state.assign_teams(
            for_stance="for",
            against_stance="against",
            vote_results={"for": for_count, "against": against_count}
        )
        
        self.logger.log_moderator_action(
            action="vote_0_completed",
            details={
                "for_count": for_count,
                "against_count": against_count,
                "average_score": avg_score,
                "team_assignments": self.state.team_assignments
            }
        )
        
        print(f"   Team A: {self.state.team_assignments['team_a']['stance'].upper()}")
        print(f"   Team B: {self.state.team_assignments['team_b']['stance'].upper()}")
        
        # 6. Calculate resource multiplier
        self.state.calculate_resource_multiplier(
            vote_results={"for": for_count, "against": against_count},
            threshold=self.config.resource_multiplier_threshold
        )
        
        if self.state.resource_multiplier > 1.0:
            losing_team = "b" if for_count > against_count else "a"
            print(f"   Resource multiplier: {self.state.resource_multiplier:.2f}x (team {losing_team})")
        
        # 7. Initialize all agents with correct stances (pass personas to crowd)
        team_a_stance = self.state.team_assignments['team_a']['stance']
        team_b_stance = self.state.team_assignments['team_b']['stance']
        self._generated_personas = personas
        self.agents = self._initialize_agents(team_a_stance, team_b_stance)
        print("✅ All agents initialized")
        
        self._save_checkpoint()
        
        # 8. Transition to opening
        self.state.transition_to(DebatePhase.OPENING)
        self.logger.log_moderator_action(
            action="phase_transition",
            details={"from": "initialization", "to": "opening"},
            state_snapshot=self.state.to_dict()
        )
        print(f"\n✅ Phase 0 complete\n")
    
    async def _generate_crowd_personas(self, topic: str, crowd_size: int) -> List[Dict[str, Any]]:
        """
        Generate topic-relevant crowd personas using an LLM.
        
        The moderator defines dimensions relevant to the debate topic,
        then creates diverse personas with unique life experiences.
        """
        from src.clients.openrouter_client import OpenRouterClient
        
        client = OpenRouterClient(
            api_key=self.config.openrouter_api_key,
            raw_data_logger=self.raw_data_logger
        )
        
        num_templates = min(crowd_size, 20)
        
        prompt = f"""You are designing a diverse audience for a debate on: "{topic}"

Generate exactly {num_templates} unique voter personas. Each persona must feel like a real person with a specific life experience that shapes their perspective on this topic.

REQUIREMENTS:
1. First, identify 4-6 dimensions RELEVANT TO THIS TOPIC (not generic). Each dimension should have 3-5 levels (NOT binary).
2. Distribute personas across these dimensions for maximum diversity.
3. Each persona needs a unique name, age, and a 1-paragraph life experience (2-3 sentences) that explains WHY they might lean a certain way on this topic.
4. The life experiences should be specific and personal, not generic descriptions.

Return a JSON object:
{{
  "dimensions": {{
    "dimension_name": ["level1", "level2", "level3", ...],
    ...
  }},
  "personas": [
    {{
      "name": "First Last, age",
      "type": "dimension_category",
      "dimensions": {{"dim1": "level", "dim2": "level", ...}},
      "life_experience": "1 paragraph personal backstory relevant to the topic..."
    }},
    ...
  ]
}}"""
        
        try:
            model = self.config.gemini_model
            response = await client.generate(
                prompt=prompt,
                model=model,
                temperature=0.9,
                max_tokens=4096
            )
            
            from src.utils.json_parser import parse_json_response
            result = parse_json_response(response)
            
            dimensions = result.get("dimensions", {})
            raw_personas = result.get("personas", [])
            
            if not raw_personas:
                print("⚠️  LLM returned no personas, falling back to defaults")
                return self._fallback_personas(crowd_size)
            
            personas = []
            for i in range(crowd_size):
                template = raw_personas[i % len(raw_personas)]
                suffix = f" (#{i // len(raw_personas) + 1})" if crowd_size > len(raw_personas) and i >= len(raw_personas) else ""
                personas.append({
                    "id": f"v_{i+1:03d}",
                    "name": f"{template['name']}{suffix}",
                    "type": template.get("type", "general"),
                    "dimensions": template.get("dimensions", {}),
                    "life_experience": template.get("life_experience", ""),
                    "description": template.get("life_experience", "")
                })
            
            return personas
            
        except Exception as e:
            print(f"⚠️  Persona generation failed: {e}. Using defaults.")
            return self._fallback_personas(crowd_size)
    
    def _fallback_personas(self, crowd_size: int) -> List[Dict[str, Any]]:
        """Fallback to hardcoded persona templates."""
        temp_crowd = CrowdAgent(
            name="crowd",
            file_manager=self.file_manager,
            config=self.config,
            raw_data_logger=self.raw_data_logger
        )
        return temp_crowd.personas
    
    async def _phase_1_opening(self) -> None:
        """
        Phase 1: Opening statements.
        
        Turn sequence:
        1. debator_a: Research + generate opening
        2. crowd: Vote after debator_a speaks
        3. factchecker_b: Verify a's citations (offensive)
        4. debator_b: Research + generate opening
        5. crowd: Vote after debator_b speaks
        6. factchecker_a: Verify b's citations (offensive)
        7. judge: Analyze both openings, map frontier
        """
        print(f"\n{'='*60}")
        print(f"🎤 PHASE 1: OPENING STATEMENTS")
        print(f"{'='*60}\n")
        
        self.state.next_round()  # Round 1
        
        # Turn 1: debator_a opening
        await self.execute_agent_turn("debator_a", {
            "phase": "opening",
            "round_number": 1,
            "instructions": "Generate your opening statement with comprehensive research"
        })
        
        # Crowd votes after debator_a speaks
        await self.execute_agent_turn("crowd", {
            "phase": "opening",
            "round_number": 1,
            "instructions": "Vote after Team A's opening statement"
        })
        
        # Turn 2: factchecker_b verifies
        await self.execute_agent_turn("factchecker_b", {
            "phase": "opening",
            "round_number": 1,
            "instructions": "Verify opponent's citations (offensive fact-checking)"
        })
        
        # Turn 3: debator_b opening
        await self.execute_agent_turn("debator_b", {
            "phase": "opening",
            "round_number": 1,
            "instructions": "Generate your opening statement with comprehensive research"
        })
        
        # Crowd votes after debator_b speaks
        await self.execute_agent_turn("crowd", {
            "phase": "opening",
            "round_number": 1,
            "instructions": "Vote after Team B's opening statement"
        })
        
        # Turn 4: factchecker_a verifies
        await self.execute_agent_turn("factchecker_a", {
            "phase": "opening",
            "round_number": 1,
            "instructions": "Verify opponent's citations (offensive fact-checking)"
        })
        
        # Turn 5: judge analyzes
        await self.execute_agent_turn("judge", {
            "phase": "opening",
            "round_number": 1,
            "instructions": "Analyze both opening statements and map disagreement frontier"
        })
        
        # Transition to debate rounds
        self.state.transition_to(DebatePhase.DEBATE_ROUNDS)
        self.logger.log_moderator_action(
            action="phase_transition",
            details={"from": "opening", "to": "debate_rounds"},
            state_snapshot=self.state.to_dict()
        )
        print(f"\n✅ Phase 1 complete\n")
    
    async def _phase_2_debate_rounds(self) -> None:
        """
        Phase 2: Debate rounds (iterative rebuttals).
        
        Each round:
        1. factchecker_a: Defense + Offense
        2. debator_a: Rebuttal targeting frontier
        3. crowd: Vote after debator_a speaks
        4. factchecker_b: Defense + Offense
        5. debator_b: Rebuttal targeting frontier
        6. crowd: Vote after debator_b speaks
        7. judge: Update frontier
        
        Default: 2 rounds (configurable)
        """
        print(f"\n{'='*60}")
        print(f"⚔️  PHASE 2: DEBATE ROUNDS")
        print(f"{'='*60}\n")
        
        num_rounds = self.config.num_debate_rounds
        print(f"Executing {num_rounds} debate rounds...\n")
        
        for i in range(num_rounds):
            round_num = 2 + i  # Rounds 2, 3, etc.
            self.state.next_round()
            
            print(f"--- Round {round_num} ---\n")
            
            # Team a turn
            await self.execute_agent_turn("factchecker_a", {
                "phase": "rebuttal",
                "round_number": round_num,
                "instructions": "Defend your citations and verify opponent's new claims"
            })
            
            await self.execute_agent_turn("debator_a", {
                "phase": "rebuttal",
                "round_number": round_num,
                "instructions": "Generate rebuttal targeting disagreement frontier"
            })
            
            # Crowd votes after debator_a speaks
            await self.execute_agent_turn("crowd", {
                "phase": "rebuttal",
                "round_number": round_num,
                "instructions": "Vote after Team A's rebuttal"
            })
            
            # Team b turn
            await self.execute_agent_turn("factchecker_b", {
                "phase": "rebuttal",
                "round_number": round_num,
                "instructions": "Defend your citations and verify opponent's new claims"
            })
            
            await self.execute_agent_turn("debator_b", {
                "phase": "rebuttal",
                "round_number": round_num,
                "instructions": "Generate rebuttal targeting disagreement frontier"
            })
            
            # Crowd votes after debator_b speaks
            await self.execute_agent_turn("crowd", {
                "phase": "rebuttal",
                "round_number": round_num,
                "instructions": "Vote after Team B's rebuttal"
            })
            
            # Evaluation
            await self.execute_agent_turn("judge", {
                "phase": "rebuttal",
                "round_number": round_num,
                "instructions": "Update disagreement frontier based on new arguments"
            })
            
            print(f"✅ Round {round_num} complete\n")
        
        # Transition to closing
        self.state.transition_to(DebatePhase.CLOSING)
        self.logger.log_moderator_action(
            action="phase_transition",
            details={"from": "debate_rounds", "to": "closing"},
            state_snapshot=self.state.to_dict()
        )
        print(f"\n✅ Phase 2 complete\n")
    
    async def _phase_3_closing(self) -> None:
        """
        Phase 3: Closing statements.
        
        Sequence:
        1. factchecker_a: Final verification round
        2. factchecker_b: Final verification round
        3. debator_a: Closing statement (no new citations)
        4. crowd: Vote after debator_a's closing
        5. debator_b: Closing statement (no new citations)
        6. crowd: Vote after debator_b's closing
        7. judge: Final analysis and report
        8. crowd: Final vote after judge's analysis
        """
        print(f"\n{'='*60}")
        print(f"🏁 PHASE 3: CLOSING STATEMENTS")
        print(f"{'='*60}\n")
        
        final_round = self.state.round_number + 1
        self.state.next_round()
        
        # Final fact-checking
        await self.execute_agent_turn("factchecker_a", {
            "phase": "closing",
            "round_number": final_round,
            "instructions": "Final verification of all citations"
        })
        
        await self.execute_agent_turn("factchecker_b", {
            "phase": "closing",
            "round_number": final_round,
            "instructions": "Final verification of all citations"
        })
        
        # Closing statements (no new research) with crowd voting after each
        await self.execute_agent_turn("debator_a", {
            "phase": "closing",
            "round_number": final_round,
            "instructions": "Generate closing statement (no new citations allowed)"
        })
        
        # Crowd votes after debator_a's closing
        await self.execute_agent_turn("crowd", {
            "phase": "closing",
            "round_number": final_round,
            "instructions": "Vote after Team A's closing statement"
        })
        
        await self.execute_agent_turn("debator_b", {
            "phase": "closing",
            "round_number": final_round,
            "instructions": "Generate closing statement (no new citations allowed)"
        })
        
        # Crowd votes after debator_b's closing
        await self.execute_agent_turn("crowd", {
            "phase": "closing",
            "round_number": final_round,
            "instructions": "Vote after Team B's closing statement"
        })
        
        # Final evaluation
        await self.execute_agent_turn("judge", {
            "phase": "closing",
            "round_number": final_round,
            "instructions": "Provide final analysis and comprehensive report"
        })
        
        # Final crowd vote after judge's analysis
        await self.execute_agent_turn("crowd", {
            "phase": "closing",
            "round_number": final_round,
            "instructions": "Cast final vote on overall debate"
        })
        
        # Mark as completed
        self.state.transition_to(DebatePhase.COMPLETED)
        self.logger.log_moderator_action(
            action="phase_transition",
            details={"from": "closing", "to": "completed"},
            state_snapshot=self.state.to_dict()
        )
        self._save_checkpoint()
        
        print(f"\n✅ Phase 3 complete\n")
    
    # ========================================================================
    # AGENT COORDINATION
    # ========================================================================
    
    async def execute_agent_turn(
        self,
        agent_name: str,
        context_params: Dict[str, Any]
    ) -> AgentResponse:
        """
        Execute a single agent turn with checkpoint saving.
        
        Steps:
        1. Get agent instance
        2. Build AgentContext with permission-filtered state
        3. Execute agent.execute_turn(context)
        4. Validate response
        5. Apply file updates
        6. Update state
        7. Log completion
        8. Save checkpoint if needed
        
        Args:
            agent_name: Name of agent to execute
            context_params: Parameters for building AgentContext
            
        Returns:
            AgentResponse from the agent
            
        Raises:
            Exception: If agent fails or returns errors
        """
        agent = self.agents[agent_name]
        
        # Inject scoreboard into debator instructions
        instructions = context_params.get("instructions", "")
        if "debator" in agent_name:
            scoreboard = self._get_scoreboard_text()
            if scoreboard:
                instructions = f"{instructions}\n\n{scoreboard}"
        
        # Build context with permission-filtered state
        context = AgentContext(
            debate_id=self.debate_id,
            topic=self.topic,
            phase=context_params.get("phase", self.state.phase.value),
            round_number=context_params.get("round_number", self.state.round_number),
            current_state=agent.read_state(),  # Permission-filtered!
            instructions=instructions
        )
        
        # Execute turn
        print(f"🎯 Executing: {agent_name} (Round {context.round_number})")
        start_time = datetime.utcnow()
        
        try:
            response = await agent.execute_turn(context)
        except Exception as e:
            print(f"❌ {agent_name} threw exception: {e}")
            self.logger.log_error(
                error_type="agent_exception",
                message=str(e),
                context={"agent": agent_name, "phase": context.phase, "round": context.round_number}
            )
            raise
        
        if not response.success:
            error_msg = ", ".join(response.errors)
            print(f"❌ {agent_name} failed: {error_msg}")
            self.logger.log_error(
                error_type="agent_failure",
                message=error_msg,
                context={"agent": agent_name, "phase": context.phase, "round": context.round_number}
            )
            raise Exception(f"Agent {agent_name} failed: {error_msg}")
        
        # Log agent turn
        self.logger.log_agent_turn(
            agent_name=agent_name,
            agent_role=agent.role,
            phase=context.phase,
            round_number=context.round_number,
            context={
                "topic": context.topic,
                "instructions": context.instructions,
                "current_state": context.current_state
            },
            response={
                "success": response.success,
                "output": response.output,
                "file_updates": [u.__dict__ if hasattr(u, '__dict__') else str(u) for u in response.file_updates],
                "metadata": response.metadata
            },
            errors=response.errors if not response.success else None
        )
        
        # Apply file updates
        for update in response.file_updates:
            self._apply_file_update(update)
        
        # Record completion
        duration = (datetime.utcnow() - start_time).total_seconds()
        cost_estimate = response.output.get("_cost_estimate", 0.0)
        
        self.completed_turns.append({
            "turn": self.state.turn_count + 1,
            "agent": agent_name,
            "phase": context.phase,
            "round": context.round_number,
            "cost": cost_estimate,
            "duration_sec": duration,
            "timestamp": datetime.utcnow().isoformat() + "Z"
        })
        
        self.total_cost += cost_estimate
        
        # Update state
        self.state.next_turn(agent_name)
        
        print(f"✅ {agent_name} completed (${cost_estimate:.3f}, {duration:.1f}s)")
        
        # Save checkpoint if expensive turn or phase boundary
        if self._should_checkpoint(agent_name, context_params):
            self._save_checkpoint()
            print(f"💾 Checkpoint saved (Total: ${self.total_cost:.2f})")
        
        return response
    
    def _apply_file_update(self, update: FileUpdate) -> None:
        """
        Apply file update from agent.
        
        Maps FileUpdateOperation to FileManager methods.
        
        Args:
            update: FileUpdate object from agent
        """
        # Log file update
        self.logger.log_file_update(
            file_type=update.file_type,
            operation=update.operation.name,
            data=update.data
        )
        
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
            vote_round = update.data
            
            # Initialize vote_rounds if it doesn't exist
            if "vote_rounds" not in data:
                data["vote_rounds"] = []
            
            # Initialize voters list if it doesn't exist
            if "voters" not in data:
                data["voters"] = []
            
            # Update voter records
            for vote in vote_round["votes"]:
                voter_id = vote["voter_id"]
                
                # Find or create voter
                voter = next(
                    (v for v in data["voters"] if v["voter_id"] == voter_id),
                    None
                )
                
                if voter:
                    voter["voting_history"].append({
                        "round": vote_round["round"],
                        "score": vote["score"],
                        "rationale": vote.get("rationale", vote.get("reasoning", ""))
                    })
                    voter["current_score"] = vote["score"]
                    # Append journal entry if present
                    if vote.get("journal_entry"):
                        voter["journal"] = voter.get("journal", "") + "\n\n" + vote["journal_entry"]
                else:
                    new_voter = {
                        "voter_id": voter_id,
                        "persona": vote.get("persona", "Unknown"),
                        "persona_description": vote.get("persona_description", ""),
                        "persona_type": vote.get("persona_type", "unknown"),
                        "voting_history": [{
                            "round": vote_round["round"],
                            "score": vote["score"],
                            "rationale": vote.get("rationale", vote.get("reasoning", ""))
                        }],
                        "current_score": vote["score"],
                        "journal": vote.get("journal_entry", "")
                    }
                    data["voters"].append(new_voter)
            
            # Add round summary
            data["vote_rounds"].append({
                "round": vote_round["round"],
                "average_score": vote_round["average_score"],
                "vote_count": vote_round["vote_count"],
                "timestamp": vote_round["timestamp"]
            })
            
            self.file_manager.write_by_moderator("crowd_opinion", data)
    
    def _initialize_agents(
        self,
        team_a_stance: str,
        team_b_stance: str
    ) -> Dict[str, Agent]:
        """
        Create all agent instances.
        
        Args:
            team_a_stance: Stance for team a ("for" or "against")
            team_b_stance: Stance for team b ("for" or "against")
            
        Returns:
            Dictionary of {agent_name: agent_instance}
        """
        agents = {
            "debator_a": DebatorAgent(
                name="debator_a",
                team="a",
                stance=team_a_stance,
                file_manager=self.file_manager,
                config=self.config,
                raw_data_logger=self.raw_data_logger
            ),
            "debator_b": DebatorAgent(
                name="debator_b",
                team="b",
                stance=team_b_stance,
                file_manager=self.file_manager,
                config=self.config,
                raw_data_logger=self.raw_data_logger
            ),
            "factchecker_a": FactCheckerAgent(
                name="factchecker_a",
                team="a",
                file_manager=self.file_manager,
                config=self.config,
                raw_data_logger=self.raw_data_logger
            ),
            "factchecker_b": FactCheckerAgent(
                name="factchecker_b",
                team="b",
                file_manager=self.file_manager,
                config=self.config,
                raw_data_logger=self.raw_data_logger
            ),
            "judge": JudgeAgent(
                name="judge",
                file_manager=self.file_manager,
                config=self.config,
                raw_data_logger=self.raw_data_logger
            ),
            "crowd": CrowdAgent(
                name="crowd",
                file_manager=self.file_manager,
                config=self.config,
                raw_data_logger=self.raw_data_logger,
                personas=getattr(self, '_generated_personas', None)
            )
        }
        
        return agents
    
    # ========================================================================
    # CHECKPOINT MANAGEMENT
    # ========================================================================
    
    def _save_checkpoint(self) -> None:
        """
        Save current state to checkpoint file.
        
        Called after:
        - Vote 0 completes (before expensive Deep Research)
        - Each debator turn (Deep Research = $0.08)
        - Each phase transition
        - Each round completes (after judge/crowd)
        """
        checkpoint = {
            "debate_id": self.debate_id,
            "topic": self.topic,
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
        
        # Log checkpoint save
        self.logger.log_moderator_action(
            action="checkpoint_saved",
            details={
                "phase": self.state.phase.value,
                "round": self.state.round_number,
                "turn_count": self.state.turn_count,
                "total_cost": self.total_cost
            }
        )
    
    def _get_scoreboard_text(self) -> str:
        """Build a scoreboard string from the latest crowd opinion data."""
        try:
            crowd_data = self.file_manager._read_json("crowd_opinion")
            vote_rounds = crowd_data.get("vote_rounds", [])
            if not vote_rounds:
                return ""

            latest = vote_rounds[-1]
            avg = latest.get("average_score", 50)
            count = latest.get("vote_count", 0)
            favor_a = sum(1 for v in crowd_data.get("voters", []) if v.get("current_score", 50) > 50)
            favor_b = count - favor_a

            lines = [
                "📊 CROWD SCOREBOARD:",
                f"  Latest avg: {avg:.1f}/100 ({'leans Team A' if avg > 50 else 'leans Team B'})",
                f"  Favor Team A: {favor_a} | Favor Team B: {favor_b}",
            ]

            if len(vote_rounds) >= 2:
                prev_avg = vote_rounds[-2].get("average_score", avg)
                shift = avg - prev_avg
                lines.append(f"  Shift: {shift:+.1f} from previous vote")

            return "\n".join(lines)
        except Exception:
            return ""

    def _should_checkpoint(self, agent_name: str, context_params: Dict[str, Any]) -> bool:
        """
        Determine if we should save a checkpoint.
        
        Checkpoint triggers:
        - Vote 0 completes (before expensive Deep Research)
        - Debator turns (Deep Research = $0.08 each)
        - Round completes (after crowd votes)
        - Phase transitions
        
        Args:
            agent_name: Agent that just completed
            context_params: Context parameters used
            
        Returns:
            True if checkpoint should be saved
        """
        # Vote 0 just completed
        if context_params.get("round_number") == 0 and agent_name == "crowd":
            return True
        
        # Debator turn (expensive Deep Research)
        if "debator" in agent_name:
            return True
        
        # Round completes (after crowd votes)
        if agent_name == "crowd":
            return True
        
        # Phase transition (judge typically marks phase end)
        if agent_name == "judge":
            return True
        
        return False
    
    def _calculate_cost_by_agent(self) -> Dict[str, float]:
        """
        Calculate total cost per agent.
        
        Returns:
            Dictionary of {agent_name: total_cost}
        """
        cost_by_agent: Dict[str, float] = {}
        
        for turn in self.completed_turns:
            agent = turn["agent"]
            cost = turn.get("cost", 0.0)
            cost_by_agent[agent] = cost_by_agent.get(agent, 0.0) + cost
        
        return cost_by_agent
    
    # ========================================================================
    # OUTPUT GENERATION
    # ========================================================================
    
    async def _generate_outputs(self) -> None:
        """
        Generate all final artifacts.
        
        Outputs:
        1. transcript_full.md - Human-readable debate transcript
        2. citation_ledger.json - All citations with scores
        3. debate_logic_map.json - Frontier evolution
        4. voter_sentiment_graph.csv - Opinion shifts over time
        
        For MVP: Simple formats, can refine later
        """
        print(f"📊 Generating outputs...")
        
        output_dir = self.debate_dir / "outputs"
        output_dir.mkdir(exist_ok=True)
        
        # Read all files
        history = self.file_manager.read_for_agent("moderator", "history_chat")
        citations = self.file_manager.read_for_agent("moderator", "citation_pool")
        latent = self.file_manager.read_for_agent("moderator", "debate_latent")
        crowd = self.file_manager.read_for_agent("moderator", "crowd_opinion")
        
        # 1. Transcript (Markdown)
        await self._generate_transcript(output_dir, history)
        
        # 2. Citation Ledger (JSON)
        await self._generate_citation_ledger(output_dir, citations)
        
        # 3. Logic Map (JSON)
        await self._generate_logic_map(output_dir, latent)
        
        # 4. Sentiment Graph (CSV)
        await self._generate_sentiment_graph(output_dir, crowd)
        
        print(f"✅ Outputs generated in: {output_dir}")
    
    async def _generate_transcript(self, output_dir: Path, history: Dict[str, Any]) -> None:
        """Generate human-readable transcript in Markdown."""
        lines = [
            f"# Debate Transcript",
            f"",
            f"**Topic**: {self.topic}",
            f"**Debate ID**: {self.debate_id}",
            f"**Date**: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
            f"",
            f"---",
            f""
        ]
        
        # Public transcript contains main statements
        for turn in history.get("public_transcript", []):
            speaker = turn.get("speaker", "unknown")
            round_num = turn.get("round", 0)
            phase = turn.get("phase", "unknown")
            statement = turn.get("statement", turn.get("main_statement", ""))
            
            lines.append(f"## Round {round_num} - {speaker} ({phase})")
            lines.append(f"")
            lines.append(statement)
            lines.append(f"")
            lines.append(f"---")
            lines.append(f"")
        
        # Add team notes as supplementary sections if needed
        team_notes = history.get("team_notes", {})
        if team_notes.get("a") or team_notes.get("b"):
            lines.append(f"## Supplementary Materials")
            lines.append(f"")
            
            for team in ["a", "b"]:
                if team_notes.get(team):
                    lines.append(f"### Team {team.upper()}")
                    for note in team_notes[team]:
                        supp = note.get("supplementary_material", "")
                        if supp:
                            lines.append(f"<details>")
                            lines.append(f"<summary>Round {note.get('round', 0)}</summary>")
                            lines.append(f"")
                            lines.append(supp)
                            lines.append(f"</details>")
                            lines.append(f"")
        
        transcript_path = output_dir / "transcript_full.md"
        with open(transcript_path, 'w', encoding='utf-8') as f:
            f.write("\n".join(lines))
    
    async def _generate_citation_ledger(self, output_dir: Path, citations: Dict[str, Any]) -> None:
        """Generate citation ledger with verification scores."""
        ledger_path = output_dir / "citation_ledger.json"
        with open(ledger_path, 'w') as f:
            json.dump(citations, f, indent=2)
    
    async def _generate_logic_map(self, output_dir: Path, latent: Dict[str, Any]) -> None:
        """Generate debate logic map showing frontier evolution."""
        logic_path = output_dir / "debate_logic_map.json"
        with open(logic_path, 'w') as f:
            json.dump(latent, f, indent=2)
    
    async def _generate_sentiment_graph(self, output_dir: Path, crowd: Dict[str, Any]) -> None:
        """Generate CSV of voter sentiment over time."""
        lines = ["round,voter_id,score,persona_type"]
        
        for voter in crowd["voters"]:
            for vote_record in voter["voting_history"]:
                lines.append(
                    f"{vote_record['round']},"
                    f"{voter['voter_id']},"
                    f"{vote_record['score']},"
                    f"{voter['persona_type']}"
                )
        
        csv_path = output_dir / "voter_sentiment_graph.csv"
        with open(csv_path, 'w') as f:
            f.write("\n".join(lines))
