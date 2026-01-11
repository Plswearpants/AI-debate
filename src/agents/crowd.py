"""
Crowd Agent - Manages 100 diverse persona voting swarm.

Uses: Lambda GPU (Llama 3.1 8B) for batch inference
Responsibilities:
- Maintain 100 diverse personas (political, professional, demographic)
- Vote 0: Vote on stance preference (determines team assignments)
- Vote 1+: Vote on debate performance (0-100 scale, team-based)
- Track opinion shifts over rounds
- Update crowd_opinion.json
"""

import json
from typing import Dict, Any, List
from datetime import datetime

from src.agents.base import Agent, AgentContext, AgentResponse, FileUpdate, FileUpdateOperation
from src.clients.lambda_client import LambdaGPUClient
from src.utils.schemas import get_schema


class CrowdAgent(Agent):
    """Agent that manages crowd voting with diverse personas."""
    
    def __init__(
        self,
        name: str,
        file_manager,
        config
    ):
        """
        Initialize crowd agent.
        
        Args:
            name: Agent name ("crowd")
            file_manager: FileManager instance
            config: Configuration object
        """
        super().__init__(name, "crowd", file_manager)
        self.config = config
        
        # Initialize Lambda GPU client
        self.lambda_client = LambdaGPUClient(
            endpoint=config.lambda_gpu_endpoint,
            api_key=config.lambda_gpu_api_key
        )
        
        # Load personas
        self.personas = self._load_personas(config.crowd_size)
    
    async def execute_turn(self, context: AgentContext) -> AgentResponse:
        """
        Execute crowd voting.
        
        All personas vote on current debate state in batch.
        
        Args:
            context: Current debate context
        
        Returns:
            AgentResponse with vote results and file updates
        """
        try:
            # Get votes from all personas
            votes = await self._batch_vote(context)
            
            # Create file update
            file_update = self._create_crowd_update(
                votes=votes,
                round_number=context.round_number
            )
            
            # Calculate aggregate statistics
            avg_score = sum(v["score"] for v in votes) / len(votes) if votes else 0
            
            return self.create_response(
                success=True,
                output={
                    "votes": votes,
                    "average_score": round(avg_score, 1),
                    "voter_count": len(votes)
                },
                file_updates=[file_update],
                metadata={
                    "average_score": round(avg_score, 1),
                    "voter_count": len(votes)
                }
            )
        
        except Exception as e:
            return self.create_response(
                success=False,
                output={},
                errors=[f"Crowd voting failed: {str(e)}"]
            )
    
    async def _batch_vote(self, context: AgentContext) -> List[Dict[str, Any]]:
        """
        Batch vote from all personas.
        
        Uses Lambda GPU for efficient parallel inference.
        
        Args:
            context: Debate context
        
        Returns:
            List of vote dictionaries
        """
        # Build prompts for all personas
        prompts = []
        for persona in self.personas:
            prompt = self._build_voting_prompt(persona, context)
            prompts.append(prompt)
        
        # Batch inference on Lambda GPU
        responses = await self.lambda_client.generate_batch(
            prompts=prompts,
            temperature=self.config.crowd_temperature,
            max_tokens=self.config.max_tokens_crowd
        )
        
        # Parse responses into votes
        votes = []
        for persona, response in zip(self.personas, responses):
            try:
                vote = self._parse_vote(response, persona)
                votes.append(vote)
            except Exception as e:
                # Skip invalid votes
                print(f"⚠️  Failed to parse vote from {persona['id']}: {e}")
                continue
        
        return votes
    
    def _build_voting_prompt(self, persona: Dict[str, Any], context: AgentContext) -> str:
        """
        Build voting prompt for a specific persona.
        
        Vote 0 (round 0): Vote on stance preference to determine team assignments
        Vote 1+: Vote on debate performance to rate which team is winning
        
        Args:
            persona: Persona dictionary
            context: Debate context
        
        Returns:
            Prompt string for this persona
        """
        # Check if this is Vote 0 (initial stance preference)
        if context.round_number == 0:
            return self._build_vote_zero_prompt(persona, context)
        
        # Get latest statements from both sides (Vote 1+)
        public_transcript = context.current_state.get("history_chat", {}).get("public_transcript", [])
        
        # Get most recent statement from each side
        last_a = ""
        last_b = ""
        for turn in reversed(public_transcript):
            if turn.get("speaker") == "a" and not last_a:
                last_a = turn.get("statement", "")
            elif turn.get("speaker") == "b" and not last_b:
                last_b = turn.get("statement", "")
            if last_a and last_b:
                break
        
        prompt = f"""You are: {persona['description']}

Topic: {context.topic}

Team a's argument:
{last_a[:400] if last_a else 'No statement yet'}

Team b's argument:
{last_b[:400] if last_b else 'No statement yet'}

Based on your perspective as a {persona['name']}, rate how convinced you are by the overall debate so far.

Score: 0-100
- 0-20: Strongly favor Team b
- 20-40: Moderately favor Team b
- 40-60: Neutral/undecided
- 60-80: Moderately favor Team a
- 80-100: Strongly favor Team a

Return JSON: {{"score": <0-100>, "reasoning": "<brief explanation>"}}"""
        
        return prompt
    
    def _build_vote_zero_prompt(self, persona: Dict[str, Any], context: AgentContext) -> str:
        """
        Build Vote 0 prompt - voting on stance preference (not debate performance).
        
        This determines which stance becomes Team a (winner) and Team b (second).
        
        Args:
            persona: Persona dictionary
            context: Debate context (topic only, no statements yet)
        
        Returns:
            Vote 0 prompt
        """
        # Extract stance descriptions from context metadata
        # For now, assume topic is phrased as "Should we [do X]?"
        # "for" = implement/yes, "against" = oppose/no
        
        prompt = f"""You are: {persona['description']}

Topic: {context.topic}

This is the initial vote BEFORE any debate arguments. Based on your values and perspective as a {persona['name']}, what is your initial stance on this topic?

Vote on your stance preference:

Score: 0-100
- 0-20: Strongly AGAINST (oppose the proposal)
- 20-40: Moderately against
- 40-60: Neutral/undecided
- 60-80: Moderately FOR (support the proposal)
- 80-100: Strongly FOR

This vote determines the baseline audience opinion before the debate begins.
The side with more support will speak first as Team a.

Return JSON: {{"score": <0-100>, "reasoning": "<brief explanation of your initial stance>"}}"""
        
        return prompt
    
    def _parse_vote(self, response: str, persona: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse vote from persona response.
        
        Args:
            response: LLM response (should be JSON)
            persona: Persona dictionary
        
        Returns:
            Vote dictionary
        """
        try:
            # Try to parse as JSON
            vote_data = json.loads(response)
            score = vote_data.get("score", 50)
            reasoning = vote_data.get("reasoning", "")
        except json.JSONDecodeError:
            # Fallback: extract score from text
            import re
            score_match = re.search(r'score[:\s]+(\d+)', response, re.IGNORECASE)
            score = int(score_match.group(1)) if score_match else 50
            reasoning = response[:100]
        
        # Clamp score to valid range
        score = max(0, min(100, score))
        
        return {
            "voter_id": persona["id"],
            "persona": persona["name"],
            "score": score,
            "reasoning": reasoning[:200]  # Keep brief
        }
    
    def _create_crowd_update(
        self,
        votes: List[Dict[str, Any]],
        round_number: int
    ) -> FileUpdate:
        """
        Create file update for crowd_opinion.json.
        
        Args:
            votes: List of vote dictionaries
            round_number: Current round number
        
        Returns:
            FileUpdate object
        """
        return FileUpdate(
            file_type="crowd_opinion",
            operation=FileUpdateOperation.ADD_CROWD_VOTE,
            data={
                "round_number": round_number,
                "votes": votes,
                "timestamp": datetime.now().isoformat()
            }
        )
    
    def _load_personas(self, count: int) -> List[Dict[str, Any]]:
        """
        Load crowd personas.
        
        For MVP, generates diverse personas programmatically.
        In production, could load from src/prompts/crowd_personas.json
        
        Args:
            count: Number of personas to generate
        
        Returns:
            List of persona dictionaries
        """
        # Persona templates covering ideological and demographic diversity
        persona_templates = [
            # Political spectrum
            {"type": "political", "name": "Progressive Activist", "description": "Strong advocate for social justice and government intervention"},
            {"type": "political", "name": "Fiscal Conservative", "description": "Prioritizes low taxes, limited government, free markets"},
            {"type": "political", "name": "Libertarian", "description": "Values individual freedom and minimal government"},
            {"type": "political", "name": "Social Democrat", "description": "Supports mixed economy and social safety net"},
            {"type": "political", "name": "Moderate Independent", "description": "Pragmatic centrist, case-by-case evaluation"},
            
            # Professional backgrounds
            {"type": "professional", "name": "Economist", "description": "PhD economist focused on data and empirical evidence"},
            {"type": "professional", "name": "Small Business Owner", "description": "Practical perspective on business and employment"},
            {"type": "professional", "name": "Social Worker", "description": "Front-line experience with poverty and social programs"},
            {"type": "professional", "name": "Tech Entrepreneur", "description": "Innovation-focused, disruption-oriented thinking"},
            {"type": "professional", "name": "Public School Teacher", "description": "Education and community welfare perspective"},
            
            # Demographic/experiential
            {"type": "demographic", "name": "Working Class Parent", "description": "Struggles with bills, childcare, job security"},
            {"type": "demographic", "name": "Retired Senior", "description": "Fixed income, healthcare concerns, traditional values"},
            {"type": "demographic", "name": "College Student", "description": "Young, idealistic, concerned about future opportunities"},
            {"type": "demographic", "name": "Rural Resident", "description": "Small town perspective, self-reliance values"},
            {"type": "demographic", "name": "Urban Professional", "description": "City dweller, cosmopolitan, career-focused"},
            
            # Stakeholder groups
            {"type": "stakeholder", "name": "Healthcare Worker", "description": "Insider view of healthcare system challenges"},
            {"type": "stakeholder", "name": "Environmental Advocate", "description": "Climate and sustainability priority"},
            {"type": "stakeholder", "name": "Union Representative", "description": "Worker rights and collective bargaining focus"},
            {"type": "stakeholder", "name": "Corporate Executive", "description": "Business efficiency and shareholder value perspective"},
            {"type": "stakeholder", "name": "Nonprofit Director", "description": "Mission-driven, community impact focused"}
        ]
        
        # Generate personas by cycling through templates
        personas = []
        for i in range(count):
            template = persona_templates[i % len(persona_templates)]
            persona = {
                "id": f"v_{i+1:03d}",
                "name": f"{template['name']} #{i//len(persona_templates) + 1}",
                "description": template["description"],
                "type": template["type"]
            }
            personas.append(persona)
        
        return personas
    
    def get_personas_summary(self) -> Dict[str, Any]:
        """
        Get summary of persona distribution.
        
        Returns:
            Summary dictionary with counts by type
        """
        by_type = {}
        for persona in self.personas:
            ptype = persona.get("type", "unknown")
            by_type[ptype] = by_type.get(ptype, 0) + 1
        
        return {
            "total_personas": len(self.personas),
            "by_type": by_type,
            "sample_personas": self.personas[:5]  # First 5 as examples
        }
