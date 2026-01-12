"""
Judge Agent - Neutral analysis and disagreement frontier mapping.

Uses: Claude (config.claude_model; often Claude 3.5 Sonnet)
Responsibilities:
- Analyze debate transcript neutrally
- Identify consensus points (where both sides agree)
- Map disagreement frontier (core contested issues)
- Update debate_latent.json with frontier
- Does NOT decide "who won" - identifies "what's left to argue"
"""

import json
from typing import Dict, Any
from datetime import datetime

from src.agents.base import Agent, AgentContext, AgentResponse, FileUpdate, FileUpdateOperation
from src.clients.claude_client import ClaudeClient


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
            openrouter_client = OpenRouterClient(
                api_key=config.openrouter_api_key,
                raw_data_logger=raw_data_logger
            )
            self.claude = create_claude_adapter(
                openrouter_client,
                config.claude_model,
                agent_name="judge"
            )
        elif config.claude_api_key:
            # Use direct Claude API
            self.claude = ClaudeClient(
                api_key=config.claude_api_key,
                model=config.claude_model
            )
        else:
            raise ValueError("Judge requires either OPENROUTER_API_KEY or CLAUDE_API_KEY")

    async def execute_turn(self, context: AgentContext) -> AgentResponse:
        """
        Execute judge's turn - analyze debate and map frontier.

        Args:
            context: Current debate context

        Returns:
            AgentResponse with analysis and file updates
        """
        try:
            analysis = await self._analyze_debate(context)

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

        Args:
            context: Debate context

        Returns:
            Analysis dictionary with consensus and disagreement_frontier
        """
        system_prompt = self._get_system_prompt()
        user_prompt = self._build_analysis_prompt(context)

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
            if "consensus" not in analysis or not isinstance(analysis.get("consensus"), list):
                analysis["consensus"] = []
            if "disagreement_frontier" not in analysis or not isinstance(analysis.get("disagreement_frontier"), list):
                analysis["disagreement_frontier"] = []

            # Validate each frontier issue has required keys
            cleaned_frontier = []
            for item in analysis["disagreement_frontier"]:
                if not isinstance(item, dict):
                    continue
                cleaned_frontier.append({
                    "core_issue": str(item.get("core_issue", "")).strip(),
                    "a_stance": str(item.get("a_stance", "")).strip(),
                    "b_stance": str(item.get("b_stance", "")).strip(),
                })
            analysis["disagreement_frontier"] = cleaned_frontier

            # Ensure consensus strings
            analysis["consensus"] = [str(x).strip() for x in analysis["consensus"] if str(x).strip()]

            return analysis

        except json.JSONDecodeError:
            return self._parse_analysis_fallback(response)

    def _get_system_prompt(self) -> str:
        """
        Get system prompt for judge analysis.

        Judge must be neutral and focus on mapping the argument space,
        not declaring a winner.
        """
        return """You are a neutral debate judge and argument cartographer.

Your role is NOT to decide who is winning. Your role is to map the logical structure of the debate so a reader can see:
(1) what both sides agree on (consensus),
(2) what is still contested (disagreement frontier),
(3) what each side’s stance is on each contested issue.

STRICT GROUNDING RULES
- Use ONLY what appears in the provided debate transcript. Do NOT introduce external facts, examples, or reasoning.
- Do NOT “repair” arguments. If something is missing, unclear, or not addressed by a side, say so.
- Do NOT infer hidden motivations. Only summarize positions stated or clearly implied.

ANTI-CONFLATION RULE (VERY IMPORTANT)
- Keep issues separate unless the transcript explicitly links them.
- Common UBI debate issues that must NOT be merged unless explicitly connected:
  (a) poverty/material hardship effects,
  (b) inflation/price effects,
  (c) labor supply/work incentives,
  (d) fiscal feasibility/financing,
  (e) targeting vs universality / welfare design & stigma.
- When writing a stance for an issue, it MUST directly address that issue. Do not substitute a different argument (e.g., inflation as a response to poverty).

CONSENSUS EXTRACTION
- Identify points where BOTH sides explicitly or implicitly agree:
  • shared goals (e.g., reducing poverty, maintaining economic stability),
  • shared constraints (e.g., fiscal limits, need for careful design),
  • shared concerns (e.g., labor participation matters).
- Only include a consensus point if you can point to evidence from BOTH sides’ statements.
- Write each consensus item as ONE short sentence (≤ 25 words).
- Consensus should GROW over time - actively look for NEW agreement points in each round.
- Pay special attention to statements where one side acknowledges the other's valid concerns or constraints.

DISAGREEMENT FRONTIER MAPPING
- Identify 2–4 core contested issues (medium granularity: not “UBI good/bad,” not overly narrow).
- For each issue, provide:
  • core_issue: short title
  • a_stance: Team a’s position as a crisp claim (≤ 35 words)
  • b_stance: Team b’s position as a crisp claim (≤ 35 words)
- If a side does not address an issue in the transcript, write exactly:
  "Not addressed in provided transcript."

TRACKING DEBATE EVOLUTION (for multi-round debates)
- Each analysis should reflect the CURRENT state based on ALL statements in the transcript
- CONSENSUS: Should GROW over time - actively identify NEW consensus points established in the current round
- CONSENSUS: Include all previous consensus PLUS any new agreement points found
- FRONTIER: If new arguments or evidence were introduced, UPDATE stances to reflect them
- FRONTIER: If new substantive disagreements emerged, ADD them as new frontier issues
- FRONTIER: If previous disagreements were resolved, REMOVE them
- Do NOT simply copy previous analysis - actively identify what has CHANGED
- Stances should reflect the most recent and complete arguments from each side

STYLE / QUALITY CONSTRAINTS
- Maintain neutrality and symmetry: both stances should be comparable in abstraction and specificity.
- Prefer concrete claims over rhetorical framing.
- If citations/links look generic or unverifiable, word stances cautiously; do not add extra fields.

OUTPUT FORMAT (JSON ONLY)
Return ONLY a valid JSON object with:
{
  "consensus": [string, ...],
  "disagreement_frontier": [
    { "core_issue": string, "a_stance": string, "b_stance": string },
    ...
  ]
}
Do not output any additional keys or commentary."""

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
            # Identify current round number for highlighting new content
            current_round = context.round_number
            prompt += f"DEBATE TRANSCRIPT (Current Round: {current_round}):\n\n"
            
            for turn in public_transcript:
                speaker = turn.get("speaker", "unknown")
                statement = turn.get("statement", "")
                round_label = turn.get("round_label", "")
                turn_round = turn.get("round_number", 0)
                
                # Highlight statements from current round
                if turn_round == current_round:
                    prompt += f"[{round_label}] Team {speaker} (CURRENT ROUND - NEW CONTENT):\n{statement}\n\n"
                else:
                    prompt += f"[{round_label}] Team {speaker}:\n{statement}\n\n"

        # Add previous analysis if available (for context, but emphasize NEW content)
        latent = context.current_state.get("debate_latent", {})
        if latent.get("round_history"):
            latest = latent["round_history"][-1]
            
            # Show previous consensus to track growth
            if latest.get("consensus"):
                prompt += "\n--- PREVIOUS CONSENSUS (FOR REFERENCE) ---\n"
                for consensus_point in latest["consensus"]:
                    prompt += f"- {consensus_point}\n"
                prompt += "\n"
            
            # Show previous frontier
            if latest.get("disagreement_frontier"):
                prompt += "--- PREVIOUS DISAGREEMENT FRONTIER (FOR REFERENCE) ---\n"
                for issue in latest["disagreement_frontier"]:
                    prompt += f"- {issue.get('core_issue', '')}\n"
                prompt += "\n"
            
            prompt += "IMPORTANT: This is a NEW analysis based on ALL statements in the transcript above.\n\n"
            prompt += "For CONSENSUS:\n"
            prompt += "- Include ALL consensus points (both previous and newly established)\n"
            prompt += "- Explicitly identify NEW consensus points that emerged in the current round\n"
            prompt += "- Consensus should GROW over time as both sides find common ground\n"
            prompt += "- If new statements reveal agreement on something not previously identified, ADD it\n\n"
            prompt += "For DISAGREEMENT FRONTIER:\n"
            prompt += "- Update stances to reflect NEW arguments and evidence presented in the most recent statements\n"
            prompt += "- Add NEW issues if new substantive disagreements emerged\n"
            prompt += "- Remove issues if they were resolved or are no longer contested\n"
            prompt += "- Do NOT simply copy the previous frontier - analyze what has CHANGED\n"

        prompt += """

YOUR TASK:
Analyze the debate and return a JSON object with:

1. "consensus": Array of strings (points both sides agree on)
   - Include ALL consensus points identified so far (cumulative list)
   - Explicitly identify NEW consensus points that emerged in the current round
   - Consensus should GROW over time as both sides find common ground
   - Look for: shared acknowledgments, mutual concerns, agreed-upon constraints, convergent views
   
2. "disagreement_frontier": Array of objects with:
   - "core_issue": The contested topic
   - "a_stance": Team a's position on this issue (reflect their LATEST arguments)
   - "b_stance": Team b's position on this issue (reflect their LATEST arguments)

CRITICAL: This is a FRESH analysis of the ENTIRE transcript above.
- Look for NEW arguments, evidence, or examples introduced in recent statements
- Update stances to include the most recent and complete positions from each side
- Add new issues if new substantive disagreements emerged
- Remove issues if they were resolved or are no longer contested
- Do NOT simply copy previous analysis - show how the debate has EVOLVED

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

        analysis = {"consensus": [], "disagreement_frontier": []}

        # Try to extract consensus points
        consensus_section = re.search(
            r'consensus[:\s]+(.*?)(?:disagreement|frontier|$)',
            response,
            re.IGNORECASE | re.DOTALL
        )
        if consensus_section:
            points = re.findall(r'[-*•]\s*(.+)', consensus_section.group(1))
            analysis["consensus"] = [p.strip() for p in points if p.strip()]

        # Try to extract disagreement frontier
        frontier_section = re.search(
            r'(?:disagreement|frontier)[:\s]+(.*?)$',
            response,
            re.IGNORECASE | re.DOTALL
        )
        if frontier_section:
            issues = re.findall(
                r'(?:issue|topic|point)[:\s]*(.+?)(?:\n|$)',
                frontier_section.group(1),
                re.IGNORECASE
            )
            for issue in issues[:4]:  # Max 4 issues (matches guidance)
                analysis["disagreement_frontier"].append({
                    "core_issue": issue.strip(),
                    "a_stance": "Not reliably parsed; see transcript.",
                    "b_stance": "Not reliably parsed; see transcript."
                })

        return analysis
