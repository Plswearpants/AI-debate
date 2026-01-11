"""
Configuration Management - Loads and validates configuration from environment.

This module provides:
- Configuration loading from .env file
- Validation of required settings
- Configuration presets for different environments
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv
from src.utils.cost_controls import CostBudget


@dataclass
class Config:
    """Configuration for the AI Debate Platform."""
    
    # API Keys - OpenRouter (recommended) OR Direct APIs
    openrouter_api_key: Optional[str] = None
    use_openrouter_for_crowd: bool = False
    
    # Direct API Keys (optional if using OpenRouter)
    gemini_api_key: Optional[str] = None
    claude_api_key: Optional[str] = None
    perplexity_api_key: Optional[str] = None
    lambda_gpu_endpoint: Optional[str] = None
    lambda_gpu_api_key: Optional[str] = None
    
    # Debate Settings
    num_debate_rounds: int = 2
    crowd_size: int = 100
    resource_multiplier_threshold: float = 0.6
    
    # Model Settings
    gemini_model: str = "gemini-1.5-pro"
    claude_model: str = "claude-3-5-sonnet-20241022"
    perplexity_model: str = "sonar-pro"
    lambda_model: str = "meta-llama/Llama-3.1-8B-Instruct"
    
    # Generation Settings
    gemini_temperature: float = 0.7
    claude_temperature: float = 0.3
    perplexity_temperature: float = 0.2
    crowd_temperature: float = 0.8
    
    max_tokens_debator: int = 4096
    max_tokens_judge: int = 2048
    max_tokens_factchecker: int = 1024
    max_tokens_crowd: int = 1024
    
    # Logging
    log_level: str = "INFO"
    
    # Cost Controls
    cost_budget: Optional[CostBudget] = None
    cost_budget_preset: str = "balanced"  # "conservative", "balanced", or "premium"
    
    @classmethod
    def from_env(cls, env_path: Optional[str] = None) -> "Config":
        """
        Load configuration from environment variables.
        
        Args:
            env_path: Path to .env file (optional)
        
        Returns:
            Config instance
        
        Raises:
            ValueError: If required environment variables are missing
        """
        if env_path:
            load_dotenv(env_path)
        else:
            load_dotenv()
        
        # Check for OpenRouter OR Direct APIs
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        gemini_key = os.getenv("GEMINI_API_KEY")
        claude_key = os.getenv("CLAUDE_API_KEY")
        perplexity_key = os.getenv("PERPLEXITY_API_KEY")
        lambda_endpoint = os.getenv("LAMBDA_GPU_ENDPOINT")
        
        # Validate: Must have either OpenRouter OR all direct APIs
        has_openrouter = bool(openrouter_key)
        has_direct_apis = all([gemini_key, claude_key, perplexity_key])
        
        if not has_openrouter and not has_direct_apis:
            raise ValueError(
                "Missing API configuration. Please choose ONE option:\n\n"
                "Option A (Recommended): OpenRouter\n"
                "  - Set OPENROUTER_API_KEY in .env\n"
                "  - Get key from: https://openrouter.ai/keys\n\n"
                "Option B (Advanced): Direct APIs\n"
                "  - Set GEMINI_API_KEY, CLAUDE_API_KEY, PERPLEXITY_API_KEY\n"
                "  - Requires multiple provider accounts\n\n"
                "See DEPLOYMENT_GUIDE.md for setup instructions."
            )
        
        # Get cost budget preset
        budget_preset = os.getenv("COST_BUDGET_PRESET", "balanced")
        if budget_preset == "conservative":
            cost_budget = CostBudget.conservative()
        elif budget_preset == "premium":
            cost_budget = CostBudget.premium()
        else:
            cost_budget = CostBudget.balanced()
        
        return cls(
            # OpenRouter or Direct APIs
            openrouter_api_key=openrouter_key,
            use_openrouter_for_crowd=os.getenv("USE_OPENROUTER_FOR_CROWD", "false").lower() == "true",
            gemini_api_key=gemini_key,
            claude_api_key=claude_key,
            perplexity_api_key=perplexity_key,
            lambda_gpu_endpoint=lambda_endpoint,
            lambda_gpu_api_key=os.getenv("LAMBDA_GPU_API_KEY"),
            # Debate settings
            num_debate_rounds=int(os.getenv("NUM_DEBATE_ROUNDS", "2")),
            crowd_size=int(os.getenv("CROWD_SIZE", "100")),
            resource_multiplier_threshold=float(os.getenv("RESOURCE_MULTIPLIER_THRESHOLD", "0.6")),
            # Model settings (work for both OpenRouter and Direct APIs)
            gemini_model=os.getenv("GEMINI_MODEL", "gemini-1.5-pro"),
            claude_model=os.getenv("CLAUDE_MODEL", "claude-3-5-sonnet-20241022"),
            perplexity_model=os.getenv("PERPLEXITY_MODEL", "sonar-pro"),
            lambda_model=os.getenv("LAMBDA_MODEL", "meta-llama/Llama-3.1-8B-Instruct"),
            # Generation settings
            gemini_temperature=float(os.getenv("GEMINI_TEMPERATURE", "0.7")),
            claude_temperature=float(os.getenv("CLAUDE_TEMPERATURE", "0.3")),
            perplexity_temperature=float(os.getenv("PERPLEXITY_TEMPERATURE", "0.2")),
            crowd_temperature=float(os.getenv("CROWD_TEMPERATURE", "0.8")),
            max_tokens_debator=int(os.getenv("MAX_TOKENS_DEBATOR", "4096")),
            max_tokens_judge=int(os.getenv("MAX_TOKENS_JUDGE", "2048")),
            max_tokens_factchecker=int(os.getenv("MAX_TOKENS_FACTCHECKER", "1024")),
            max_tokens_crowd=int(os.getenv("MAX_TOKENS_CROWD", "100")),
            # Other settings
            log_level=os.getenv("LOG_LEVEL", "INFO"),
            cost_budget=cost_budget,
            cost_budget_preset=budget_preset
        )
    
    @classmethod
    def test_config(cls) -> "Config":
        """
        Create a test configuration with mock values.
        
        Returns:
            Config instance for testing
        """
        return cls(
            openrouter_api_key=None,  # Tests use direct APIs
            use_openrouter_for_crowd=False,
            gemini_api_key="test_gemini_key",
            claude_api_key="test_claude_key",
            perplexity_api_key="test_perplexity_key",
            lambda_gpu_endpoint="http://localhost:8000",
            lambda_gpu_api_key="test_lambda_key",
            num_debate_rounds=1,  # Faster tests
            crowd_size=10,        # Smaller crowd for tests
            resource_multiplier_threshold=0.6,
            log_level="DEBUG",
            cost_budget=CostBudget.conservative(),  # Use conservative for tests
            cost_budget_preset="conservative"
        )
    
    def validate(self) -> None:
        """
        Validate configuration values.
        
        Raises:
            ValueError: If configuration is invalid
        """
        if self.num_debate_rounds < 1:
            raise ValueError("num_debate_rounds must be at least 1")
        
        if self.crowd_size < 1:
            raise ValueError("crowd_size must be at least 1")
        
        if not (0.0 <= self.resource_multiplier_threshold <= 1.0):
            raise ValueError("resource_multiplier_threshold must be between 0.0 and 1.0")
        
        if self.gemini_temperature < 0 or self.gemini_temperature > 1:
            raise ValueError("gemini_temperature must be between 0 and 1")
