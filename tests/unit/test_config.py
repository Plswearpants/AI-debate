"""
Unit tests for Configuration.

Tests cover:
- Config creation
- Environment variable loading
- Validation
- Test config preset
"""

import pytest
import os
from src.config import Config


class TestConfigCreation:
    """Test configuration creation."""
    
    def test_create_config_directly(self):
        """Test creating config with direct values."""
        config = Config(
            gemini_api_key="test_gemini",
            claude_api_key="test_claude",
            perplexity_api_key="test_perplexity",
            lambda_gpu_endpoint="http://localhost:8000"
        )
        
        assert config.gemini_api_key == "test_gemini"
        assert config.claude_api_key == "test_claude"
        assert config.perplexity_api_key == "test_perplexity"
        assert config.lambda_gpu_endpoint == "http://localhost:8000"
    
    def test_config_defaults(self):
        """Test that config has sensible defaults."""
        config = Config(
            gemini_api_key="test",
            claude_api_key="test",
            perplexity_api_key="test",
            lambda_gpu_endpoint="test"
        )
        
        assert config.num_debate_rounds == 2
        assert config.crowd_size == 100
        assert config.resource_multiplier_threshold == 0.6
        assert config.gemini_model == "gemini-1.5-pro"
        assert config.claude_model == "claude-3-5-sonnet-20241022"
        assert config.perplexity_model == "sonar-pro"
    
    def test_test_config_preset(self):
        """Test that test_config() returns valid test configuration."""
        config = Config.test_config()
        
        assert config.gemini_api_key == "test_gemini_key"
        assert config.num_debate_rounds == 1
        assert config.crowd_size == 10
        assert config.log_level == "DEBUG"


class TestConfigValidation:
    """Test configuration validation."""
    
    def test_validate_valid_config(self):
        """Test that valid config passes validation."""
        config = Config.test_config()
        config.validate()  # Should not raise
    
    def test_validate_invalid_rounds(self):
        """Test that invalid num_debate_rounds raises error."""
        config = Config.test_config()
        config.num_debate_rounds = 0
        
        with pytest.raises(ValueError, match="num_debate_rounds must be at least 1"):
            config.validate()
    
    def test_validate_invalid_crowd_size(self):
        """Test that invalid crowd_size raises error."""
        config = Config.test_config()
        config.crowd_size = -1
        
        with pytest.raises(ValueError, match="crowd_size must be at least 1"):
            config.validate()
    
    def test_validate_invalid_threshold(self):
        """Test that invalid threshold raises error."""
        config = Config.test_config()
        config.resource_multiplier_threshold = 1.5
        
        with pytest.raises(ValueError, match="resource_multiplier_threshold"):
            config.validate()
    
    def test_validate_invalid_temperature(self):
        """Test that invalid temperature raises error."""
        config = Config.test_config()
        config.gemini_temperature = -0.5
        
        with pytest.raises(ValueError, match="gemini_temperature"):
            config.validate()


class TestConfigFromEnv:
    """Test loading config from environment variables."""
    
    def test_from_env_missing_required_keys(self, monkeypatch):
        """Test that missing required keys raises error."""
        # Mock load_dotenv to do nothing (prevent loading from .env file)
        monkeypatch.setattr("src.config.load_dotenv", lambda *args, **kwargs: None)
        
        # Clear all relevant env vars (both OpenRouter and Direct APIs)
        for key in ["OPENROUTER_API_KEY", "GEMINI_API_KEY", "CLAUDE_API_KEY", "PERPLEXITY_API_KEY", "LAMBDA_GPU_ENDPOINT"]:
            monkeypatch.delenv(key, raising=False)
        
        with pytest.raises(ValueError, match="Missing API configuration"):
            Config.from_env()
    
    def test_from_env_with_all_keys(self, monkeypatch):
        """Test loading config when all keys are present."""
        monkeypatch.setenv("GEMINI_API_KEY", "test_gemini")
        monkeypatch.setenv("CLAUDE_API_KEY", "test_claude")
        monkeypatch.setenv("PERPLEXITY_API_KEY", "test_perplexity")
        monkeypatch.setenv("LAMBDA_GPU_ENDPOINT", "http://test:8000")
        monkeypatch.setenv("NUM_DEBATE_ROUNDS", "3")
        monkeypatch.setenv("CROWD_SIZE", "50")
        
        config = Config.from_env()
        
        assert config.gemini_api_key == "test_gemini"
        assert config.claude_api_key == "test_claude"
        assert config.num_debate_rounds == 3
        assert config.crowd_size == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
