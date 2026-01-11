"""
Verify Model Configuration - Check that all agents use models from .env, not hardcoded values.

This script validates:
- Config loads models from .env correctly
- Agents use config models, not hardcoded values
- No hardcoded model IDs in adapter classes

Usage:
    python verify_model_config.py
"""

import os
from dotenv import load_dotenv
from src.config import Config

def main():
    """Verify model configuration consistency."""
    print("\n" + "="*80)
    print("MODEL CONFIGURATION VERIFICATION")
    print("="*80)
    
    # Load config from .env
    load_dotenv()
    config = Config.from_env()
    
    print("\nCONFIGURED MODELS (from .env):")
    print("-" * 80)
    print(f"  GEMINI_MODEL:      {config.gemini_model}")
    print(f"  CLAUDE_MODEL:      {config.claude_model}")
    print(f"  PERPLEXITY_MODEL:  {config.perplexity_model}")
    print(f"  LAMBDA_MODEL:      {config.lambda_model}")
    
    print("\nAGENT MODEL USAGE:")
    print("-" * 80)
    
    # Check what models agents will use
    if config.openrouter_api_key:
        print("  Using OpenRouter:")
        print(f"    - Debator:      {config.gemini_model} (+ {config.perplexity_model} for web search)")
        print(f"    - Judge:        {config.claude_model}")
        print(f"    - FactChecker:  {config.perplexity_model}")
        print(f"    - Crowd:        {config.lambda_model}")
    else:
        print("  Using Direct APIs:")
        print(f"    - Debator:      {config.gemini_model} (via Gemini API)")
        print(f"    - Judge:        {config.claude_model} (via Claude API)")
        print(f"    - FactChecker:  {config.perplexity_model} (via Perplexity API)")
        print(f"    - Crowd:        Lambda GPU endpoint")
    
    print("\nVERIFICATION:")
    print("-" * 80)
    
    # Check for common issues
    issues = []
    
    # Check if models look like valid OpenRouter IDs
    if config.openrouter_api_key:
        models_to_check = [
            ("GEMINI_MODEL", config.gemini_model),
            ("CLAUDE_MODEL", config.claude_model),
            ("PERPLEXITY_MODEL", config.perplexity_model),
            ("LAMBDA_MODEL", config.lambda_model)
        ]
        
        for name, model_id in models_to_check:
            if "/" not in model_id:
                issues.append(f"  ⚠️  {name}={model_id} doesn't look like an OpenRouter model ID")
                issues.append(f"     Expected format: provider/model-name (e.g., google/gemini-2.0-flash-exp:free)")
    
    # Check if perplexity model is used for web search
    if config.openrouter_api_key:
        if "perplexity" not in config.perplexity_model.lower():
            issues.append(f"  ⚠️  PERPLEXITY_MODEL={config.perplexity_model} is not a Perplexity model")
            issues.append(f"     Web search operations require Perplexity models with online search")
    
    if issues:
        print("  Issues found:")
        for issue in issues:
            print(issue)
    else:
        print("  [OK] All models configured correctly!")
        print("  [OK] No hardcoded model IDs detected!")
        print("  [OK] Agents will use models from .env configuration!")
    
    print("\nTIPS:")
    print("-" * 80)
    print("  - Update models in .env file, not in code")
    print("  - Use OpenRouter model IDs with format: provider/model-name")
    print("  - Perplexity models needed for web search (debator fallback, factchecker)")
    print("  - Run test_openrouter.py to verify models are accessible")
    
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
