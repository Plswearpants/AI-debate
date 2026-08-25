"""
Crowd Agent - Manages diverse persona voting swarm with personal journals.

Uses: OpenRouter or Lambda GPU for batch inference
Responsibilities:
- Maintain diverse personas with topic-relevant dimensions and life experiences
- Vote 0: Vote on stance preference (determines team assignments)
- Vote 1+: Two-pass voting (score first, then journal entry)
- Track opinion shifts via personal journals (cumulative memory)
- Enforce consistency: justify score changes relative to baseline
- Update crowd_opinion.json with votes and journals
"""

import json
from typing import Dict, Any, List, Optional
from datetime import datetime

from src.agents.base import Agent, AgentContext, AgentResponse, FileUpdate, FileUpdateOperation
from src.clients.lambda_client import LambdaGPUClient
from src.utils.schemas import get_schema


class CrowdAgent(Agent):
    """Agent that manages crowd voting with diverse personas and personal journals."""

    def __init__(
        self,
        name: str,
        file_manager,
        config,
        raw_data_logger=None,
        personas: Optional[List[Dict[str, Any]]] = None
    ):
        super().__init__(name, "crowd", file_manager)
        self.config = config

        if config.use_openrouter_for_crowd and config.openrouter_api_key:
            from src.clients.openrouter_client import OpenRouterClient, create_lambda_adapter
            openrouter_client = OpenRouterClient(api_key=config.openrouter_api_key, raw_data_logger=raw_data_logger)
            self.lambda_client = create_lambda_adapter(openrouter_client, config.crowd_model, agent_name="crowd")
        elif config.lambda_gpu_endpoint:
            self.lambda_client = LambdaGPUClient(
                endpoint=config.lambda_gpu_endpoint,
                api_key=config.lambda_gpu_api_key
            )
        else:
            raise ValueError(
                "Crowd agent requires either:\n"
                "  - OPENROUTER_API_KEY + USE_OPENROUTER_FOR_CROWD=true, OR\n"
                "  - LAMBDA_GPU_ENDPOINT (for direct Lambda GPU)"
            )

        if personas:
            self.personas = personas
        else:
            persisted_personas = self._load_persisted_personas()
            self.personas = persisted_personas or self._load_personas(config.crowd_size)

    async def execute_turn(self, context: AgentContext) -> AgentResponse:
        try:
            if context.round_number == 0:
                return await self._execute_vote_zero(context)
            return await self._execute_two_pass_vote(context)
        except Exception as e:
            error_detail = str(e).strip() or repr(e)
            return self.create_response(
                success=False,
                output={},
                errors=[f"Crowd voting failed: {error_detail}"]
            )

    # ------------------------------------------------------------------
    # Vote 0: baseline stance preference (same as before, no journal yet)
    # ------------------------------------------------------------------

    async def _execute_vote_zero(self, context: AgentContext) -> AgentResponse:
        prompts = [self._build_vote_zero_prompt(p, context) for p in self.personas]

        responses = await self.lambda_client.generate_batch(
            prompts=prompts,
            temperature=self.config.crowd_temperature,
            max_tokens=self.config.max_tokens_crowd
        )

        votes = []
        for persona, response in zip(self.personas, responses):
            try:
                vote = self._parse_vote(response, persona)
                votes.append(vote)
            except Exception as e:
                print(f"⚠️  Failed to parse vote from {persona['id']}: {e}")
                continue

        file_update = self._create_crowd_update(votes, context.round_number)
        avg_score = sum(v["score"] for v in votes) / len(votes) if votes else 0

        return self.create_response(
            success=True,
            output={"votes": votes, "average_score": round(avg_score, 1), "voter_count": len(votes)},
            file_updates=[file_update],
            metadata={"average_score": round(avg_score, 1), "voter_count": len(votes)}
        )

    # ------------------------------------------------------------------
    # Two-pass voting: score first, then journal entry
    # ------------------------------------------------------------------

    async def _execute_two_pass_vote(self, context: AgentContext) -> AgentResponse:
        voter_data = self._load_voter_data(context)

        # --- Pass 1: Score only ---
        score_prompts = [
            self._build_score_prompt(p, context, voter_data.get(p["id"]))
            for p in self.personas
        ]
        score_responses = await self.lambda_client.generate_batch(
            prompts=score_prompts,
            temperature=self.config.crowd_temperature,
            max_tokens=30
        )

        scores = {}
        for persona, resp in zip(self.personas, score_responses):
            scores[persona["id"]] = self._extract_score(resp, persona)

        # --- Pass 2: Journal entry only for final vote or large deltas (>10) ---
        is_final_vote = "cast final vote on overall debate" in (context.instructions or "").lower()
        journal_targets: List[Dict[str, Any]] = []
        for p in self.personas:
            vid = p["id"]
            vd = voter_data.get(vid, {})
            prev = vd.get("current_score") if vd else None
            change = abs(scores[vid] - prev) if prev is not None else 0

            should_write_journal = is_final_vote or change > 10
            if not should_write_journal:
                continue

            if change >= 25:
                token_limit = 240
            elif change >= 15:
                token_limit = 180
            elif change >= 3:
                token_limit = 120
            else:
                token_limit = 60

            journal_targets.append({
                "persona": p,
                "token_limit": token_limit,
                "prompt": self._build_journal_prompt(p, context, scores[vid], vd),
            })

        journal_text_by_voter: Dict[str, str] = {}
        if journal_targets:
            max_journal_tokens = max(t["token_limit"] for t in journal_targets)
            journal_responses = await self.lambda_client.generate_batch(
                prompts=[t["prompt"] for t in journal_targets],
                temperature=self.config.crowd_temperature,
                max_tokens=max_journal_tokens
            )
            for target, journal_resp in zip(journal_targets, journal_responses):
                persona = target["persona"]
                token_limit = target["token_limit"]
                char_limit = token_limit * 4
                journal_text_by_voter[persona["id"]] = self._truncate_at_sentence(
                    journal_resp.strip(),
                    char_limit
                )

        # --- Combine into votes ---
        votes = []
        for persona in self.personas:
            vid = persona["id"]
            score = scores[vid]
            journal_text = journal_text_by_voter.get(vid, "")

            vd = voter_data.get(vid, {})
            prev_score = vd.get("current_score")
            vote_label = context.instructions or f"Round {context.round_number}"

            full_entry = None
            if journal_text:
                journal_header = f"## {vote_label} | Score: {score}"
                if prev_score is not None:
                    delta = score - prev_score
                    direction = "↑" if delta > 0 else ("↓" if delta < 0 else "→")
                    journal_header += f" ({direction}{abs(delta)} from {prev_score})"
                full_entry = f"{journal_header}\n{journal_text}"

            votes.append({
                "voter_id": vid,
                "persona": persona["name"],
                "persona_description": persona.get("life_experience", persona.get("description", "")),
                "persona_type": persona.get("type", "general"),
                "score": score,
                "rationale": (journal_text[:200] if journal_text else f"Score update: {score}"),
                **({"journal_entry": full_entry} if full_entry else {})
            })

        file_update = self._create_crowd_update(votes, context.round_number)
        avg_score = sum(v["score"] for v in votes) / len(votes) if votes else 0

        return self.create_response(
            success=True,
            output={"votes": votes, "average_score": round(avg_score, 1), "voter_count": len(votes)},
            file_updates=[file_update],
            metadata={"average_score": round(avg_score, 1), "voter_count": len(votes)}
        )

    # ------------------------------------------------------------------
    # Prompt builders
    # ------------------------------------------------------------------

    def _build_vote_zero_prompt(self, persona: Dict[str, Any], context: AgentContext) -> str:
        life_exp = persona.get("life_experience", persona.get("description", ""))

        return f"""You are: {persona['name']}
{life_exp}

Topic: {context.topic}

This is the initial vote BEFORE any debate arguments. Based on your life experience and values, what is your initial stance on this topic?

**SCORING SCHEME (-50 to 50):**
• -50 to -1: AGAINST the proposal (oppose it)
  - -50 to -26: Strongly against
  - -25 to -1: Moderately against
• 0: Neutral / undecided
• 1 to 50: FOR the proposal (support it)
  - 1 to 25: Moderately for
  - 26 to 50: Strongly for

Return JSON: {{"score": <-50 to 50>, "reasoning": "<brief explanation of your initial stance>"}}"""

    def _build_score_prompt(
        self,
        persona: Dict[str, Any],
        context: AgentContext,
        voter_data: Optional[Dict[str, Any]]
    ) -> str:
        life_exp = persona.get("life_experience", persona.get("description", ""))
        journal = ""
        vote_history_text = ""
        baseline_score = None
        prev_score = None

        if voter_data:
            journal = voter_data.get("journal", "")
            history = voter_data.get("voting_history", [])
            if history:
                baseline_score = history[0].get("score")
                prev_score = voter_data.get("current_score", history[-1].get("score"))
                vote_history_text = "Your vote history: " + ", ".join(
                    f"R{h['round']}={h['score']}" for h in history
                )

        public_transcript = context.current_state.get("history_chat", {}).get("public_transcript", [])
        mode = getattr(self.config, "crowd_context_mode", "full_transcript")

        prompt = f"""You are: {persona['name']}
{life_exp}

Topic: {context.topic}
"""

        if journal:
            prompt += f"""
YOUR PERSONAL JOURNAL (your thoughts so far):
{journal[-1500:]}

"""

        if mode == "full_transcript":
            transcript_chunks: List[str] = []
            for turn in public_transcript:
                speaker = str(turn.get("speaker", "?")).upper()
                round_label = turn.get("round_label") or f"Round {turn.get('round_number', '?')}"
                statement = (turn.get("statement", "") or "").strip()
                if not statement:
                    continue
                transcript_chunks.append(f"[{round_label}] Team {speaker}:\n{statement}")

            if transcript_chunks:
                prompt += "FULL PUBLIC TRANSCRIPT SO FAR:\n\n"
                prompt += "\n\n".join(transcript_chunks)
                prompt += "\n\n"
            else:
                prompt += "No public transcript is available yet.\n\n"
        else:
            # latest_plus_latent: lower token mode using freshest statements + judge latent map
            last_a = ""
            last_b = ""
            for turn in reversed(public_transcript):
                if turn.get("speaker") == "a" and not last_a:
                    last_a = (turn.get("statement", "") or "").strip()
                elif turn.get("speaker") == "b" and not last_b:
                    last_b = (turn.get("statement", "") or "").strip()
                if last_a and last_b:
                    break

            prompt += f"""Team A's latest argument:
{last_a if last_a else 'No statement yet'}

Team B's latest argument:
{last_b if last_b else 'No statement yet'}

"""

            debate_latent = context.current_state.get("debate_latent", {})
            round_history = debate_latent.get("round_history", [])
            if round_history:
                latest_latent = round_history[-1]
                consensus = latest_latent.get("consensus", [])
                frontier = latest_latent.get("disagreement_frontier", [])

                if consensus:
                    prompt += "JUDGE CONSENSUS SNAPSHOT:\n"
                    for point in consensus[-6:]:
                        prompt += f"- {point}\n"
                    prompt += "\n"

                if frontier:
                    prompt += "JUDGE DISAGREEMENT FRONTIER:\n"
                    for issue in frontier[-5:]:
                        core = issue.get("core_issue", "Unknown issue")
                        a_stance = issue.get("a_stance", "")
                        b_stance = issue.get("b_stance", "")
                        prompt += (
                            f"- {core}\n"
                            f"  Team A: {a_stance}\n"
                            f"  Team B: {b_stance}\n"
                        )
                    prompt += "\n"
        if vote_history_text:
            prompt += f"{vote_history_text}\n"
        if baseline_score is not None:
            prompt += f"Your baseline score (before debate): {baseline_score}\n"
        if prev_score is not None:
            prompt += f"Your most recent score: {prev_score}\n"

        prompt += """
**SCORING (-50 to 50):** -50 to -1 = favor Team B, 0 = neutral, 1 to 50 = favor Team A.

CONSISTENCY RULE: You are the same person throughout this debate. Your score should only change if a specific argument or evidence justifies it. Random swings are not allowed.

Respond with ONLY a single integer (your score). Nothing else."""

        return prompt

    def _build_journal_prompt(
        self,
        persona: Dict[str, Any],
        context: AgentContext,
        new_score: int,
        voter_data: Optional[Dict[str, Any]]
    ) -> str:
        life_exp = persona.get("life_experience", persona.get("description", ""))
        prev_score = None
        baseline_score = None

        if voter_data:
            history = voter_data.get("voting_history", [])
            if history:
                baseline_score = history[0].get("score")
                prev_score = voter_data.get("current_score", history[-1].get("score"))

        score_change = abs(new_score - prev_score) if prev_score is not None else 0

        if score_change >= 20:
            length_guide = "Write 3-4 sentences explaining what specifically changed your mind. This is a major shift and must be well justified."
        elif score_change >= 10:
            length_guide = "Write 2-3 sentences on what influenced your updated view."
        elif score_change >= 3:
            length_guide = "Write 1-2 sentences noting what you found notable."
        else:
            length_guide = "Write 1 sentence on your current thinking."

        prompt = f"""You are: {persona['name']}
{life_exp}

You just scored this debate round: {new_score} (scale: -50 to 50; negative = favor Team B, positive = favor Team A, 0 = neutral).
"""
        if baseline_score is not None:
            prompt += f"Your baseline (pre-debate) score was: {baseline_score}\n"
        if prev_score is not None:
            prompt += f"Your previous score was: {prev_score} (change: {new_score - prev_score:+d})\n"

        prompt += f"""
Write a personal journal entry reflecting on this round of the debate. {length_guide}

Focus on: what arguments resonated or fell flat, what evidence mattered to you, and why your score changed or stayed the same. Write from your personal perspective.

Journal entry:"""

        return prompt

    # ------------------------------------------------------------------
    # Text helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _truncate_at_sentence(text: str, max_chars: int) -> str:
        """Truncate text at the last complete sentence before max_chars."""
        if len(text) <= max_chars:
            return text
        truncated = text[:max_chars]
        last_period = max(truncated.rfind('. '), truncated.rfind('.\n'), truncated.rfind('.'))
        last_exclam = truncated.rfind('! ')
        last_question = truncated.rfind('? ')
        boundary = max(last_period, last_exclam, last_question)
        if boundary > max_chars // 3:
            return truncated[:boundary + 1].strip()
        return truncated.strip()

    # ------------------------------------------------------------------
    # Score extraction (Pass 1 parsing)
    # ------------------------------------------------------------------

    def _extract_score(self, response: str, persona: Dict[str, Any]) -> int:
        import re
        text = response.strip()

        # Try direct integer parse
        try:
            score = int(text)
            return max(-50, min(50, score))
        except ValueError:
            pass

        # Try to find a number in the response
        match = re.search(r'(?<!\d)-?\d{1,3}(?!\d)', text)
        if match:
            score = int(match.group(0))
            if -50 <= score <= 50:
                return score

        # Try JSON parse
        try:
            from src.utils.json_parser import parse_json_response
            data = parse_json_response(text)
            score = data.get("score", 0)
            return max(-50, min(50, int(score)))
        except (json.JSONDecodeError, ValueError, TypeError):
            pass

        print(f"Warning: Could not parse score for {persona['id']}, using fallback: 0")
        return 0

    # ------------------------------------------------------------------
    # Legacy vote parsing (for Vote 0 backward compat)
    # ------------------------------------------------------------------

    def _parse_vote(self, response: str, persona: Dict[str, Any]) -> Dict[str, Any]:
        import re
        from src.utils.json_parser import parse_json_response

        try:
            vote_data = parse_json_response(response)
            score = vote_data.get("score", 0)
            reasoning = vote_data.get("reasoning", vote_data.get("rationale", ""))
        except json.JSONDecodeError:
            score_match = re.search(r'"?score"?\s*[:\s]+(-?\d+)', response, re.IGNORECASE)
            if score_match:
                score = int(score_match.group(1))
                reasoning = response[:200]
            else:
                number_match = re.search(r'(?<!\d)-?\d{1,3}(?!\d)', response)
                score = int(number_match.group(0)) if number_match else 0
                reasoning = response[:200]
                print(f"Warning: Could not parse vote JSON for {persona['id']}, using fallback score: {score}")

        score = max(-50, min(50, score))

        return {
            "voter_id": persona["id"],
            "persona": persona["name"],
            "persona_description": persona.get("life_experience", persona.get("description", "")),
            "persona_type": persona.get("type", "general"),
            "score": score,
            "rationale": reasoning[:200]
        }

    # ------------------------------------------------------------------
    # File updates
    # ------------------------------------------------------------------

    def _create_crowd_update(self, votes: List[Dict[str, Any]], round_number: int) -> FileUpdate:
        avg_score = sum(v["score"] for v in votes) / len(votes) if votes else 0

        return FileUpdate(
            file_type="crowd_opinion",
            operation=FileUpdateOperation.ADD_CROWD_VOTE,
            data={
                "round": round_number,
                "votes": votes,
                "average_score": round(avg_score, 1),
                "vote_count": len(votes),
                "timestamp": datetime.now().isoformat()
            }
        )

    # ------------------------------------------------------------------
    # Voter data loading
    # ------------------------------------------------------------------

    def _load_voter_data(self, context: AgentContext) -> Dict[str, Dict[str, Any]]:
        crowd_opinion = context.current_state.get("crowd_opinion", {})
        voters = crowd_opinion.get("voters", [])
        return {v["voter_id"]: v for v in voters}

    def _load_persisted_personas(self) -> Optional[List[Dict[str, Any]]]:
        """
        Load personas from debate storage so resumed runs keep the same voters.
        """
        try:
            personas_data = self.file_manager._read_json("personas")
            personas = personas_data.get("personas", [])
            if personas:
                return personas
        except Exception:
            pass

        # Backward compatibility: older debates may only have personas in crowd_opinion.
        try:
            crowd_data = self.file_manager._read_json("crowd_opinion")
            personas = crowd_data.get("personas", [])
            if personas:
                return personas
        except Exception:
            pass

        return None

    # ------------------------------------------------------------------
    # Default persona generation (fallback if moderator doesn't provide)
    # ------------------------------------------------------------------

    def _load_personas(self, count: int) -> List[Dict[str, Any]]:
        persona_templates = [
            {"type": "political", "name": "Progressive Activist", "description": "Strong advocate for social justice and government intervention"},
            {"type": "political", "name": "Fiscal Conservative", "description": "Prioritizes low taxes, limited government, free markets"},
            {"type": "political", "name": "Libertarian", "description": "Values individual freedom and minimal government"},
            {"type": "political", "name": "Social Democrat", "description": "Supports mixed economy and social safety net"},
            {"type": "political", "name": "Moderate Independent", "description": "Pragmatic centrist, case-by-case evaluation"},
            {"type": "professional", "name": "Economist", "description": "PhD economist focused on data and empirical evidence"},
            {"type": "professional", "name": "Small Business Owner", "description": "Practical perspective on business and employment"},
            {"type": "professional", "name": "Social Worker", "description": "Front-line experience with poverty and social programs"},
            {"type": "professional", "name": "Tech Entrepreneur", "description": "Innovation-focused, disruption-oriented thinking"},
            {"type": "professional", "name": "Public School Teacher", "description": "Education and community welfare perspective"},
            {"type": "demographic", "name": "Working Class Parent", "description": "Struggles with bills, childcare, job security"},
            {"type": "demographic", "name": "Retired Senior", "description": "Fixed income, healthcare concerns, traditional values"},
            {"type": "demographic", "name": "College Student", "description": "Young, idealistic, concerned about future opportunities"},
            {"type": "demographic", "name": "Rural Resident", "description": "Small town perspective, self-reliance values"},
            {"type": "demographic", "name": "Urban Professional", "description": "City dweller, cosmopolitan, career-focused"},
            {"type": "stakeholder", "name": "Healthcare Worker", "description": "Insider view of healthcare system challenges"},
            {"type": "stakeholder", "name": "Environmental Advocate", "description": "Climate and sustainability priority"},
            {"type": "stakeholder", "name": "Union Representative", "description": "Worker rights and collective bargaining focus"},
            {"type": "stakeholder", "name": "Corporate Executive", "description": "Business efficiency and shareholder value perspective"},
            {"type": "stakeholder", "name": "Nonprofit Director", "description": "Mission-driven, community impact focused"}
        ]

        personas = []
        for i in range(count):
            template = persona_templates[i % len(persona_templates)]
            persona = {
                "id": f"v_{i+1:03d}",
                "name": f"{template['name']} #{i//len(persona_templates) + 1}",
                "description": template["description"],
                "life_experience": template["description"],
                "type": template["type"]
            }
            personas.append(persona)

        return personas

    def get_personas_summary(self) -> Dict[str, Any]:
        by_type = {}
        for persona in self.personas:
            ptype = persona.get("type", "unknown")
            by_type[ptype] = by_type.get(ptype, 0) + 1

        return {
            "total_personas": len(self.personas),
            "by_type": by_type,
            "sample_personas": self.personas[:5]
        }
