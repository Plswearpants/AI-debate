"""
Resume a debate from checkpoint.

Usage:
    python resume_debate.py <debate_id>
"""

import asyncio
import sys
from src.moderator import DebateModerator
from src.config import Config


async def resume_debate(debate_id: str):
    """Resume a debate from checkpoint."""
    print(f"\n{'='*60}")
    print(f"♻️  RESUMING DEBATE")
    print(f"{'='*60}")
    print(f"Debate ID: {debate_id}")
    print(f"{'='*60}\n")
    
    # Load config
    try:
        config = Config.from_env()
        print("✅ Configuration loaded\n")
    except Exception as e:
        print(f"❌ Configuration error: {e}\n")
        return
    
    # Resume from checkpoint
    try:
        moderator = await DebateModerator.resume_from_checkpoint(debate_id, config)
        
        # Continue the debate
        await moderator.run_debate()
        
    except FileNotFoundError as e:
        print(f"❌ {e}")
        print(f"\nMake sure:")
        print(f"  1. Debate ID is correct")
        print(f"  2. Checkpoint file exists at:")
        print(f"     debates/{debate_id}/moderator_checkpoint.json\n")
        
    except Exception as e:
        print(f"❌ Resume failed: {e}\n")
        raise


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("\nUsage: python resume_debate.py <debate_id>")
        print("\nExample:")
        print("  python resume_debate.py abc-123-def-456\n")
        sys.exit(1)
    
    debate_id = sys.argv[1]
    asyncio.run(resume_debate(debate_id))
