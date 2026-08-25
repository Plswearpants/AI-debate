"""
Test OpenRouter setup.

This script verifies that OpenRouter API is working correctly
and tests all models that will be used in debates.
"""

import asyncio
import os
from dotenv import load_dotenv
from src.clients.openrouter_client import OpenRouterClient
from src.config import Config


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}\n")


async def test_openrouter():
    """Test OpenRouter API connection and models."""
    
    print_section("OpenRouter API Test Suite")
    
    # Load environment variables
    load_dotenv()
    api_key = os.getenv("OPENROUTER_API_KEY")
    
    if not api_key:
        print("❌ OPENROUTER_API_KEY not found in .env file")
        print("\nPlease add to .env:")
        print("  OPENROUTER_API_KEY=sk-or-v1-your-key-here")
        return False
    
    print(f"✅ API Key loaded: {api_key[:20]}...")
    
    # Load role-based model configuration from config.yaml
    print_section("Configuration from config.yaml")
    config = Config.from_files()
    debator_model = config.debator_model
    judge_model = config.judge_model
    factchecker_model = config.factchecker_model
    crowd_model = config.crowd_model
    
    print(f"Debator model:      {debator_model}")
    print(f"Judge model:        {judge_model}")
    print(f"Fact-checker model: {factchecker_model}")
    print(f"Crowd model:        {crowd_model}")
    
    # Initialize client
    client = OpenRouterClient(api_key=api_key)
    
    # Test 1: Health Check
    print_section("1. Testing API Connection")
    try:
        health = await client.health_check()
        if health.get("status") == "ok":
            print("✅ OpenRouter API is accessible")
        else:
            print(f"❌ Health check failed: {health}")
            return False
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return False
    
    # Test 2: List Models
    print_section("2. Listing Available Models")
    try:
        models = await client.list_models()
        print(f"✅ Found {len(models)} available models")
        
        # Show a few example models
        print("\nExample models available:")
        for model in models[:5]:
            model_id = model.get("id", "unknown")
            print(f"   - {model_id}")
        print("   - ... and many more")
        
    except Exception as e:
        print(f"⚠️  Could not list models: {e}")
        print("   (This is optional, continuing...)")
    
    # Test 3: Gemini Model (for debators)
    print_section("3. Testing Gemini Model (Debators)")
    print(f"Testing: {debator_model}")
    
    try:
        response = await client.generate(
            prompt="In one sentence, explain what universal basic income is.",
            model=debator_model,
            temperature=0.7,
            max_tokens=100
        )
        print(f"✅ Gemini model working")
        print(f"   Response: {response[:100]}...")
    except Exception as e:
        print(f"❌ Gemini test failed: {e}")
        print(f"\nPossible issues:")
        print(f"   - Model ID incorrect")
        print(f"   - Insufficient credits")
        print(f"   - Model not available in your region")
        return False
    
    # Test 4: Claude Model (for judge)
    print_section("4. Testing Claude Model (Judge)")
    print(f"Testing: {judge_model}")
    
    try:
        response = await client.generate(
            prompt="In one sentence, what makes a good neutral judge?",
            model=judge_model,
            temperature=0.3,
            max_tokens=100
        )
        print(f"✅ Claude model working")
        print(f"   Response: {response[:100]}...")
    except Exception as e:
        print(f"❌ Claude test failed: {e}")
        print("\nTry using a different judge model in config.yaml:")
        print("   models.judge: anthropic/claude-3-haiku")
        return False
    
    # Test 5: Perplexity Model (for fact-checkers)
    print_section("5. Testing Perplexity Model (Fact-Checkers)")
    print(f"Testing: {factchecker_model}")
    
    try:
        response = await client.generate_with_search(
            prompt="What is the current population of the United States? Be specific.",
            model=factchecker_model,
            temperature=0.2,
            max_tokens=100
        )
        print(f"✅ Perplexity model working (with web search)")
        print(f"   Response: {response[:100]}...")
    except Exception as e:
        print(f"❌ Perplexity test failed: {e}")
        print("\nTry using a different fact-checker model in config.yaml:")
        print("   models.factchecker: perplexity/llama-3.1-sonar-small-128k-online")
        return False
    
    # Test 6: Llama Model (for crowd)
    print_section("6. Testing Llama Model (Crowd)")
    print(f"Testing: {crowd_model}")
    
    try:
        # Test single generation
        response = await client.generate(
            prompt="Rate this debate argument from 0-100: 'UBI would reduce poverty.' Your score:",
            model=crowd_model,
            temperature=0.8,
            max_tokens=50
        )
        print(f"✅ Llama model working (single)")
        print(f"   Response: {response[:80]}...")
        
        # Test batch generation (important for crowd voting)
        print("\n   Testing batch generation (for 100 personas)...")
        batch_prompts = [
            "Rate from 0-100: Good argument. Score:",
            "Rate from 0-100: Bad argument. Score:",
            "Rate from 0-100: Neutral argument. Score:"
        ]
        
        responses = await client.generate_batch(
            prompts=batch_prompts,
            model=crowd_model,
            temperature=0.8,
            max_tokens=20
        )
        
        print(f"✅ Batch generation working ({len(responses)} responses)")
        for i, r in enumerate(responses):
            print(f"      Prompt {i+1}: {r[:50]}...")
        
    except Exception as e:
        print(f"❌ Llama test failed: {e}")
        print(f"\nNote: Batch generation through OpenRouter may be slower")
        print(f"      For better performance, consider using Lambda GPU")
        return False
    
    # Test 7: Structured Output (JSON)
    print_section("7. Testing Structured Output")
    try:
        response = await client.generate(
            prompt="Generate a JSON with keys 'argument' and 'score'. Argument about UBI, score 1-10.",
            model=debator_model,
            temperature=0.7,
            max_tokens=100,
            response_format={"type": "json_object"}
        )
        print(f"✅ Structured output working")
        print(f"   Response: {response[:150]}...")
    except Exception as e:
        print(f"⚠️  Structured output test failed: {e}")
        print(f"   (Some models may not support this, continuing...)")
    
    # Summary
    print_section("TEST SUMMARY")
    print("✅ All critical tests passed!")
    print("\nYour OpenRouter setup is ready!")
    print("\nNext steps:")
    print("   1. Review model costs at: https://openrouter.ai/models")
    print("   2. Add credits at: https://openrouter.ai/credits")
    print("   3. Run your first debate:")
    print('      python run_debate.py "Your topic here"')
    print("="*60)
    
    return True


async def test_cost_estimation():
    """Estimate costs for a full debate."""
    print_section("COST ESTIMATION")
    
    print("Estimated costs per debate with OpenRouter:")
    print("\nUsing free tier models:")
    print("   Debators (Gemini Flash Free):     $0.00")
    print("   Judge (Claude Sonnet):            $0.30")
    print("   Fact-checkers (Perplexity):       $0.60")
    print("   Crowd (Llama Free):               $0.00")
    print("   " + "-"*40)
    print("   Total:                            $0.90")
    
    print("\nUsing premium models:")
    print("   Debators (Gemini 1.5 Pro):        $0.50")
    print("   Judge (Claude Sonnet):            $0.30")
    print("   Fact-checkers (Perplexity):       $0.60")
    print("   Crowd (Llama 70B):                $0.20")
    print("   " + "-"*40)
    print("   Total:                            $1.60")
    
    print("\nWith $20 credits:")
    print("   Free tier: ~22 debates")
    print("   Premium:   ~12 debates")


if __name__ == "__main__":
    print("\n🔧 OpenRouter Setup Test")
    print("="*60)
    
    success = asyncio.run(test_openrouter())
    
    if success:
        asyncio.run(test_cost_estimation())
        exit(0)
    else:
        print("\n❌ Setup incomplete - please fix issues above")
        exit(1)
