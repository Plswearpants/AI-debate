"""
Test deployment setup before running first debate.

This script tests:
1. Configuration loading
2. All API clients (Gemini, Claude, Perplexity, Lambda GPU)
3. File operations
4. Basic system functionality

Run this before your first debate to ensure everything is set up correctly.
"""

import asyncio
from pathlib import Path
import shutil

from src.config import Config
from src.clients.gemini_client import GeminiClient
from src.clients.claude_client import ClaudeClient
from src.clients.perplexity_client import PerplexityClient
from src.clients.lambda_client import LambdaGPUClient
from src.utils.file_manager import FileManager


def print_section(title: str):
    """Print a section header."""
    print(f"\n{'='*60}")
    print(f"{title}")
    print(f"{'='*60}\n")


async def test_configuration():
    """Test configuration loading and validation."""
    print_section("1. Testing Configuration")
    
    try:
        config = Config.from_env()
        print("✅ Configuration loaded from .env")
        
        config.validate()
        print("✅ Configuration validated")
        
        print(f"\n   API Keys:")
        print(f"   - Gemini: {config.gemini_api_key[:20]}...")
        print(f"   - Claude: {config.claude_api_key[:20]}...")
        print(f"   - Perplexity: {config.perplexity_api_key[:20]}...")
        print(f"\n   Lambda GPU: {config.lambda_gpu_endpoint}")
        print(f"\n   Settings:")
        print(f"   - Debate rounds: {config.num_debate_rounds}")
        print(f"   - Crowd size: {config.crowd_size}")
        print(f"   - Cost preset: {config.cost_budget_preset}")
        
        return config
        
    except Exception as e:
        print(f"❌ Configuration failed: {e}")
        print("\nPlease check:")
        print("  1. .env file exists")
        print("  2. All required API keys are set")
        print("  3. Values are valid")
        return None


async def test_gemini_client(config: Config):
    """Test Gemini API client."""
    print_section("2. Testing Gemini Client")
    
    try:
        client = GeminiClient(config.gemini_api_key)
        
        # Test basic generation
        response = await client.generate(
            "Say 'Hello from Gemini' in one short sentence",
            temperature=0.7
        )
        
        print(f"✅ Gemini API working")
        print(f"   Response: {response[:80]}...")
        
        # Note: We can't easily test Deep Research in a quick test
        # as it takes 2-5 minutes. Just verify basic API works.
        print(f"\n   Note: Deep Research not tested (takes 2-5 min)")
        print(f"   It will be used in actual debate")
        
        return True
        
    except Exception as e:
        print(f"❌ Gemini client failed: {e}")
        print("\nPlease check:")
        print("  1. API key is correct")
        print("  2. You have API quota")
        print("  3. gemini-1.5-pro model is available")
        return False


async def test_claude_client(config: Config):
    """Test Claude API client."""
    print_section("3. Testing Claude Client")
    
    try:
        client = ClaudeClient(config.claude_api_key)
        
        response = await client.generate(
            "Say 'Hello from Claude' in one short sentence",
            temperature=0.3
        )
        
        print(f"✅ Claude API working")
        print(f"   Response: {response[:80]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Claude client failed: {e}")
        print("\nPlease check:")
        print("  1. API key is correct")
        print("  2. You have API quota")
        print("  3. claude-3-5-sonnet model is available")
        return False


async def test_perplexity_client(config: Config):
    """Test Perplexity API client."""
    print_section("4. Testing Perplexity Client")
    
    try:
        client = PerplexityClient(config.perplexity_api_key)
        
        response = await client.chat(
            "What is the capital of France? Answer in one sentence."
        )
        
        print(f"✅ Perplexity API working")
        print(f"   Response: {response[:80]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Perplexity client failed: {e}")
        print("\nPlease check:")
        print("  1. API key is correct")
        print("  2. You have API quota")
        print("  3. sonar-pro model is available")
        return False


async def test_lambda_client(config: Config):
    """Test Lambda GPU client."""
    print_section("5. Testing Lambda GPU Client")
    
    try:
        client = LambdaGPUClient(
            endpoint=config.lambda_gpu_endpoint,
            api_key=config.lambda_gpu_api_key
        )
        
        # Test health check
        health = await client.health_check()
        print(f"✅ Lambda GPU health check passed")
        print(f"   Status: {health}")
        
        # Test single generation
        response = await client.generate_single(
            "Say 'Hello from Llama' in one sentence",
            max_tokens=50
        )
        
        print(f"✅ Lambda GPU generation working")
        print(f"   Response: {response[:80]}...")
        
        # Test batch generation (important for crowd voting)
        prompts = [
            "Rate this from 1-10: Good argument",
            "Rate this from 1-10: Bad argument"
        ]
        responses = await client.generate_batch(prompts, max_tokens=20)
        
        print(f"✅ Lambda GPU batch generation working")
        print(f"   Batch size: {len(responses)}")
        
        return True
        
    except Exception as e:
        print(f"❌ Lambda GPU client failed: {e}")
        print("\nPlease check:")
        print("  1. Lambda GPU server is running")
        print("  2. Endpoint URL is correct")
        print("  3. Server is accessible (firewall, network)")
        print("  4. vLLM server started successfully")
        return False


async def test_file_operations():
    """Test file manager operations."""
    print_section("6. Testing File Operations")
    
    try:
        # Create test directory
        test_dir = Path("debates/deployment-test")
        test_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize file manager
        fm = FileManager(str(test_dir))
        fm.initialize_files("deployment-test", "Test Topic")
        
        print(f"✅ File initialization working")
        
        # Test read
        data = fm.read_for_agent("moderator", "history_chat")
        print(f"✅ File reading working")
        print(f"   Keys: {list(data.keys())}")
        
        # Test citation management
        fm.add_citation("a", "test_cite", {
            "source": "Test Source",
            "content": "Test content",
            "url": "http://test.com"
        })
        
        citations = fm.read_for_agent("moderator", "citation_pool")
        print(f"✅ Citation management working")
        
        # Test permissions
        debator_data = fm.read_for_agent("debator_a", "history_chat")
        judge_data = fm.read_for_agent("judge", "history_chat")
        
        print(f"✅ Permission filtering working")
        print(f"   Debator sees: {list(debator_data.keys())}")
        print(f"   Judge sees: {list(judge_data.keys())}")
        
        # Cleanup
        shutil.rmtree(test_dir)
        print(f"✅ Cleanup successful")
        
        return True
        
    except Exception as e:
        print(f"❌ File operations failed: {e}")
        return False


async def main():
    """Run all deployment tests."""
    print("\n" + "="*60)
    print("🔧 DEPLOYMENT TEST SUITE")
    print("="*60)
    print("\nThis will test all components before your first debate.")
    print("Each test should show ✅ if working correctly.\n")
    
    results = {}
    
    # Test 1: Configuration
    config = await test_configuration()
    results['config'] = config is not None
    
    if not config:
        print("\n❌ Cannot continue without valid configuration")
        return False
    
    # Test 2-5: API Clients
    results['gemini'] = await test_gemini_client(config)
    results['claude'] = await test_claude_client(config)
    results['perplexity'] = await test_perplexity_client(config)
    results['lambda'] = await test_lambda_client(config)
    
    # Test 6: File Operations
    results['files'] = await test_file_operations()
    
    # Summary
    print_section("DEPLOYMENT TEST SUMMARY")
    
    all_passed = all(results.values())
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status:10} - {test_name.capitalize()}")
    
    print()
    
    if all_passed:
        print("="*60)
        print("🎉 ALL TESTS PASSED!")
        print("="*60)
        print("\nYour deployment is ready!")
        print("\nTo run your first debate:")
        print('  python run_debate.py "Your debate topic here"')
        print("\nOr use the default topic:")
        print('  python run_debate.py')
        print("="*60)
    else:
        print("="*60)
        print("⚠️  SOME TESTS FAILED")
        print("="*60)
        print("\nPlease fix the failed components before running a debate.")
        print("See error messages above for details.")
        print("="*60)
    
    return all_passed


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
