"""
Debator Agent - Generates arguments with deep research.

Uses: Gemini 1.5 Pro + MCP Browser for research
Responsibilities:
- Deep research on topic using MCP
- Generate opening, rebuttal, and closing statements based on the stance and previous statements with citations
- Add citations to citation pool
- Target disagreement frontier in rebuttals

"""

import re
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

from src.agents.base import Agent, AgentContext, AgentResponse, FileUpdate, FileUpdateOperation
from src.clients.gemini_client import GeminiClient
from src.utils.schemas import get_schema
from src.utils.cost_controls import CostTracker, ResearchTier, get_research_tier_for_budget, estimate_deep_research_cost
import json
from src.clients.mcp_client import MCPBrowserClient, SearchResult


class DebatorAgent(Agent):
    """Agent that generates debate arguments with research."""
    
    def __init__(
        self,
        name: str,
        team: str,
        stance: str,
        file_manager,
        config,
        raw_data_logger=None
    ):
        """
        Initialize debator agent.
        
        Args:
            name: Agent name ("debator_a" or "debator_b")
            team: Team identifier ("a" or "b")
            stance: Stance description (e.g., "for", "against")
            file_manager: FileManager instance
            config: Configuration object
            raw_data_logger: Optional RawDataLogger for logging all model calls
        """
        super().__init__(name, "debator", file_manager)
        self.team = team
        self.stance = stance
        self.config = config
        
        # Initialize client based on configuration
        if config.openrouter_api_key:
            # Use OpenRouter
            from src.clients.openrouter_client import OpenRouterClient, create_gemini_adapter
            openrouter_client = OpenRouterClient(api_key=config.openrouter_api_key, raw_data_logger=raw_data_logger)
            self.gemini = create_gemini_adapter(openrouter_client, config.gemini_model, config.perplexity_model, agent_name=f"debator_{team}")
        elif config.gemini_api_key:
            # Use direct Gemini API
            self.gemini = GeminiClient(
                api_key=config.gemini_api_key,
                model=config.gemini_model
            )
        else:
            raise ValueError(
                "Debator requires either OPENROUTER_API_KEY or GEMINI_API_KEY"
            )
        
        # Initialize cost tracker
        self.cost_tracker = CostTracker(config.cost_budget) if config.cost_budget else None
    
    async def execute_turn(self, context: AgentContext) -> AgentResponse:
        """
        Execute debator's turn.
        
        Args:
            context: Current debate context
        
        Returns:
            AgentResponse with statement and file updates
        """
        try:
            phase = context.phase
            
            if phase == "opening":
                return await self._generate_opening(context)
            elif phase == "rebuttal":
                return await self._generate_rebuttal(context)
            elif phase == "closing":
                return await self._generate_closing(context)
            else:
                raise ValueError(f"Unknown phase: {phase}")
        
        except Exception as e:
            return self.create_response(
                success=False,
                output={},
                errors=[f"Debator turn failed: {str(e)}"]
            )
    
    async def _generate_opening(self, context: AgentContext) -> AgentResponse:
        """
        Generate opening statement with research.
        
        Steps:
        1. Deep research using Gemini Deep Research agent
        2. Generate opening statement based on research
        3. Extract citations and add to pool
        4. Create file updates
        """
        # Step 1: Research using Gemini Deep Research
        research_report = await self._deep_research(context.topic)
        
        # Step 2: Extract sources from research report
        sources = self._parse_research_sources(research_report)
        
        # Step 3: Generate statement based on research
        statement, supplementary = await self._generate_statement(
            context=context,
            research_report=research_report,
            sources=sources,
            statement_type="opening"
        )
        
        # Step 4: Extract and register citations
        citations = self._extract_citations(statement + supplementary)
        file_updates = await self._register_citations(
            citations,
            sources,
            context.round_number,
            turn_id=f"turn_{context.round_number:03d}_{self.team}"
        )
        
        # Step 4: Create turn update
        turn_data = {
            "turn_id": f"turn_{context.round_number:03d}_{self.team}",
            "round_number": context.round_number,
            "round_label": "Opening",
            "phase": "Phase 1",
            "speaker": self.team,
            "agent": self.name,
            "timestamp": datetime.now().isoformat(),
            "statement": statement,
            "citations_used": citations
        }
        
        file_updates.append(FileUpdate(
            file_type="history_chat",
            operation=FileUpdateOperation.APPEND_TURN,
            data=turn_data
        ))
        
        # Add supplementary material if any
        if supplementary:
            supp_data = {
                "turn_id": turn_data["turn_id"],
                "round_number": context.round_number,
                "supplementary_material": supplementary,
                "citations_used": self._extract_citations(supplementary),
                "timestamp": datetime.now().isoformat()
            }
            
            file_updates.append(FileUpdate(
                file_type="history_chat",
                operation=FileUpdateOperation.APPEND_TURN,
                data={"speaker": self.team, **supp_data}
            ))
        
        return self.create_response(
            success=True,
            output={
                "statement": statement,
                "supplementary_material": supplementary,
                "citations": citations,
                "sources": sources,
                "research_report": research_report
            },
            file_updates=file_updates,
            metadata={"phase": "opening", "source_count": len(sources)}
        )
    
    async def _generate_rebuttal(self, context: AgentContext) -> AgentResponse:
        """
        Generate rebuttal statement targeting disagreement frontier.
        
        Uses Deep Research with debate context (Option C: Adversarial research).
        """
        # Step 1: Deep Research with adversarial focus and debate context
        research_report = await self._deep_research_with_context(context)
        
        # Step 2: Extract sources from research
        sources = self._parse_research_sources(research_report)
        
        # Step 3: Generate rebuttal based on research
        statement, supplementary = await self._generate_statement(
            context=context,
            research_report=research_report,
            sources=sources,
            statement_type="rebuttal"
        )
        
        # Step 4: Extract and register citations
        citations = self._extract_citations(statement + supplementary)
        file_updates = await self._register_citations(
            citations,
            sources,
            context.round_number,
            turn_id=f"turn_{context.round_number:03d}_{self.team}"
        )
        
        # Step 5: Create turn updates (same as opening)
        turn_data = {
            "turn_id": f"turn_{context.round_number:03d}_{self.team}",
            "round_number": context.round_number,
            "round_label": f"Rebuttal {context.round_number - 1}",
            "phase": "Phase 2",
            "speaker": self.team,
            "agent": self.name,
            "timestamp": datetime.now().isoformat(),
            "statement": statement,
            "citations_used": citations
        }
        
        file_updates.append(FileUpdate(
            file_type="history_chat",
            operation=FileUpdateOperation.APPEND_TURN,
            data=turn_data
        ))
        
        if supplementary:
            supp_data = {
                "turn_id": turn_data["turn_id"],
                "round_number": context.round_number,
                "supplementary_material": supplementary,
                "citations_used": self._extract_citations(supplementary),
                "timestamp": datetime.now().isoformat()
            }
            file_updates.append(FileUpdate(
                file_type="history_chat",
                operation=FileUpdateOperation.APPEND_TURN,
                data={"speaker": self.team, **supp_data}
            ))
        
        return self.create_response(
            success=True,
            output={
                "statement": statement,
                "supplementary_material": supplementary,
                "citations": citations,
                "sources": sources,
                "research_report": research_report
            },
            file_updates=file_updates,
            metadata={"phase": "rebuttal", "source_count": len(sources)}
        )
    
    async def _generate_closing(self, context: AgentContext) -> AgentResponse:
        """Generate closing statement (no new citations allowed)."""
        # TODO: Summarize arguments, no new research
        return self.create_response(success=True, output={"statement": "TBD"})
    
    async def _deep_research(self, topic: str, phase: str = "opening") -> str:
        """
        Perform deep research using Gemini Deep Research agent with cost controls.
        
        This uses Google's built-in Deep Research agent which:
        - Performs comprehensive web searches
        - Reads multiple sources deeply
        - Synthesizes information
        - Provides citations
        
        Includes cost monitoring and fallback to quick search if budget exceeded.
        
        Args:
            topic: The debate topic
            phase: Current phase (for cost tracking)
        
        Returns:
            Research report as text (includes sources and citations)
        """
        # Check if we can afford Deep Research
        if self.cost_tracker and not self.cost_tracker.can_afford_deep_research():
            print(f"⚠️  Budget limit reached. Falling back to quick search.")
            return await self._quick_search_fallback(topic)
        
        # Check which tier to use based on remaining budget
        research_tier = ResearchTier.DEEP  # Default
        if self.cost_tracker:
            remaining = self.cost_tracker.get_remaining_budget()
            research_tier = get_research_tier_for_budget(remaining)
            print(f"💰 Remaining budget: ${remaining:.2f} → Using {research_tier.value} research")
        
        research_query = self._build_research_query(topic)
        budget = self.config.cost_budget if self.config.cost_budget else None
        
        # Adjust Deep Research parameters based on tier
        max_wait = 300  # 5 minutes default
        if research_tier == ResearchTier.STANDARD:
            max_wait = 180  # 3 minutes for standard
            research_query += "\n\nNote: Provide concise analysis focusing on key evidence."
        
        # Use Deep Research agent
        try:
            research_report = await self.gemini.deep_research(
                query=research_query,
                background=True,
                poll_interval=10,
                max_wait=max_wait if budget else 300
            )
            
            # Estimate and record cost
            if self.cost_tracker:
                estimated_cost = estimate_deep_research_cost(
                    num_queries=budget.max_grounding_queries if budget else 20,
                    context_tokens=budget.max_context_tokens if budget else 150000,
                    output_tokens=budget.max_output_tokens if budget else 10000
                )
                self.cost_tracker.record_research_cost(estimated_cost, is_deep=True, phase=phase)
                print(f"💸 Research cost: ${estimated_cost:.2f} | Total: ${self.cost_tracker.total_cost:.2f}")
            
            return research_report
        
        except Exception as e:
            print(f"⚠️  Deep Research failed: {e}. Falling back to quick search.")
            return await self._quick_search_fallback(topic)
    
    async def _quick_search_fallback(self, topic: str) -> str:
        """
        Fallback to quick Google Search when budget is limited.
        
        Much cheaper (~$0.10) but lower quality than Deep Research.
        """
        query = f"Research {topic} focusing on {self.stance} position. Provide evidence and sources."
        
        # Use quick search with grounding
        report = await self.gemini.generate_with_search(
            prompt=query,
            temperature=0.7,
            max_tokens=2048
        )
        
        # Record cost (much cheaper)
        if self.cost_tracker:
            self.cost_tracker.record_research_cost(0.10, is_deep=False, phase="fallback")
        
        return report
    
    def _build_research_query(self, topic: str) -> str:
        """
        Build research query for Deep Research agent (Opening - Option B).
        
        Option B: Detailed research prompt for comprehensive analysis
        """
        query = f"""Research the topic: {topic}

My position: {self.stance}

Focus on:
1. Statistical evidence and empirical data
2. Academic studies and peer-reviewed research
3. Real-world case studies (successes and failures)
4. Expert opinions from economists, policy makers, and domain experts
5. Implementation challenges and solutions
6. Cost-benefit analysis
7. Economic, social, and ethical implications

Provide comprehensive analysis with specific data points and credible sources."""
        
        return query
    
    async def _deep_research_with_context(self, context: AgentContext) -> str:
        """
        Deep Research for rebuttals with debate context (Option C: Adversarial).
        
        Includes previous debate context to research both sides and counterarguments.
        Respects cost budget and may fallback to quick search.
        """
        # Check budget
        if self.cost_tracker and self.cost_tracker.should_use_quick_search():
            print(f"⚠️  Low budget. Using quick search for rebuttal.")
            return await self._quick_search_fallback(context.topic)
        # Get opponent's last statement
        opponent_team = 'b' if self.team == 'a' else 'a'
        opponent_statement = ""
        
        public_transcript = context.current_state.get("history_chat", {}).get("public_transcript", [])
        for turn in reversed(public_transcript):
            if turn.get("speaker") == opponent_team:
                opponent_statement = turn.get("statement", "")
                break
        
        # Get disagreement frontier
        frontier_issues = []
        latent = context.current_state.get("debate_latent", {})
        if latent.get("round_history"):
            latest = latent["round_history"][-1]
            frontier_issues = latest.get("disagreement_frontier", [])
        
        # Build adversarial research query (Option C)
        query = f"""Research BOTH sides of: {context.topic}

My position: {self.stance}

DEBATE CONTEXT:
Opponent's recent argument: {opponent_statement[:500]}

Key disagreement points to address:
"""
        
        for issue in frontier_issues[:3]:  # Focus on top 3 issues
            query += f"- {issue.get('core_issue', '')}\n"
        
        query += f"""

Research objectives:
1. Strongest evidence FOR my position on these specific disagreement points
2. Common counterarguments AGAINST my position
3. Effective rebuttals to those counterarguments
4. Data and studies that directly challenge opponent's claims
5. Examples that support my stance and undermine opponent's
6. Expert opinions that favor my position

Provide comprehensive analysis with credible sources and specific rebuttals."""
        
        # Use Deep Research with cost tracking
        try:
            research_report = await self.gemini.deep_research(
                query,
                background=True,
                max_wait=self.config.cost_budget.max_research_time if self.config.cost_budget else 300
            )
            
            # Record cost
            if self.cost_tracker:
                budget = self.config.cost_budget
                estimated_cost = estimate_deep_research_cost(
                    num_queries=budget.max_grounding_queries if budget else 20,
                    context_tokens=budget.max_context_tokens if budget else 150000,
                    output_tokens=budget.max_output_tokens if budget else 10000
                )
                self.cost_tracker.record_research_cost(estimated_cost, is_deep=True, phase="rebuttal")
                print(f"💸 Rebuttal research cost: ${estimated_cost:.2f} | Total: ${self.cost_tracker.total_cost:.2f}")
            
            return research_report
        
        except Exception as e:
            print(f"⚠️  Deep Research failed: {e}. Falling back to quick search.")
            return await self._quick_search_fallback(context.topic)
    
    def _parse_research_sources(self, research_report: str) -> List[Dict[str, Any]]:
        """
        Parse sources from research report.
        
        Extracts sources from:
        1. "Source List:" section (if present)
        2. Numbered citations [1], [2], [3] etc. in the report body
        3. Context around each citation to identify what it refers to
        
        For free models without web access, this creates searchable URLs.
        For models with web access (Perplexity), this extracts real URLs.
        
        Args:
            research_report: Research report from research agent
        
        Returns:
            List of sources extracted from report
        """
        import re
        
        sources = []
        seen_citation_numbers = set()
        
        # Method 1: Try to find "Source List:" section
        source_list_match = re.search(
            r'\*\*Source List:\*\*\s*(.*?)(?:\n\n|\Z)',
            research_report,
            re.DOTALL | re.IGNORECASE
        )
        
        if source_list_match:
            source_text = source_list_match.group(1)
            
            # Parse numbered citations (e.g., "1. Author. (Year). Title. Publisher.")
            citation_pattern = r'(\d+)\.\s+(.+?)(?=\n\d+\.|\Z)'
            citations = re.findall(citation_pattern, source_text, re.DOTALL)
            
            for num, citation in citations:
                citation_clean = citation.strip()
                citation_num = int(num)
                seen_citation_numbers.add(citation_num)
                
                # Try to extract title (usually after year in parentheses)
                title_match = re.search(r'\([0-9]{4}\)\.\s+(.+?)\.', citation_clean)
                title = title_match.group(1) if title_match else citation_clean[:100]
                
                # Try to extract URL if present (look for http/https)
                url_match = re.search(r'(https?://[^\s\)]+)', citation_clean)
                url = url_match.group(1) if url_match else f"https://scholar.google.com/scholar?q={title.replace(' ', '+')}"
                
                sources.append({
                    "url": url,
                    "title": title,
                    "content": citation_clean,
                    "snippet": citation_clean[:200],
                    "citation_number": citation_num
                })
        
        # Method 2: Extract numbered citations [1], [2], [3] from report body
        # Find all citation references in the text
        citation_refs = re.findall(r'\[(\d+)\]', research_report)
        citation_numbers = sorted(set(int(ref) for ref in citation_refs))
        
        # For each citation number, extract context and create a source
        for citation_num in citation_numbers:
            if citation_num in seen_citation_numbers:
                continue  # Already extracted from source list
            
            # Find sentences/paragraphs containing this citation
            # Look for patterns like "...text [N]..." or "...[N] text..."
            citation_pattern = rf'\[{citation_num}\](?:[^\[]*?)(?=\[|\n\n|$)'
            matches = re.findall(citation_pattern, research_report, re.DOTALL | re.IGNORECASE)
            
            # Also look for reverse pattern: text before [N]
            reverse_pattern = rf'([^\[\n]{{20,200}})\[{citation_num}\]'
            reverse_matches = re.findall(reverse_pattern, research_report, re.DOTALL | re.IGNORECASE)
            
            # Combine context from both directions
            context_parts = []
            if matches:
                context_parts.extend(matches[:2])  # Take first 2 matches
            if reverse_matches:
                context_parts.extend(reverse_matches[:2])
            
            # Extract key phrases to identify the source
            context_text = " ".join(context_parts[:100]) if context_parts else ""
            
            # Try to identify source type from context
            title = None
            if "Stockton" in context_text or "pilot program" in context_text.lower():
                title = "Stockton Universal Basic Income Pilot Program"
            elif "Roosevelt Institute" in context_text:
                title = "Roosevelt Institute UBI Economic Analysis"
            elif "Pew Research" in context_text or "Pew" in context_text:
                title = "Pew Research Center UBI Public Opinion Survey"
            elif "Bread for the City" in context_text:
                title = "Bread for the City Guaranteed Income Project"
            elif "Alaska" in context_text and "dividend" in context_text.lower():
                title = "Alaska Permanent Fund Dividend Program"
            elif "Gallup" in context_text:
                title = "Gallup Poll on UBI and Automation"
            elif "Georgetown" in context_text or "Widerquist" in context_text:
                title = "Georgetown University UBI Cost Analysis"
            elif "Congressional Budget Office" in context_text or "CBO" in context_text:
                title = "Congressional Budget Office UBI Cost Estimate"
            else:
                # Extract a meaningful title from context
                # Look for capitalized phrases or quoted text
                title_match = re.search(r'["\']([^"\']{10,80})["\']', context_text)
                if title_match:
                    title = title_match.group(1)
                else:
                    # Use first significant phrase
                    words = context_text.split()[:10]
                    title = " ".join(words).strip()[:80]
                    if not title:
                        title = f"Research Source {citation_num}"
            
            # Create searchable URL
            search_query = title.replace(' ', '+') if title else f"universal+basic+income+source+{citation_num}"
            url = f"https://scholar.google.com/scholar?q={search_query}"
            
            # Extract snippet from context
            snippet = context_text[:200] if context_text else f"Source referenced as [{citation_num}] in research report"
            
            sources.append({
                "url": url,
                "title": title or f"Research Source {citation_num}",
                "content": context_text[:500] if context_text else f"Citation [{citation_num}] from research report",
                "snippet": snippet,
                "citation_number": citation_num
            })
        
        # Sort by citation number to maintain order
        sources.sort(key=lambda x: x.get("citation_number", 999))
        
        # Remove citation_number from final output (it was just for sorting)
        for source in sources:
            source.pop("citation_number", None)
        
        # Fallback: If no sources found at all, create one placeholder
        if not sources:
            sources = [{
                "url": "https://scholar.google.com/scholar?q=universal+basic+income",
                "title": "Research compilation on topic",
                "content": research_report[:1000],
                "snippet": research_report[:200]
            }]
        
        return sources
    
    def _update_sources_from_structured_output(
        self,
        citation_data: List[Dict[str, Any]],
        sources: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Update sources list with citation mappings from structured output.
        
        The structured output includes citation_key → source_url mappings,
        which we use to create/update our sources list.
        
        Args:
            citation_data: Citations from structured JSON output
            sources: Current sources list
        
        Returns:
            Updated sources list
        """
        # Build source map from structured output
        structured_sources = []
        for cit in citation_data:
            structured_sources.append({
                "url": cit.get("source_url", ""),
                "title": cit.get("source_title", ""),
                "content": cit.get("relevant_quote", ""),
                "snippet": cit.get("relevant_quote", "")[:200]
            })
        
        # Merge with existing sources (prefer structured data)
        return structured_sources if structured_sources else sources
    
    
    async def _generate_statement(
        self,
        context: AgentContext,
        research_report: str,
        sources: List[Dict[str, Any]],
        statement_type: str
    ) -> Tuple[str, str]:
        """
        Generate statement using Gemini based on Deep Research report.
        
        COLLABORATION POINT 4: System prompt and argumentation strategy
        
        Args:
            context: Debate context
            sources: Researched sources
            statement_type: "opening", "rebuttal", or "closing"
        
        Returns:
            Tuple of (main_statement, supplementary_material)
        """
        system_prompt = self._get_system_prompt(statement_type)
        user_prompt = self._build_user_prompt(context, research_report, sources, statement_type)
        
        # Get JSON schema for structured output
        schema = get_schema("debator", "statement")
        
        response = await self.gemini.generate(
            prompt=user_prompt,
            system_instruction=system_prompt,
            temperature=self.config.gemini_temperature,
            max_tokens=self.config.max_tokens_debator,
            response_format=schema  # Enforce JSON structure
        )
        
        # Parse JSON response (deterministic with schema)
        try:
            from src.utils.json_parser import parse_json_response
            parsed = parse_json_response(response)
            main = parsed.get("main_statement", "")
            supplementary = parsed.get("supplementary_material", "")
            
            # Update sources with citation mappings from structured output
            if "citations" in parsed:
                sources = self._update_sources_from_structured_output(parsed["citations"], sources)
        except json.JSONDecodeError:
            # Fallback to old parsing if JSON fails
            main, supplementary = self._parse_response(response)
        
        return main, supplementary
    
    def _get_system_prompt(self, statement_type: str) -> str:
        """
        Get system prompt for statement generation.
        
        COLLABORATION POINT 5: Core prompt engineering
        
        Goal: Achieve Gemini 3 Pro Deep Research quality + debate mindset
        """
        # TODO: Load from src/prompts/debator_{team}.txt
        # For now, inline version inspired by Deep Research quality
        
        base_prompt = f"""You are {self.name}, an expert debater with deep research capabilities, arguing {self.stance} on the given topic.

Your capabilities (inspired by Gemini Deep Research):
- Synthesize complex information from multiple sources
- Present evidence-based arguments with high-quality citations
- Analyze policy implications and real-world impacts
- Anticipate counterarguments and address them preemptively

Your debate mindset:
- Be persuasive but intellectually rigorous
- Focus on actionable insights and practical implications
- Use data and studies to support every major claim
- Maintain credibility through accurate citations

Citation requirements:
- Format: [a_1], [a_2], etc. for your citations (or [b_1], [b_2] for team b)
- Cite EVERY factual claim, statistic, or study reference
- Use inline citations with context (e.g., "According to the 2024 World Bank report [a_1]...")
- Provide specific, credible sources

"""
        
        if statement_type == "opening":
            base_prompt += """
Opening statement guidelines:
- Establish your main thesis
- Present 2-3 core arguments
- Provide strong evidence for each
- Anticipate counterarguments
"""
        elif statement_type == "rebuttal":
            base_prompt += """
Rebuttal guidelines:
- Address the disagreement frontier identified by the judge
- Challenge opponent's key claims
- Introduce new evidence to shift the debate
- Avoid circular arguments
"""
        elif statement_type == "closing":
            base_prompt += """
Closing statement guidelines:
- Summarize your strongest arguments
- Highlight where opponent failed to address your points
- No new citations allowed - use existing evidence
- Make emotional/ethical appeal if appropriate
"""
        
        return base_prompt
    
    def _build_user_prompt(
        self,
        context: AgentContext,
        research_report: str,
        sources: List[Dict[str, Any]],
        statement_type: str
    ) -> str:
        """
        Build user prompt with research and context.
        
        COLLABORATION POINT 6: How to present research and context?
        """
        prompt = f"""Topic: {context.topic}

Your Position: {self.stance}

RESEARCH FINDINGS:
{research_report}

"""
        
        # Add current debate context
        if context.current_state.get("history_chat", {}).get("public_transcript"):
            prompt += "\n--- DEBATE CONTEXT ---\n"
            prompt += "Previous Statements:\n"
            for turn in context.current_state["history_chat"]["public_transcript"][-3:]:
                speaker_label = "Your previous" if turn['speaker'] == self.team else "Opponent's"
                prompt += f"\n{speaker_label} statement:\n{turn['statement'][:300]}...\n"
            prompt += "\n"
        
        # Add disagreement frontier if available (for rebuttals)
        if statement_type == "rebuttal":
            latent = context.current_state.get("debate_latent", {})
            if latent.get("round_history"):
                latest = latent["round_history"][-1]
                if latest.get("disagreement_frontier"):
                    prompt += "\n--- DISAGREEMENT FRONTIER (PRIORITIZE THESE) ---\n"
                    for issue in latest["disagreement_frontier"]:
                        opponent_team = 'b' if self.team == 'a' else 'a'
                        prompt += f"\nIssue: {issue['core_issue']}\n"
                        prompt += f"  Your stance: {issue.get(f'{self.team}_stance', 'N/A')}\n"
                        prompt += f"  Opponent's stance: {issue.get(f'{opponent_team}_stance', 'N/A')}\n"
                    prompt += "\n"
        
        # Add sources for citation mapping
        if sources:
            prompt += "\n--- AVAILABLE SOURCES FOR CITATIONS ---\n"
            prompt += "IMPORTANT: The research findings above use numbered citations [1], [2], [3], etc.\n"
            prompt += "You MUST map these to the debate citation format below:\n\n"
            
            for i, source in enumerate(sources[:15], 1):  # Max 15 sources
                prompt += f"[Source {i}] → Use as [{self.team}_{i}]\n"
                prompt += f"  Maps from research citation [{i}] in the findings above\n"
                prompt += f"  URL: {source['url']}\n"
                prompt += f"  Title: {source.get('title', 'N/A')}\n"
                if source.get('snippet'):
                    prompt += f"  Context: {source['snippet'][:150]}...\n"
                prompt += "\n"
        
        prompt += f"""--- YOUR TASK ---
Generate your {statement_type} statement for the debate.

CITATION MAPPING (CRITICAL):
- The research findings use numbered citations like [1], [2], [3], [4], [5], [6]
- You MUST map these to debate citations: [1] → [{self.team}_1], [2] → [{self.team}_2], [3] → [{self.team}_3], etc.
- Each different study, survey, or program should get its OWN citation number
- Do NOT use the same citation [{self.team}_1] for multiple different sources
- If research citation [1] refers to "150 pilot programs", use [{self.team}_1] for that
- If research citation [2] refers to "Roosevelt Institute", use [{self.team}_2] for that
- If research citation [3] refers to "Pew Research", use [{self.team}_3] for that
- And so on for each distinct source

Requirements:
1. Use the research findings above to craft compelling arguments
2. Map research citations [1], [2], [3]... to debate citations [{self.team}_1], [{self.team}_2], [{self.team}_3]...
3. Each distinct source/study should have its own citation number
4. Every factual claim must have a citation matching the source it came from
5. Present arguments in a clear, persuasive manner

Generate your {statement_type} statement now.

OUTPUT FORMAT:
Return a JSON object with this structure:
{{
  "main_statement": "Your debate statement with inline citations [a_1], [a_2]...",
  "supplementary_material": "Internal notes for your team",
  "citations": [
    {{
      "citation_key": "a_1",
      "source_url": "https://...",
      "source_title": "Source title",
      "relevant_quote": "Specific data or quote from source"
    }}
  ]
}}"""
        
        return prompt
    
    def _parse_response(self, response: str) -> Tuple[str, str]:
        """
        Parse LLM response into main statement and supplementary material.
        
        COLLABORATION POINT 6: How to structure agent output?
        
        Args:
            response: Raw LLM response
        
        Returns:
            Tuple of (main_statement, supplementary_material)
        """
        # Look for markers like "MAIN STATEMENT:" and "SUPPLEMENTARY:"
        if "SUPPLEMENTARY:" in response:
            parts = response.split("SUPPLEMENTARY:", 1)
            main = parts[0].replace("MAIN STATEMENT:", "").strip()
            supplementary = parts[1].strip()
        else:
            main = response.strip()
            supplementary = ""
        
        return main, supplementary
    
    def _extract_citations(self, text: str) -> List[str]:
        """
        Extract citation keys from text.
        
        Args:
            text: Text containing citations like [a_1], [b_2]
        
        Returns:
            List of citation keys
        """
        pattern = rf'\[{self.team}_\d+\]'
        matches = re.findall(pattern, text)
        # Remove brackets
        citations = [m.strip('[]') for m in matches]
        # Remove duplicates while preserving order
        seen = set()
        unique_citations = []
        for c in citations:
            if c not in seen:
                seen.add(c)
                unique_citations.append(c)
        return unique_citations
    
    async def _register_citations(
        self,
        citation_keys: List[str],
        sources: List[Dict[str, Any]],
        round_number: int,
        turn_id: str
    ) -> List[FileUpdate]:
        """
        Register citations in the citation pool.
        
        COLLABORATION POINT 7: How to map citations to sources?
        
        Args:
            citation_keys: List of citation keys used (e.g., ["a_1", "a_2"])
            sources: List of researched sources
            round_number: Current round number
            turn_id: Turn identifier
        
        Returns:
            List of FileUpdate objects for adding citations
        """
        file_updates = []
        
        for i, citation_key in enumerate(citation_keys):
            # Map citation to source (simple: use order)
            # In production, might use semantic matching
            source = sources[i] if i < len(sources) else sources[-1]
            
            citation_data = {
                "source_url": source["url"],
                "added_by": self.name,
                "added_in_turn": turn_id,
                "added_in_round": round_number,
                "added_at": datetime.now().isoformat(),
                "metadata": {
                    "title": source.get("title", ""),
                    "snippet": source.get("snippet", "")
                }
            }
            
            file_updates.append(FileUpdate(
                file_type="citation_pool",
                operation=FileUpdateOperation.ADD_CITATION,
                data={
                    "team": self.team,
                    "key": citation_key,
                    "citation": citation_data
                }
            ))
        
        return file_updates
