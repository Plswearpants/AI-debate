"""
Run a complete AI debate.

Usage:
    python run_debate.py "Your debate topic here"
    
Or use default topic:
    python run_debate.py
"""

import asyncio
import sys
from pathlib import Path
from src.moderator import DebateModerator
from src.config import Config


async def run_debate(topic: str):
    """Run a complete debate."""
    print(f"\n{'='*60}")
    print(f"🎭 AI DEBATE PLATFORM")
    print(f"{'='*60}")
    print(f"Topic: {topic}")
    print(f"{'='*60}\n")
    
    # Load config
    try:
        config = Config.from_env()
        config.validate()
        print("✅ Configuration loaded and validated\n")
    except Exception as e:
        print(f"❌ Configuration error: {e}")
        print("\nPlease ensure:")
        print("  1. .env file exists in project root")
        print("  2. All required API keys are set")
        print("  3. Lambda GPU endpoint is correct")
        return
    
    # Create moderator
    moderator = DebateModerator(topic=topic, config=config)
    
    print(f"Debate ID: {moderator.debate_id}")
    print(f"Output directory: debates/{moderator.debate_id}/\n")
    
    # Run the debate!
    try:
        debate_id = await moderator.run_debate()
        
        print(f"\n{'='*60}")
        print(f"✅ DEBATE COMPLETED SUCCESSFULLY!")
        print(f"{'='*60}")
        print(f"Debate ID: {debate_id}")
        print(f"Total Cost: ${moderator.total_cost:.2f}")
        print(f"Total Turns: {moderator.state.turn_count}")
        print(f"\nOutputs generated:")
        print(f"  📄 debates/{debate_id}/outputs/transcript_full.md")
        print(f"  📊 debates/{debate_id}/outputs/citation_ledger.json")
        print(f"  🗺️  debates/{debate_id}/outputs/debate_logic_map.json")
        print(f"  📈 debates/{debate_id}/outputs/voter_sentiment_graph.csv")
        print(f"{'='*60}\n")
        
        return debate_id
        
    except KeyboardInterrupt:
        print(f"\n\n⚠️  Debate interrupted by user")
        print(f"💾 Checkpoint saved at:")
        print(f"   debates/{moderator.debate_id}/moderator_checkpoint.json")
        print(f"\nTo resume:")
        print(f"   python resume_debate.py {moderator.debate_id}\n")
        
    except Exception as e:
        print(f"\n{'='*60}")
        print(f"❌ DEBATE FAILED")
        print(f"{'='*60}")
        print(f"Error: {e}")
        print(f"\n💾 Checkpoint may have been saved at:")
        print(f"   debates/{moderator.debate_id}/moderator_checkpoint.json")
        print(f"\nTo resume:")
        print(f"   python resume_debate.py {moderator.debate_id}")
        print(f"{'='*60}\n")
        raise


if __name__ == "__main__":
    # Get topic from command line or use default
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
    else:
        # Default topic
        topic = "Should universal basic income be implemented?"
        print(f"No topic provided, using default:")
        print(f"  \"{topic}\"")
        print(f"\nTo use custom topic: python run_debate.py \"Your topic here\"\n")
    
    asyncio.run(run_debate(topic))
