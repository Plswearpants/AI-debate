"""
Unit tests for Configuration.

Tests cover:
- Config creation
- File-based loading (.env + config.yaml)
- Validation
- Test config helper
"""

import pytest
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
        assert config.debator_model == "gemini-1.5-pro"
        assert config.judge_model == "claude-3-5-sonnet-20241022"
        assert config.factchecker_model == "sonar-pro"
        assert config.crowd_context_mode == "full_transcript"
    
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
        config.num_debate_rounds = -1
        
        with pytest.raises(ValueError, match="num_debate_rounds must be at least 0"):
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
        config.debator_temperature = -0.5
        
        with pytest.raises(ValueError, match="debator_temperature"):
            config.validate()

    def test_validate_invalid_crowd_context_mode(self):
        """Test that invalid crowd context mode raises error."""
        config = Config.test_config()
        config.crowd_context_mode = "invalid_mode"

        with pytest.raises(ValueError, match="crowd_context_mode"):
            config.validate()


class TestConfigFromEnv:
    """Test loading config from .env + config.yaml."""
    
    def test_from_files_missing_required_keys(self, monkeypatch, tmp_path):
        """Test that missing required API keys raises error."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "debate:\n"
            "  num_rounds: 1\n"
            "  crowd_size: 10\n"
            "  resource_multiplier_threshold: 0.6\n"
            "models:\n"
            "  use_openrouter_for_crowd: true\n"
            "  debator: \"google/gemini-2.5-flash\"\n"
            "  judge: \"anthropic/claude-3.5-sonnet\"\n"
            "  factchecker: \"perplexity/sonar\"\n"
            "  crowd: \"meta-llama/llama-3.3-70b-instruct\"\n"
            "generation:\n"
            "  temperature: { debator: 0.7, judge: 0.3, factchecker: 0.2, crowd: 0.8 }\n"
            "  max_tokens: { debator: 4096, judge: 2048, factchecker: 1024, crowd: 100, crowd_journal: 240 }\n"
            "research:\n"
            "  max_cost_per_research: 2.0\n"
            "  max_grounding_queries: 20\n"
            "  max_context_tokens: 180000\n"
            "  max_output_tokens: 15000\n"
            "  max_research_time: 300\n"
            "  quick_search_threshold: 1.0\n"
            "budget:\n"
            "  max_cost_per_debate: 5.0\n"
            "  max_deep_research_calls: 4\n"
            "logging:\n"
            "  level: \"INFO\"\n",
            encoding="utf-8",
        )

        for key in ["OPENROUTER_API_KEY", "GEMINI_API_KEY", "CLAUDE_API_KEY", "PERPLEXITY_API_KEY", "LAMBDA_GPU_ENDPOINT"]:
            monkeypatch.delenv(key, raising=False)

        env_file = tmp_path / ".env.empty"
        env_file.write_text("", encoding="utf-8")

        with pytest.raises(ValueError, match="Missing API configuration"):
            Config.from_files(env_path=str(env_file), config_path=str(config_file))

    def test_from_files_with_all_keys(self, monkeypatch, tmp_path):
        """Test loading config when keys + config file are present."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            "debate:\n"
            "  num_rounds: 3\n"
            "  crowd_size: 50\n"
            "  resource_multiplier_threshold: 0.6\n"
            "models:\n"
            "  use_openrouter_for_crowd: true\n"
            "  debator: \"google/gemini-2.5-flash\"\n"
            "  judge: \"anthropic/claude-3.5-sonnet\"\n"
            "  factchecker: \"perplexity/sonar\"\n"
            "  crowd: \"meta-llama/llama-3.3-70b-instruct\"\n"
            "generation:\n"
            "  temperature: { debator: 0.7, judge: 0.3, factchecker: 0.2, crowd: 0.8 }\n"
            "  max_tokens: { debator: 4096, judge: 2048, factchecker: 1024, crowd: 100, crowd_journal: 240 }\n"
            "research:\n"
            "  max_cost_per_research: 2.0\n"
            "  max_grounding_queries: 20\n"
            "  max_context_tokens: 180000\n"
            "  max_output_tokens: 15000\n"
            "  max_research_time: 300\n"
            "  quick_search_threshold: 1.0\n"
            "budget:\n"
            "  max_cost_per_debate: 5.0\n"
            "  max_deep_research_calls: 4\n"
            "logging:\n"
            "  level: \"INFO\"\n",
            encoding="utf-8",
        )

        monkeypatch.setenv("GEMINI_API_KEY", "test_gemini")
        monkeypatch.setenv("CLAUDE_API_KEY", "test_claude")
        monkeypatch.setenv("PERPLEXITY_API_KEY", "test_perplexity")
        monkeypatch.setenv("LAMBDA_GPU_ENDPOINT", "http://test:8000")

        env_file = tmp_path / ".env.empty"
        env_file.write_text("", encoding="utf-8")

        config = Config.from_files(env_path=str(env_file), config_path=str(config_file))

        assert config.gemini_api_key == "test_gemini"
        assert config.claude_api_key == "test_claude"
        assert config.num_debate_rounds == 3
        assert config.crowd_size == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
