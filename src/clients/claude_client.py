"""
Claude Client - Wrapper for Anthropic Claude API.

Used by: judge
Purpose: Neutral analysis and frontier identification
"""

from anthropic import Anthropic
from typing import List, Dict, Any, Optional
import time


class ClaudeClient:
    """Client for Anthropic Claude API."""
    
    def __init__(self, api_key: str, model: str = "claude-3-5-sonnet-20241022"):
        """
        Initialize Claude client.
        
        Args:
            api_key: Anthropic API key
            model: Model name (default: claude-3-5-sonnet-20241022)
        """
        self.client = Anthropic(api_key=api_key)
        self.model = model
    
    async def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        max_retries: int = 3
    ) -> str:
        """
        Generate text using Claude.
        
        Args:
            prompt: The user prompt
            system: System prompt (optional)
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum output tokens
            max_retries: Number of retries on failure
        
        Returns:
            Generated text
        
        Raises:
            Exception: If generation fails after all retries
        """
        for attempt in range(max_retries):
            try:
                message_params = {
                    "model": self.model,
                    "max_tokens": max_tokens,
                    "temperature": temperature,
                    "messages": [
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ]
                }
                
                if system:
                    message_params["system"] = system
                
                response = self.client.messages.create(**message_params)
                
                return response.content[0].text
            
            except Exception as e:
                if attempt < max_retries - 1:
                    # Exponential backoff
                    wait_time = (2 ** attempt) * 1
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"Claude API call failed after {max_retries} attempts: {e}")
    
    async def generate_with_context(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4096
    ) -> str:
        """
        Generate with multi-turn conversation context.
        
        Args:
            messages: List of messages [{"role": "user", "content": "..."}, {"role": "assistant", ...}]
            system: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
        
        Returns:
            Generated text
        """
        message_params = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }
        
        if system:
            message_params["system"] = system
        
        response = self.client.messages.create(**message_params)
        
        return response.content[0].text
