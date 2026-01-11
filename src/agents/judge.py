"""
Judge Agent - Neutral analysis and disagreement frontier mapping.

Uses: Claude 3.5 Sonnet
Responsibilities:
- Analyze debate transcript neutrally
- Identify consensus points (where both sides agree)
- Map disagreement frontier (core contested issues)
- Update debate_latent.json with frontier
- Does NOT decide "who won" - identifies "what's left to argue"
"""

import json
from typing import Dict, Any, List, Tuple
from datetime import datetime

from src.agents.base import Agent, AgentContext, AgentResponse, FileUpdate, FileUpdateOperation
from src.clients.claude_client import ClaudeClient
from src.utils.schemas import get_schema


class JudgeAgent(Agent):
    """Agent that analyzes debate and maps disagreement frontier."""
    
    def __init__(
        self,
        name: str,
        file_manager,
        config,
        raw_data_logger=None
    ):
        """
        Initialize judge agent.
        
        Args:
            name: Agent name ("judge")
            file_manager: FileManager instance
            config: Configuration object
            raw_data_logger: Optional RawDataLogger for logging all model calls
        """
        super().__init__(name, "judge", file_manager)
        self.config = config
        
        # Initialize client based on configuration
        if config.openrouter_api_key:
            # Use OpenRouter
            from src.clients.openrouter_client import OpenRouterClient, create_claude_adapter
            openrouter_client = OpenRouterClient(api_key=config.openrouter_api_key, raw_data_logger=raw_data_logger)
            self.claude = create_claude_adapter(openrouter_client, config.claude_model, agent_name="judge")
        elif config.claude_api_key:
            # Use direct Claude API
            self.claude = ClaudeClient(
                api_key=config.claude_api_key,
                model=config.claude_model
            )
        else:
            raise ValueError(
                "Judge requires either OPENROUTER_API_KEY or CLAUDE_API_KEY"
            )
    
    async def execute_turn(self, context: AgentContext) -> AgentResponse:
        """
        Execute judge's turn - analyze debate and map frontier.
        
        Args:
            context: Current debate context
        
        Returns:
            AgentResponse with analysis and file updates
        """
        try:
            # Analyze the debate
            analysis = await self._analyze_debate(context)
            
            # Create file update for debate_latent.json
            file_update = self._create_latent_update(
                analysis=analysis,
                round_number=context.round_number
            )
            
            return self.create_response(
                success=True,
                output=analysis,
                file_updates=[file_update],
                metadata={
                    "consensus_count": len(analysis.get("consensus", [])),
                    "frontier_count": len(analysis.get("disagreement_frontier", []))
                }
            )
        
        except Exception as e:
            return self.create_response(
                success=False,
                output={},
                errors=[f"Judge turn failed: {str(e)}"]
            )
    
    async def _analyze_debate(self, context: AgentContext) -> Dict[str, Any]:
        """
        Analyze debate transcript to identify consensus and disagreement.
        
        Uses Claude 3.5 Sonnet with structured output for reliable parsing.
        
        Args:
            context: Debate context
        
        Returns:
            Analysis dictionary with consensus and disagreement_frontier
        """
        system_prompt = self._get_system_prompt()
        user_prompt = self._build_analysis_prompt(context)
        
        # Get structured output from Claude
        schema = get_schema("judge", "analysis")
        
        response = await self.claude.generate(
            prompt=user_prompt,
            system=system_prompt,
            temperature=self.config.claude_temperature,
            max_tokens=self.config.max_tokens_judge
        )
        
        # Parse JSON response
        try:
            from src.utils.json_parser import parse_json_response
            analysis = parse_json_response(response)
            
            # Validate structure
            if "consensus" not in analysis:
                analysis["consensus"] = []
            if "disagreement_frontier" not in analysis:
                analysis["disagreement_frontier"] = []
            
            return analysis
        
        except json.JSONDecodeError:
            # Fallback parsing
            return self._parse_analysis_fallback(response)
    
    def _get_system_prompt(self) -> str:
        """
        Get system prompt for judge analysis.
        
        Judge must be neutral and focus on mapping the argument space,
        not declaring a winner.
        """
        prompt = """You are a neutral debate judge and argument cartographer.

Your role is NOT to decide who is winning, but to map the logical structure of the debate.

Your responsibilities:
1. IDENTIFY CONSENSUS: Find points where both sides implicitly or explicitly agree
   - Common ground on facts
   - Shared concerns
   - Agreed-upon goals (even if they disagree on methods)

2. MAP DISAGREEMENT FRONTIER: Identify the core issues still being contested
   - Focus on substantive disagreements, not rhetorical differences
   - Capture BOTH sides' stances on each issue
   - Prioritize issues with the most evidence/argumentation
   - Aim for medium level of detail (not too broad, not too granular)

3. MAINTAIN NEUTRALITY: Do not favor either side
   - Accurately represent both positions
   - Focus on "what's left to argue" not "who's right"

Output format: Structured JSON with consensus[] and disagreement_frontier[]

Quality over quantity: Better to identify 2-3 real core issues than list 10 minor points."""
        
        return prompt
    
    def _build_analysis_prompt(self, context: AgentContext) -> str:
        """
        Build analysis prompt with debate transcript.
        
        Args:
            context: Debate context
        
        Returns:
            Prompt for Claude
        """
        prompt = f"""Analyze this debate:

TOPIC: {context.topic}

"""
        
        # Add debate transcript (public only, no team notes)
        public_transcript = context.current_state.get("history_chat", {}).get("public_transcript", [])
        
        if not public_transcript:
            prompt += "No statements yet. This is the initial analysis.\n"
        else:
            prompt += "DEBATE TRANSCRIPT:\n\n"
            for turn in public_transcript:
                speaker = turn.get("speaker", "unknown")
                statement = turn.get("statement", "")
                round_label = turn.get("round_label", "")
                
                prompt += f"[{round_label}] Team {speaker}:\n{statement}\n\n"
        
        # Add previous frontier if available (for context)
        latent = context.current_state.get("debate_latent", {})
        if latent.get("round_history"):
            latest = latent["round_history"][-1]
            if latest.get("disagreement_frontier"):
                prompt += "\n--- PREVIOUS DISAGREEMENT FRONTIER ---\n"
                for issue in latest["disagreement_frontier"]:
                    prompt += f"- {issue.get('core_issue', '')}\n"
                prompt += "\nUpdate this frontier based on new statements.\n"
        
        prompt += f"""

YOUR TASK:
Analyze the debate and return a JSON object with:

1. "consensus": Array of strings (points both sides agree on)
2. "disagreement_frontier": Array of objects with:
   - "core_issue": The contested topic
   - "a_stance": Team a's position on this issue
   - "b_stance": Team b's position on this issue

Focus on substantive disagreements. Aim for 2-4 frontier issues (medium detail).

Return JSON now:"""
        
        return prompt
    
    def _create_latent_update(
        self,
        analysis: Dict[str, Any],
        round_number: int
    ) -> FileUpdate:
        """
        Create file update for debate_latent.json.
        
        Args:
            analysis: Judge's analysis
            round_number: Current round number
        
        Returns:
            FileUpdate object
        """
        round_entry = {
            "round_number": round_number,
            "consensus": analysis.get("consensus", []),
            "disagreement_frontier": analysis.get("disagreement_frontier", []),
            "analyzed_at": datetime.now().isoformat()
        }
        
        return FileUpdate(
            file_type="debate_latent",
            operation=FileUpdateOperation.UPDATE_DEBATE_LATENT,
            data=round_entry
        )
    
    def _parse_analysis_fallback(self, response: str) -> Dict[str, Any]:
        """
        Fallback parser if JSON parsing fails.
        
        Attempts to extract consensus and frontier from text.
        
        Args:
            response: Text response from Claude
        
        Returns:
            Analysis dictionary
        """
        import re
        
        analysis = {
            "consensus": [],
            "disagreement_frontier": []
        }
        
        # Try to extract consensus points
        consensus_section = re.search(
            r'consensus[:\s]+(.*?)(?:disagreement|frontier|$)',
            response,
            re.IGNORECASE | re.DOTALL
        )
        if consensus_section:
            # Extract bullet points or numbered items
            points = re.findall(r'[-*•]\s*(.+)', consensus_section.group(1))
            analysis["consensus"] = [p.strip() for p in points if p.strip()]
        
        # Try to extract disagreement frontier
        frontier_section = re.search(
            r'(?:disagreement|frontier)[:\s]+(.*?)$',
            response,
            re.IGNORECASE | re.DOTALL
        )
        if frontier_section:
            # Look for issue patterns
            issues = re.findall(
                r'(?:issue|topic|point)[:\s]*(.+?)(?:\n|$)',
                frontier_section.group(1),
                re.IGNORECASE
            )
            for issue in issues[:3]:  # Max 3 issues
                analysis["disagreement_frontier"].append({
                    "core_issue": issue.strip(),
                    "a_stance": "See transcript",
                    "b_stance": "See transcript"
                })
        
        return analysis
