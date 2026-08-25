"""
Configuration Management - Loads secrets from .env and parameters from config.yaml.
"""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

import yaml
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
    
    # Model Settings (role-based)
    debator_model: str = "gemini-1.5-pro"
    judge_model: str = "claude-3-5-sonnet-20241022"
    factchecker_model: str = "sonar-pro"
    crowd_model: str = "meta-llama/Llama-3.1-8B-Instruct"
    
    # Generation Settings (role-based)
    debator_temperature: float = 0.7
    judge_temperature: float = 0.3
    factchecker_temperature: float = 0.2
    crowd_temperature: float = 0.8
    crowd_context_mode: str = "full_transcript"
    
    max_tokens_debator: int = 4096
    max_tokens_judge: int = 2048
    max_tokens_factchecker: int = 1024
    max_tokens_crowd: int = 100
    max_tokens_crowd_journal: int = 240
    
    # Logging
    log_level: str = "INFO"
    
    # Cost Controls
    cost_budget: Optional[CostBudget] = None

    @classmethod
    def from_files(
        cls,
        env_path: Optional[str] = None,
        config_path: Optional[str] = None
    ) -> "Config":
        """
        Load secrets from .env and non-secret parameters from config.yaml.
        """
        # Load secrets
        load_dotenv(env_path) if env_path else load_dotenv()

        # Resolve and load unified config file
        cfg_path = Path(config_path) if config_path else Path("config.yaml")
        if not cfg_path.exists():
            raise FileNotFoundError(
                f"Missing unified config file: {cfg_path}\n"
                "Create it from template, e.g. copy config.balanced.yaml config.yaml"
            )

        with open(cfg_path, "r", encoding="utf-8") as f:
            raw_cfg = yaml.safe_load(f) or {}

        # Accept both nested and legacy-flat layouts for smoother migration.
        debate_cfg = raw_cfg.get("debate", {})
        models_cfg = raw_cfg.get("models", {})
        gen_cfg = raw_cfg.get("generation", {})
        temp_cfg = gen_cfg.get("temperature", {})
        token_cfg = gen_cfg.get("max_tokens", {})
        research_cfg = raw_cfg.get("research", {})
        budget_cfg = raw_cfg.get("budget", {})
        logging_cfg = raw_cfg.get("logging", {})

        # Secrets from .env only
        openrouter_key = os.getenv("OPENROUTER_API_KEY")
        gemini_key = os.getenv("GEMINI_API_KEY")
        claude_key = os.getenv("CLAUDE_API_KEY")
        perplexity_key = os.getenv("PERPLEXITY_API_KEY")
        lambda_endpoint = os.getenv("LAMBDA_GPU_ENDPOINT")
        lambda_api_key = os.getenv("LAMBDA_GPU_API_KEY")

        # Validate: Must have either OpenRouter OR all direct APIs
        has_openrouter = bool(openrouter_key)
        has_direct_apis = all([gemini_key, claude_key, perplexity_key])

        if not has_openrouter and not has_direct_apis:
            raise ValueError(
                "Missing API configuration. Please set either:\n"
                "  - OPENROUTER_API_KEY in .env, or\n"
                "  - GEMINI_API_KEY + CLAUDE_API_KEY + PERPLEXITY_API_KEY in .env"
            )

        # Build explicit budget (no preset middle layer)
        cost_budget = CostBudget(
            max_cost_per_research=float(
                research_cfg.get("max_cost_per_research", 2.0)
            ),
            max_grounding_queries=int(
                research_cfg.get("max_grounding_queries", 20)
            ),
            max_context_tokens=int(
                research_cfg.get("max_context_tokens", 180000)
            ),
            max_output_tokens=int(
                research_cfg.get("max_output_tokens", 15000)
            ),
            max_research_time=int(
                research_cfg.get("max_research_time", 300)
            ),
            max_cost_per_debate=float(
                budget_cfg.get("max_cost_per_debate", 5.0)
            ),
            max_deep_research_calls=int(
                budget_cfg.get("max_deep_research_calls", 4)
            ),
            use_quick_search_threshold=float(
                research_cfg.get("quick_search_threshold", 1.0)
            ),
        )

        return cls(
            # Secrets
            openrouter_api_key=openrouter_key,
            gemini_api_key=gemini_key,
            claude_api_key=claude_key,
            perplexity_api_key=perplexity_key,
            lambda_gpu_endpoint=lambda_endpoint,
            lambda_gpu_api_key=lambda_api_key,

            # Unified parameter file
            use_openrouter_for_crowd=bool(
                models_cfg.get("use_openrouter_for_crowd", True)
            ),
            num_debate_rounds=int(
                debate_cfg.get("num_rounds", raw_cfg.get("num_debate_rounds", 2))
            ),
            crowd_size=int(
                debate_cfg.get("crowd_size", raw_cfg.get("crowd_size", 100))
            ),
            resource_multiplier_threshold=float(
                debate_cfg.get(
                    "resource_multiplier_threshold",
                    raw_cfg.get("resource_multiplier_threshold", 0.6),
                )
            ),
            debator_model=str(models_cfg.get("debator", "gemini-1.5-pro")),
            judge_model=str(models_cfg.get("judge", "claude-3-5-sonnet-20241022")),
            factchecker_model=str(models_cfg.get("factchecker", "sonar-pro")),
            crowd_model=str(models_cfg.get("crowd", "meta-llama/Llama-3.1-8B-Instruct")),
            debator_temperature=float(temp_cfg.get("debator", 0.7)),
            judge_temperature=float(temp_cfg.get("judge", 0.3)),
            factchecker_temperature=float(temp_cfg.get("factchecker", 0.2)),
            crowd_temperature=float(
                temp_cfg.get("crowd", raw_cfg.get("crowd_temperature", 0.8))
            ),
            crowd_context_mode=str(
                gen_cfg.get("crowd_context_mode", raw_cfg.get("crowd_context_mode", "full_transcript"))
            ),
            max_tokens_debator=int(
                token_cfg.get("debator", raw_cfg.get("max_tokens_debator", 4096))
            ),
            max_tokens_judge=int(
                token_cfg.get("judge", raw_cfg.get("max_tokens_judge", 2048))
            ),
            max_tokens_factchecker=int(
                token_cfg.get(
                    "factchecker", raw_cfg.get("max_tokens_factchecker", 1024)
                )
            ),
            max_tokens_crowd=int(
                token_cfg.get("crowd", raw_cfg.get("max_tokens_crowd", 100))
            ),
            max_tokens_crowd_journal=int(
                token_cfg.get(
                    "crowd_journal", raw_cfg.get("max_tokens_crowd_journal", 240)
                )
            ),
            log_level=str(logging_cfg.get("level", raw_cfg.get("log_level", "INFO"))),
            cost_budget=cost_budget,
        )

    @classmethod
    def from_env(cls, env_path: Optional[str] = None) -> "Config":
        """
        Backward-compatible loader name.
        """
        return cls.from_files(env_path=env_path)
    
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
            cost_budget=CostBudget(
                max_cost_per_research=0.50,
                max_grounding_queries=10,
                max_context_tokens=100000,
                max_output_tokens=8000,
                max_research_time=180,
                max_cost_per_debate=2.0,
                max_deep_research_calls=2,
                use_quick_search_threshold=0.5,
            ),
        )
    
    def validate(self) -> None:
        """
        Validate configuration values.
        
        Raises:
            ValueError: If configuration is invalid
        """
        if self.num_debate_rounds < 0:
            raise ValueError("num_debate_rounds must be at least 0")
        
        if self.crowd_size < 1:
            raise ValueError("crowd_size must be at least 1")
        
        if not (0.0 <= self.resource_multiplier_threshold <= 1.0):
            raise ValueError("resource_multiplier_threshold must be between 0.0 and 1.0")
        
        if self.debator_temperature < 0 or self.debator_temperature > 1:
            raise ValueError("debator_temperature must be between 0 and 1")

        if self.judge_temperature < 0 or self.judge_temperature > 1:
            raise ValueError("judge_temperature must be between 0 and 1")

        if self.factchecker_temperature < 0 or self.factchecker_temperature > 1:
            raise ValueError("factchecker_temperature must be between 0 and 1")

        if self.crowd_temperature < 0 or self.crowd_temperature > 1:
            raise ValueError("crowd_temperature must be between 0 and 1")

        valid_crowd_context_modes = {"full_transcript", "latest_plus_latent"}
        if self.crowd_context_mode not in valid_crowd_context_modes:
            raise ValueError(
                "crowd_context_mode must be one of: "
                + ", ".join(sorted(valid_crowd_context_modes))
            )
