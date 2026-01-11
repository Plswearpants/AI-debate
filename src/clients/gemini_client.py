"""
Gemini Client - Wrapper for Google Gemini API (Interactions API).

Used by: debator_a, debator_b
Purpose: Generate arguments with Deep Research agent
API: New google-genai Interactions API (https://ai.google.dev/gemini-api/docs/interactions)
"""

from google import genai
from google.genai import types
from typing import List, Dict, Any, Optional
import time


class GeminiClient:
    """Client for Google Gemini API using Interactions API."""
    
    def __init__(self, api_key: str, model: str = "gemini-2.5-flash"):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Google AI API key
            model: Model name (default: gemini-2.5-flash for fast responses)
        """
        self.client = genai.Client(api_key=api_key)
        self.model_name = model
    
    async def generate(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        max_retries: int = 3,
        tools: Optional[List[Dict[str, Any]]] = None,
        response_format: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate text using Gemini with Interactions API.
        
        Args:
            prompt: The user prompt
            system_instruction: System instruction (optional)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum output tokens
            max_retries: Number of retries on failure
            tools: List of tools to use (e.g., [{"type": "google_search"}])
            response_format: JSON schema for structured output (optional)
        
        Returns:
            Generated text (JSON string if response_format provided)
        
        Raises:
            Exception: If generation fails after all retries
        """
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens,
            "thinking_level": "medium"  # Balanced thinking
        }
        
        for attempt in range(max_retries):
            try:
                create_params = {
                    "model": self.model_name,
                    "input": prompt,
                    "generation_config": generation_config,
                    "system_instruction": system_instruction,
                }
                
                if tools:
                    create_params["tools"] = tools
                
                if response_format:
                    create_params["response_format"] = response_format
                
                interaction = self.client.interactions.create(**create_params)
                
                # Extract text from outputs (skip tool outputs)
                text_output = next((o for o in interaction.outputs if o.type == "text"), None)
                if text_output:
                    return text_output.text
                else:
                    return ""
            
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = (2 ** attempt) * 1
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"Gemini API call failed after {max_retries} attempts: {e}")
    
    async def deep_research(
        self,
        query: str,
        background: bool = True,
        poll_interval: int = 5,
        max_wait: int = 300
    ) -> str:
        """
        Use Gemini Deep Research agent for thorough research.
        
        This is the KEY method for debator research - uses Google's built-in
        Deep Research agent which performs comprehensive web research.
        
        Args:
            query: Research query/topic
            background: Run in background (default: True)
            poll_interval: Seconds between status checks
            max_wait: Maximum seconds to wait (default: 5 minutes)
        
        Returns:
            Research report text
        
        Raises:
            Exception: If research fails or times out
        """
        # Start Deep Research agent
        interaction = self.client.interactions.create(
            agent="deep-research-pro-preview-12-2025",
            input=query,
            background=background
        )
        
        print(f"Deep Research started. Interaction ID: {interaction.id}")
        
        if not background:
            # Return immediately if not running in background
            text_output = next((o for o in interaction.outputs if o.type == "text"), None)
            return text_output.text if text_output else ""
        
        # Poll for completion (background mode)
        elapsed = 0
        while elapsed < max_wait:
            interaction = self.client.interactions.get(interaction.id)
            status = interaction.status
            
            print(f"Research status: {status} (elapsed: {elapsed}s)")
            
            if status == "completed":
                # Extract final report
                text_output = next((o for o in interaction.outputs if o.type == "text"), None)
                if text_output:
                    return text_output.text
                else:
                    raise Exception("Deep Research completed but no text output found")
            
            elif status in ["failed", "cancelled"]:
                raise Exception(f"Deep Research {status}")
            
            # Wait before polling again
            time.sleep(poll_interval)
            elapsed += poll_interval
        
        raise Exception(f"Deep Research timed out after {max_wait} seconds")
    
    async def generate_with_search(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """
        Generate with Google Search grounding (faster than Deep Research).
        
        Args:
            prompt: The prompt
            system_instruction: System instruction
            temperature: Temperature
            max_tokens: Max tokens
        
        Returns:
            Generated text with search grounding
        """
        return await self.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=[{"type": "google_search"}]
        )
    
    async def generate_with_url_context(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """
        Generate with URL context (reads URLs mentioned in prompt).
        
        Args:
            prompt: The prompt (can include URLs)
            system_instruction: System instruction
            temperature: Temperature
            max_tokens: Max tokens
        
        Returns:
            Generated text with URL context
        """
        return await self.generate(
            prompt=prompt,
            system_instruction=system_instruction,
            temperature=temperature,
            max_tokens=max_tokens,
            tools=[{"type": "url_context"}]
        )
    
    async def generate_with_context(
        self,
        messages: List[Dict[str, str]],
        system_instruction: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ) -> str:
        """
        Generate with multi-turn conversation context (stateless).
        
        Args:
            messages: List of messages [{"role": "user", "content": "..."}, ...]
            system_instruction: System instruction
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
        
        Returns:
            Generated text
        """
        # Convert messages to Interactions API format
        input_content = []
        for msg in messages:
            input_content.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        generation_config = {
            "temperature": temperature,
            "max_output_tokens": max_tokens
        }
        
        interaction = self.client.interactions.create(
            model=self.model_name,
            input=input_content,
            generation_config=generation_config,
            system_instruction=system_instruction
        )
        
        # Extract text output
        text_output = next((o for o in interaction.outputs if o.type == "text"), None)
        return text_output.text if text_output else ""
