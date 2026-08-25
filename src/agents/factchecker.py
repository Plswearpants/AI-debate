"""
FactChecker Agent - Verifies citations with rigorous source analysis.

Uses: Perplexity Sonar Pro (with built-in web search)
Responsibilities:
- OFFENSE: Scrutinize opponent's citations (credibility + correspondence)
- DEFENSE: Respond to adversary scores on our citations
- Update citation_pool with verification scores
"""

import json
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from src.agents.base import Agent, AgentContext, AgentResponse, FileUpdate, FileUpdateOperation
from src.clients.perplexity_client import PerplexityClient
from src.utils.schemas import get_schema


class FactCheckerAgent(Agent):
    """Agent that verifies citations and responds to criticism."""
    
    def __init__(
        self,
        name: str,
        team: str,
        file_manager,
        config,
        raw_data_logger=None
    ):
        """
        Initialize fact-checker agent.
        
        Args:
            name: Agent name ("factchecker_a" or "factchecker_b")
            team: Team identifier ("a" or "b")
            file_manager: FileManager instance
            config: Configuration object
            raw_data_logger: Optional RawDataLogger for logging all model calls
        """
        super().__init__(name, "factchecker", file_manager)
        self.team = team
        self.opponent_team = 'b' if team == 'a' else 'a'
        self.config = config
        
        # Initialize client based on configuration
        if config.openrouter_api_key:
            # Use OpenRouter
            from src.clients.openrouter_client import OpenRouterClient, create_perplexity_adapter
            openrouter_client = OpenRouterClient(api_key=config.openrouter_api_key, raw_data_logger=raw_data_logger)
            self.perplexity = create_perplexity_adapter(
                openrouter_client,
                config.factchecker_model,
                agent_name=f"factchecker_{team}"
            )
        elif config.perplexity_api_key:
            # Use direct Perplexity API
            self.perplexity = PerplexityClient(
                api_key=config.perplexity_api_key,
                model=config.factchecker_model
            )
        else:
            raise ValueError(
                "FactChecker requires either OPENROUTER_API_KEY or PERPLEXITY_API_KEY"
            )
    
    async def execute_turn(self, context: AgentContext) -> AgentResponse:
        """
        Execute fact-checker's turn.
        
        Performs both defense (respond to criticism) and offense (verify opponent).
        
        Args:
            context: Current debate context
        
        Returns:
            AgentResponse with verification results and file updates
        """
        try:
            file_updates = []
            results = {
                "offense": {},
                "defense": {}
            }
            
            # DEFENSE: Respond to adversary scores on our citations
            defense_updates, defense_results = await self._defend_citations(context)
            file_updates.extend(defense_updates)
            results["defense"] = defense_results
            
            # OFFENSE: Verify opponent's citations
            offense_updates, offense_results = await self._verify_citations(context)
            file_updates.extend(offense_updates)
            results["offense"] = offense_results
            
            return self.create_response(
                success=True,
                output=results,
                file_updates=file_updates,
                metadata={
                    "citations_verified": len(offense_results),
                    "defenses_made": len(defense_results)
                }
            )
        
        except Exception as e:
            return self.create_response(
                success=False,
                output={},
                errors=[f"FactChecker turn failed: {str(e)}"]
            )
    
    async def _verify_citations(self, context: AgentContext) -> Tuple[List[FileUpdate], Dict[str, Any]]:
        """
        OFFENSE: Verify opponent's recent citations.
        
        Args:
            context: Debate context
        
        Returns:
            Tuple of (file_updates, verification_results)
        """
        file_updates = []
        results = {}
        
        # Get opponent's recent citations
        opponent_citations = self._get_opponent_recent_citations(context)
        
        if not opponent_citations:
            return file_updates, results
        
        # Verify each citation
        for citation_key, citation_data in opponent_citations.items():
            try:
                verification = await self._verify_single_citation(
                    citation_key=citation_key,
                    citation_data=citation_data
                )
                
                # Create file update
                file_updates.append(FileUpdate(
                    file_type="citation_pool",
                    operation=FileUpdateOperation.UPDATE_VERIFICATION,
                    data={
                        "team": self.opponent_team,
                        "key": citation_key,
                        "verification": verification
                    }
                ))
                
                results[citation_key] = verification
            
            except Exception as e:
                print(f"⚠️  Failed to verify {citation_key}: {e}")
                continue
        
        return file_updates, results
    
    async def _verify_single_citation(
        self,
        citation_key: str,
        citation_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Verify a single citation by evaluating:
        1. Content correspondence: does the claim match the cited source?
        2. Source credibility: is the source trustworthy?
        """
        claim = citation_data.get("claim_in_debate", "")
        source_title = citation_data.get("source_title", citation_data.get("metadata", {}).get("title", ""))
        source_url = citation_data.get("source_url", "")
        relevant_quote = citation_data.get("relevant_quote", citation_data.get("metadata", {}).get("snippet", ""))
        has_url = citation_data.get("has_verified_url", bool(source_url and "scholar.google.com/scholar?q=" not in source_url))
        
        prompt = f"""You are a rigorous fact-checker in an academic-style debate.

CITATION [{citation_key}]:
- Claim made in debate: "{claim}"
- Source title: "{source_title}"
- Quoted from source: "{relevant_quote}"
{"- Source URL: " + source_url if has_url else "- No verified URL provided"}

YOUR TASK — evaluate this citation on two dimensions:

1. CONTENT CORRESPONDENCE (1-10):
   Like an academic reviewer: does the quoted passage actually support the claim?
   - 9-10: Quote directly and accurately supports the claim
   - 6-8: Quote generally supports but claim slightly overstates or simplifies
   - 3-5: Weak connection; claim stretches what the source says
   - 1-2: Misrepresentation; the source doesn't support this claim

2. SOURCE CREDIBILITY (1-10):
   Based on the source title, type, and what you can independently verify:
   - 9-10: Peer-reviewed journal, government data, authoritative institution
   - 6-8: Reputable news, well-known think tank, expert opinion
   - 3-5: Blog, opinion piece, unverified report
   - 1-2: Source appears fabricated, non-existent, or unreliable

3. ADVERSARY COMMENT (2-3 sentences):
   Explain your scores. Point out specific issues: misrepresentation,
   cherry-picking, source quality concerns, or fabrication.

Return JSON: {{"source_credibility_score": <1-10>, "content_correspondence_score": <1-10>, "adversary_comment": "<your analysis>"}}"""
        
        # Get structured output from Perplexity
        schema = get_schema("factchecker", "verification")
        
        response = await self.perplexity.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=self.config.factchecker_temperature,
            max_tokens=self.config.max_tokens_factchecker,
            search_recency_filter=None  # Let Perplexity decide
        )
        
        # Parse JSON response
        try:
            from src.utils.json_parser import parse_json_response
            verification = parse_json_response(response)
            
            # Add metadata
            verification["verified_by"] = self.name
            verification["verified_at"] = datetime.now().isoformat()
            verification["proponent_response"] = None  # Will be filled by defense
            
            return verification
        
        except json.JSONDecodeError:
            # Fallback: extract scores from text
            return self._parse_verification_fallback(response)
    
    async def _defend_citations(self, context: AgentContext) -> Tuple[List[FileUpdate], Dict[str, Any]]:
        """
        DEFENSE: Respond to adversary scores on our citations.
        
        Args:
            context: Debate context
        
        Returns:
            Tuple of (file_updates, defense_results)
        """
        file_updates = []
        results = {}
        
        # Get our citations that have adversary comments needing response
        citations_to_defend = self._get_our_citations_needing_defense(context)
        
        if not citations_to_defend:
            return file_updates, results
        
        # Generate defense for each
        for citation_key, citation_data in citations_to_defend.items():
            try:
                adversary_comment = citation_data["verification"]["adversary_comment"]
                
                defense_response = await self._generate_defense_response(
                    citation_key=citation_key,
                    citation_data=citation_data,
                    adversary_comment=adversary_comment
                )
                
                # Update citation with our response
                file_updates.append(FileUpdate(
                    file_type="citation_pool",
                    operation=FileUpdateOperation.UPDATE_VERIFICATION,
                    data={
                        "team": self.team,
                        "key": citation_key,
                        "verification": {
                            "proponent_response": defense_response
                        }
                    }
                ))
                
                results[citation_key] = defense_response
            
            except Exception as e:
                print(f"⚠️  Failed to defend {citation_key}: {e}")
                continue
        
        return file_updates, results
    
    async def _generate_defense_response(
        self,
        citation_key: str,
        citation_data: Dict[str, Any],
        adversary_comment: str
    ) -> str:
        """
        Generate defense response to adversary criticism.
        
        Args:
            citation_key: Citation key
            citation_data: Citation data
            adversary_comment: Opponent's criticism
        
        Returns:
            Defense response text
        """
        claim = citation_data.get("claim_in_debate", "")
        source_title = citation_data.get("source_title", citation_data.get("metadata", {}).get("title", ""))
        relevant_quote = citation_data.get("relevant_quote", citation_data.get("metadata", {}).get("snippet", ""))
        
        prompt = f"""You are defending your team's citation that was criticized by the opponent.

Your Citation: [{citation_key}]
Your claim: "{claim}"
Source: "{source_title}"
Your quoted evidence: "{relevant_quote}"

Opponent's Criticism:
{adversary_comment}

Generate a brief, professional response (2-3 sentences) that:
1. Acknowledges valid criticisms if warranted
2. Clarifies any misrepresentation claims with evidence
3. Provides additional context about the source's credibility
4. Maintains your team's credibility

Be concise, professional, and effective. Do not be defensive or dismissive."""
        
        # Use Perplexity for informed response (can verify our source)
        response = await self.perplexity.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,  # More factual for defense
            max_tokens=200,   # Keep it brief
            search_recency_filter=None
        )
        
        return response.strip()
    
    def _get_opponent_recent_citations(self, context: AgentContext) -> Dict[str, Dict[str, Any]]:
        """
        Get opponent's recent citations that need verification.
        
        Args:
            context: Debate context
        
        Returns:
            Dictionary of {citation_key: citation_data}
        """
        citations = {}
        
        # Get citation pool from context
        citation_pool = context.current_state.get("citation_pool", {})
        opponent_team_key = f"team {self.opponent_team}"
        
        if opponent_team_key not in citation_pool.get("citations", {}):
            return citations
        
        opponent_citations = citation_pool["citations"][opponent_team_key]
        
        # Get citations from current round that haven't been verified yet
        for key, data in opponent_citations.items():
            if data.get("added_in_round") == context.round_number:
                # Check if already verified by us
                verification = data.get("verification", {})
                if not verification.get("verified_by") or verification.get("verified_by") != self.name:
                    citations[key] = data
        
        return citations
    
    def _get_our_citations_needing_defense(self, context: AgentContext) -> Dict[str, Dict[str, Any]]:
        """
        Get our team's citations that have adversary comments needing response.
        
        Args:
            context: Debate context
        
        Returns:
            Dictionary of {citation_key: citation_data}
        """
        citations = {}
        
        # Get citation pool from context
        citation_pool = context.current_state.get("citation_pool", {})
        our_team_key = f"team {self.team}"
        
        if our_team_key not in citation_pool.get("citations", {}):
            return citations
        
        our_citations = citation_pool["citations"][our_team_key]
        
        # Get citations that have adversary comments but no proponent response yet
        for key, data in our_citations.items():
            verification = data.get("verification", {})
            if verification.get("adversary_comment") and not verification.get("proponent_response"):
                citations[key] = data
        
        return citations
    
    def _parse_verification_fallback(self, response: str) -> Dict[str, Any]:
        """
        Fallback parser if JSON parsing fails.
        
        Attempts to extract scores and comment from text.
        
        Args:
            response: Text response from Perplexity
        
        Returns:
            Verification dictionary
        """
        # Try to extract scores using regex
        import re
        
        credibility_match = re.search(r'credibility.*?(\d+)', response, re.IGNORECASE)
        correspondence_match = re.search(r'correspondence.*?(\d+)', response, re.IGNORECASE)
        
        credibility_score = int(credibility_match.group(1)) if credibility_match else 5
        correspondence_score = int(correspondence_match.group(1)) if correspondence_match else 5
        
        # Clamp to 1-10 range
        credibility_score = max(1, min(10, credibility_score))
        correspondence_score = max(1, min(10, correspondence_score))
        
        return {
            "source_credibility_score": credibility_score,
            "content_correspondence_score": correspondence_score,
            "adversary_comment": response[:300],  # Use full response as comment
            "verified_by": self.name,
            "verified_at": datetime.now().isoformat(),
            "proponent_response": None
        }
