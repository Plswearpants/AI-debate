"""
OpenRouter Client - Unified API gateway for multiple LLM providers.

OpenRouter provides access to 200+ models through a single API key,
including Claude, Gemini, GPT, Llama, and more.

This client can replace:
- GeminiClient (for debators)
- ClaudeClient (for judge)
- PerplexityClient (for fact-checkers)
- LambdaGPUClient (for crowd, if desired)

Author: AI Debate Platform Team
Date: January 2026
"""

import asyncio

import aiohttp
from typing import Optional, Dict, Any, List


class OpenRouterClient:
    """
    Client for OpenRouter API (OpenAI-compatible interface).
    
    OpenRouter provides unified access to multiple LLM providers:
    - Claude 3.5 Sonnet (for judge)
    - Gemini 2.0 Flash (for debators)
    - Perplexity Sonar (for fact-checkers with web search)
    - Llama models (for crowd)
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://openrouter.ai/api/v1",
        app_name: str = "AI-Debate-Platform",
        raw_data_logger=None
    ):
        """
        Initialize OpenRouter client.
        
        Args:
            api_key: OpenRouter API key (starts with sk-or-)
            base_url: API base URL (default: OpenRouter)
            app_name: Your app name (for OpenRouter analytics)
            raw_data_logger: Optional RawDataLogger instance for logging all calls
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        self.app_name = app_name
        self.raw_data_logger = raw_data_logger
        self._current_agent = None  # Set by adapters
        # Keep crowd batch calls stable under transient provider hiccups.
        self.batch_max_concurrency = 6
        self.batch_max_retries = 2
        
        self._last_citations = []
        
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/your-repo",  # Optional
            "X-Title": app_name,
            "Content-Type": "application/json"
        }
    
    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        system_prompt: Optional[str] = None,
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate text using any OpenRouter model.
        
        Args:
            prompt: User prompt
            model: OpenRouter model ID (e.g., "anthropic/claude-3.5-sonnet")
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            system_prompt: Optional system prompt
            response_format: Optional JSON schema for structured output
            
        Returns:
            Generated text
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        # Add response format if specified (for structured output)
        if response_format:
            payload["response_format"] = response_format
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload
            ) as response:
                response.raise_for_status()
                data = await response.json()
                
                result = data["choices"][0]["message"]["content"]
                
                # Capture citation URLs from Perplexity models
                api_citations = data.get("citations", [])
                if api_citations:
                    self._last_citations = api_citations
                
                # Log the call if logger is available
                if self.raw_data_logger and self._current_agent:
                    self.raw_data_logger.log_model_call(
                        agent_name=self._current_agent,
                        model=model,
                        prompt=prompt,
                        response=result,
                        system_prompt=system_prompt,
                        temperature=temperature,
                        max_tokens=max_tokens
                    )
                
                return result
    
    def pop_citations(self) -> List[str]:
        """Retrieve and clear the citation URLs from the last API call.
        Perplexity models return citation URLs as a top-level array."""
        citations = self._last_citations
        self._last_citations = []
        return citations

    async def generate_with_search(
        self,
        prompt: str,
        model: str = "perplexity/llama-3.1-sonar-large-128k-online",
        temperature: float = 0.2,
        max_tokens: int = 1024
    ) -> str:
        """
        Generate text with web search (for fact-checking).
        
        Uses Perplexity models via OpenRouter which have built-in web search.
        
        Args:
            prompt: Search query and context
            model: Perplexity model with web search
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            
        Returns:
            Response with web-grounded information
        """
        return await self.generate(
            prompt=prompt,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens
        )
    
    async def generate_batch(
        self,
        prompts: List[str],
        model: str,
        temperature: float = 0.8,
        max_tokens: int = 100
    ) -> List[str]:
        """
        Generate batch of responses (for crowd voting).
        
        Note: OpenRouter doesn't have native batch API, so we make
        parallel requests. For true batch inference, use Lambda GPU.
        
        Args:
            prompts: List of prompts
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Max tokens per response
            
        Returns:
            List of generated texts
        """
        # Temporarily disable individual logging during batch
        original_agent = self._current_agent
        self._current_agent = None  # Disable logging in generate()

        async def _generate_with_retry(
            prompt: str,
            index: int,
            sem: asyncio.Semaphore
        ) -> str:
            last_error: Optional[Exception] = None
            for attempt in range(self.batch_max_retries + 1):
                try:
                    async with sem:
                        return await self.generate(
                            prompt=prompt,
                            model=model,
                            temperature=temperature,
                            max_tokens=max_tokens
                        )
                except Exception as e:
                    last_error = e
                    if attempt < self.batch_max_retries:
                        await asyncio.sleep(0.5 * (attempt + 1))
                        continue
            raise RuntimeError(
                f"batch item {index} failed after {self.batch_max_retries + 1} attempts: "
                f"{type(last_error).__name__}: {last_error}"
            )

        sem = asyncio.Semaphore(self.batch_max_concurrency)
        tasks = [
            _generate_with_retry(prompt, idx, sem)
            for idx, prompt in enumerate(prompts)
        ]

        try:
            raw_results = await asyncio.gather(*tasks, return_exceptions=True)
            failures = [
                (idx, result) for idx, result in enumerate(raw_results)
                if isinstance(result, Exception)
            ]
            if failures:
                first_idx, first_err = failures[0]
                raise RuntimeError(
                    f"OpenRouter batch failed for {len(failures)}/{len(prompts)} prompts "
                    f"(first failure at index {first_idx}: {first_err})"
                )

            results = [r for r in raw_results if isinstance(r, str)]

            # Restore agent context and log the batch call
            self._current_agent = original_agent
            if self.raw_data_logger and self._current_agent:
                self.raw_data_logger.log_batch_call(
                    agent_name=self._current_agent,
                    model=model,
                    prompts=prompts,
                    responses=results,
                    temperature=temperature,
                    max_tokens=max_tokens
                )

            return results
        finally:
            self._current_agent = original_agent
    
    async def health_check(self) -> Dict[str, str]:
        """
        Check if OpenRouter API is accessible.
        
        Returns:
            Health status dictionary
        """
        try:
            # Try to list models as health check
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.base_url}/models",
                    headers=self.headers
                ) as response:
                    if response.status == 200:
                        return {"status": "ok"}
                    else:
                        return {"status": "error", "message": f"HTTP {response.status}"}
        except Exception as e:
            return {"status": "error", "message": str(e)}
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List available models on OpenRouter.
        
        Returns:
            List of model metadata
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"{self.base_url}/models",
                headers=self.headers
            ) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("data", [])


# Adapter functions for backward compatibility

def create_gemini_adapter(
    openrouter_client: OpenRouterClient,
    model: str,
    factchecker_model: str = "perplexity/llama-3.1-sonar-small-128k-online",
    agent_name: str = "debator"
):
    """
    Create a Gemini-compatible adapter using OpenRouter.
    
    Args:
        openrouter_client: OpenRouter client instance
        model: Gemini model ID (for regular generation)
        factchecker_model: Fact-checker model ID (for web search operations)
        agent_name: Name of the agent using this adapter (for logging)
    """
    
    class GeminiAdapter:
        def __init__(self):
            self.client = openrouter_client
            self.model = model
            self.factchecker_model = factchecker_model  # For web search
            self.agent_name = agent_name
            self.last_research_citations = []  # Real URLs from Perplexity
        
        async def generate(self, prompt, temperature=0.7, max_tokens=4096, system_prompt=None, system_instruction=None, response_format=None):
            """
            Generate text with the model.
            
            Accepts both system_prompt and system_instruction for compatibility.
            system_instruction takes precedence if both are provided.
            """
            # Set agent context for logging
            self.client._current_agent = self.agent_name
            
            # Use system_instruction if provided, otherwise system_prompt
            final_system_prompt = system_instruction if system_instruction is not None else system_prompt
            
            return await self.client.generate(
                prompt=prompt,
                model=self.model,
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=final_system_prompt,
                response_format=response_format
            )
        
        async def generate_with_search(
            self,
            prompt: str,
            system_instruction: Optional[str] = None,
            temperature: float = 0.7,
            max_tokens: int = 2048
        ) -> str:
            """
            Generate with web search (quick search fallback).
            
            Uses Perplexity models via OpenRouter which have built-in web search.
            This is a faster alternative to deep_research() for quick searches.
            
            Args:
                prompt: Search query and context
                system_instruction: Optional system instruction (converted to system prompt)
                temperature: Sampling temperature
                max_tokens: Maximum tokens
                
            Returns:
                Response with web-grounded information
            """
            # Set agent context for logging
            self.client._current_agent = self.agent_name
            
            # Convert system_instruction to system_prompt for OpenRouter
            system_prompt = system_instruction
            
            # Use Perplexity model with web search (from config)
            result = await self.client.generate_with_search(
                prompt=prompt,
                model=self.factchecker_model,
                temperature=temperature,
                max_tokens=max_tokens
            )
            self.last_research_citations = self.client.pop_citations()
            return result
        
        async def deep_research(self, query, background=True, poll_interval=5, max_wait=300):
            """
            Simulate deep research using Perplexity via OpenRouter.
            Citation URLs are captured in self.last_research_citations.
            """
            self.client._current_agent = self.agent_name
            
            research_prompt = f"""You are a research assistant. Conduct comprehensive research on:

{query}

Provide a detailed, well-sourced analysis with specific data points and credible sources.
Include inline citations and a source list at the end."""
            
            result = await self.client.generate_with_search(
                prompt=research_prompt,
                model=self.factchecker_model,
                temperature=0.7,
                max_tokens=4096
            )
            self.last_research_citations = self.client.pop_citations()
            return result
    
    return GeminiAdapter()


def create_claude_adapter(openrouter_client: OpenRouterClient, model: str, agent_name: str = "judge"):
    """Create a Claude-compatible adapter using OpenRouter."""
    
    class ClaudeAdapter:
        def __init__(self):
            self.client = openrouter_client
            self.model = model
            self.agent_name = agent_name
        
        async def generate(self, prompt, temperature=0.3, max_tokens=2048, system_prompt=None, system=None):
            """
            Generate text with the model.
            
            Accepts both system_prompt and system for compatibility.
            system takes precedence if both are provided.
            """
            # Set agent context for logging
            self.client._current_agent = self.agent_name
            
            # Use system if provided, otherwise system_prompt
            final_system_prompt = system if system is not None else system_prompt
            
            return await self.client.generate(
                prompt=prompt,
                model=self.model,
                temperature=temperature,
                max_tokens=max_tokens,
                system_prompt=final_system_prompt
            )
    
    return ClaudeAdapter()


def create_perplexity_adapter(openrouter_client: OpenRouterClient, model: str, agent_name: str = "factchecker"):
    """Create a Perplexity-compatible adapter using OpenRouter."""
    
    class PerplexityAdapter:
        def __init__(self):
            self.client = openrouter_client
            self.model = model
            self.agent_name = agent_name
        
        async def chat(self, query=None, messages=None, temperature=0.2, max_tokens=1024, search_recency_filter=None):
            """
            Chat with the model.
            
            Accepts both query (string) and messages (list) for compatibility.
            If messages is provided, extracts the user message.
            
            Args:
                query: Direct query string (alternative to messages)
                messages: List of message dicts (alternative to query)
                temperature: Sampling temperature
                max_tokens: Maximum tokens to generate
                search_recency_filter: Optional recency filter (ignored for OpenRouter, kept for compatibility)
            """
            # Set agent context for logging
            self.client._current_agent = self.agent_name
            
            # Handle both calling conventions
            if messages is not None:
                # Extract the user message from messages list
                prompt = next((msg["content"] for msg in messages if msg.get("role") == "user"), "")
            else:
                prompt = query or ""
            
            # Note: OpenRouter/Perplexity models don't support search_recency_filter via this API
            # The parameter is accepted for compatibility but ignored
            
            return await self.client.generate_with_search(
                prompt=prompt,
                model=self.model,
                temperature=temperature,
                max_tokens=max_tokens
            )
        
        async def verify_source(self, claim, source_url):
            """Verify a claim against a source using web search."""
            verify_prompt = f"""Verify this claim against the source:

Claim: {claim}
Source: {source_url}

Rate the credibility and correspondence. Provide scores and explanation."""
            
            return await self.chat(query=verify_prompt)
    
    return PerplexityAdapter()


def create_lambda_adapter(openrouter_client: OpenRouterClient, model: str, agent_name: str = "crowd"):
    """Create a Lambda GPU-compatible adapter using OpenRouter."""
    
    class LambdaAdapter:
        def __init__(self):
            self.client = openrouter_client
            self.model = model
            self.agent_name = agent_name
        
        async def generate_single(self, prompt, temperature=0.8, max_tokens=100):
            # Set agent context for logging
            self.client._current_agent = self.agent_name
            return await self.client.generate(
                prompt=prompt,
                model=self.model,
                temperature=temperature,
                max_tokens=max_tokens
            )
        
        async def generate_batch(self, prompts, temperature=0.8, max_tokens=100):
            # Set agent context for logging
            self.client._current_agent = self.agent_name
            return await self.client.generate_batch(
                prompts=prompts,
                model=self.model,
                temperature=temperature,
                max_tokens=max_tokens
            )
        
        async def health_check(self):
            return await self.client.health_check()
    
    return LambdaAdapter()
