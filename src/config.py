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
    
    # API Keys
    gemini_api_key: str
    claude_api_key: str
    perplexity_api_key: str
    lambda_gpu_endpoint: str
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
    max_tokens_crowd: int = 100
    
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
        
        # Required keys
        required_keys = [
            "GEMINI_API_KEY",
            "CLAUDE_API_KEY",
            "PERPLEXITY_API_KEY",
            "LAMBDA_GPU_ENDPOINT"
        ]
        
        missing_keys = [key for key in required_keys if not os.getenv(key)]
        if missing_keys:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_keys)}. "
                f"Please create a .env file based on env.example"
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
            gemini_api_key=os.getenv("GEMINI_API_KEY"),
            claude_api_key=os.getenv("CLAUDE_API_KEY"),
            perplexity_api_key=os.getenv("PERPLEXITY_API_KEY"),
            lambda_gpu_endpoint=os.getenv("LAMBDA_GPU_ENDPOINT"),
            lambda_gpu_api_key=os.getenv("LAMBDA_GPU_API_KEY"),
            num_debate_rounds=int(os.getenv("NUM_DEBATE_ROUNDS", "2")),
            crowd_size=int(os.getenv("CROWD_SIZE", "100")),
            resource_multiplier_threshold=float(os.getenv("RESOURCE_MULTIPLIER_THRESHOLD", "0.6")),
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
