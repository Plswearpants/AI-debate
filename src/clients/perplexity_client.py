"""
Perplexity Client - Wrapper for Perplexity API.

Used by: factchecker_a, factchecker_b
Purpose: Fact-checking with built-in web search
"""

from openai import OpenAI
from typing import List, Dict, Any, Optional
import time


class PerplexityClient:
    """Client for Perplexity API (uses OpenAI-compatible interface)."""
    
    def __init__(self, api_key: str, model: str = "sonar-pro"):
        """
        Initialize Perplexity client.
        
        Args:
            api_key: Perplexity API key
            model: Model name (default: sonar-pro)
        """
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.perplexity.ai"
        )
        self.model = model
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.2,
        max_tokens: int = 1024,
        search_recency_filter: Optional[str] = "month",
        max_retries: int = 3
    ) -> str:
        """
        Chat with Perplexity (includes web search).
        
        Args:
            messages: List of messages [{"role": "user", "content": "..."}, ...]
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum output tokens
            search_recency_filter: Recency filter ("month", "week", "day", or None)
            max_retries: Number of retries on failure
        
        Returns:
            Generated text with citations
        
        Raises:
            Exception: If generation fails after all retries
        """
        for attempt in range(max_retries):
            try:
                # Note: search_recency_filter might not be supported by all OpenAI-compatible APIs
                create_params = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens
                }
                
                # Add search_recency_filter if provided (Perplexity-specific)
                if search_recency_filter:
                    create_params["search_recency_filter"] = search_recency_filter
                
                response = self.client.chat.completions.create(**create_params)
                
                return response.choices[0].message.content
            
            except Exception as e:
                if attempt < max_retries - 1:
                    # Exponential backoff
                    wait_time = (2 ** attempt) * 1
                    time.sleep(wait_time)
                    continue
                else:
                    raise Exception(f"Perplexity API call failed after {max_retries} attempts: {e}")
    
    async def verify_source(
        self,
        source_url: str,
        claim: str,
        temperature: float = 0.2
    ) -> Dict[str, Any]:
        """
        Verify a source and claim using Perplexity.
        
        Args:
            source_url: URL of the source
            claim: Claim to verify
            temperature: Sampling temperature
        
        Returns:
            Dictionary with verification results
        """
        prompt = f"""
Verify the following claim against the source:

Source URL: {source_url}
Claim: {claim}

Evaluate two aspects:
1. Source Credibility (1-10): Rate the reliability of the source
2. Content Correspondence (1-10): How well the source supports the claim

Respond in JSON format:
{{
  "credibility_score": <1-10>,
  "correspondence_score": <1-10>,
  "comment": "<brief explanation>"
}}
"""
        
        response = await self.chat(
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=500
        )
        
        # Parse JSON response (will implement proper parsing in agent)
        return {"raw_response": response}
