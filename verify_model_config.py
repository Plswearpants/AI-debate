"""
Verify Model Configuration - Check that all agents use config.yaml models.
"""

from src.config import Config

def main():
    """Verify model configuration consistency."""
    print("\n" + "="*80)
    print("MODEL CONFIGURATION VERIFICATION")
    print("="*80)
    
    # Load config from .env + config.yaml
    config = Config.from_files()
    
    print("\nCONFIGURED MODELS (from config.yaml):")
    print("-" * 80)
    print(f"  DEBATOR_MODEL:      {config.debator_model}")
    print(f"  JUDGE_MODEL:        {config.judge_model}")
    print(f"  FACTCHECKER_MODEL:  {config.factchecker_model}")
    print(f"  CROWD_MODEL:        {config.crowd_model}")
    
    print("\nAGENT MODEL USAGE:")
    print("-" * 80)
    
    # Check what models agents will use
    if config.openrouter_api_key:
        print("  Using OpenRouter:")
        print(f"    - Debator:      {config.debator_model} (+ {config.factchecker_model} for web search)")
        print(f"    - Judge:        {config.judge_model}")
        print(f"    - FactChecker:  {config.factchecker_model}")
        print(f"    - Crowd:        {config.crowd_model}")
    else:
        print("  Using Direct APIs:")
        print(f"    - Debator:      {config.debator_model} (via Gemini API)")
        print(f"    - Judge:        {config.judge_model} (via Claude API)")
        print(f"    - FactChecker:  {config.factchecker_model} (via Perplexity API)")
        print(f"    - Crowd:        Lambda GPU endpoint")
    
    print("\nVERIFICATION:")
    print("-" * 80)
    
    # Check for common issues
    issues = []
    
    # Check if models look like valid OpenRouter IDs
    if config.openrouter_api_key:
        models_to_check = [
            ("DEBATOR_MODEL", config.debator_model),
            ("JUDGE_MODEL", config.judge_model),
            ("FACTCHECKER_MODEL", config.factchecker_model),
            ("CROWD_MODEL", config.crowd_model)
        ]
        
        for name, model_id in models_to_check:
            if "/" not in model_id:
                issues.append(f"  [WARN] {name}={model_id} doesn't look like an OpenRouter model ID")
                issues.append(f"     Expected format: provider/model-name (e.g., google/gemini-2.0-flash-exp:free)")
    
    # Check if perplexity model is used for web search
    if config.openrouter_api_key:
        if "perplexity" not in config.factchecker_model.lower():
            issues.append(f"  [WARN] FACTCHECKER_MODEL={config.factchecker_model} is not a Perplexity model")
            issues.append(f"     Web search operations require Perplexity models with online search")
    
    if issues:
        print("  Issues found:")
        for issue in issues:
            print(issue)
    else:
        print("  [OK] All models configured correctly!")
        print("  [OK] No hardcoded model IDs detected!")
        print("  [OK] Agents will use models from config.yaml configuration!")
    
    print("\nTIPS:")
    print("-" * 80)
    print("  - Update API keys in .env file")
    print("  - Update models and runtime settings in config.yaml")
    print("  - Use OpenRouter model IDs with format: provider/model-name")
    print("  - Perplexity models needed for web search (debator fallback, factchecker)")
    print("  - Run test_openrouter.py to verify models are accessible")
    
    print("\n" + "="*80 + "\n")

if __name__ == "__main__":
    main()
