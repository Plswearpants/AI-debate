"""
Lambda GPU Client - Wrapper for self-hosted Llama model on Lambda GPU.

Used by: crowd
Purpose: Batch inference for 100 persona voting
"""

import requests
import aiohttp
from typing import List, Dict, Any, Optional


class LambdaGPUClient:
    """Client for Lambda GPU endpoint running Llama."""
    
    def __init__(self, endpoint: str, api_key: Optional[str] = None):
        """
        Initialize Lambda GPU client.
        
        Args:
            endpoint: Lambda GPU endpoint URL
            api_key: API key for authentication (optional)
        """
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.headers = {}
        if api_key:
            self.headers["Authorization"] = f"Bearer {api_key}"
    
    async def generate_batch(
        self,
        prompts: List[str],
        temperature: float = 0.8,
        max_tokens: int = 100
    ) -> List[str]:
        """
        Generate responses for multiple prompts in batch.
        
        Args:
            prompts: List of prompts
            temperature: Sampling temperature
            max_tokens: Maximum output tokens per prompt
        
        Returns:
            List of generated texts (same order as prompts)
        
        Raises:
            Exception: If batch inference fails
        """
        payload = {
            "prompts": prompts,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_p": 0.9
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.endpoint}/v1/batch",
                json=payload,
                headers=self.headers
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Lambda GPU batch inference failed: {error_text}")
                
                result = await response.json()
                return result.get("completions", [])
    
    async def generate_single(
        self,
        prompt: str,
        temperature: float = 0.8,
        max_tokens: int = 100
    ) -> str:
        """
        Generate response for a single prompt.
        
        Args:
            prompt: The prompt
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
        
        Returns:
            Generated text
        """
        responses = await self.generate_batch(
            [prompt],
            temperature=temperature,
            max_tokens=max_tokens
        )
        return responses[0] if responses else ""
    
    def health_check(self) -> bool:
        """
        Check if Lambda GPU endpoint is healthy.
        
        Returns:
            True if endpoint is responding, False otherwise
        """
        try:
            response = requests.get(
                f"{self.endpoint}/health",
                headers=self.headers,
                timeout=5
            )
            return response.status_code == 200
        except Exception:
            return False
