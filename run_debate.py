"""
Run a complete AI debate.

Usage:
    python run_debate.py "Your debate topic here"
    python run_debate.py "Your debate topic here" --predict-cost
    
Or use default topic:
    python run_debate.py
"""

import asyncio
import sys
from src.moderator import DebateModerator
from src.config import Config


def predict_debate_cost(config: Config) -> dict:
    """
    Rough cost estimate based on configured budget caps.
    Kept intentionally conservative and optional.
    """
    opening_base = 0.30
    # If unified config uses explicit budget values, this still remains rough.
    if config.cost_budget:
        # Two opening research calls (team a + team b)
        opening_base += min(config.cost_budget.max_cost_per_research * 2, config.cost_budget.max_cost_per_debate)

    per_rebuttal = max(0.20, opening_base * 0.8)
    total_est = opening_base + (per_rebuttal * max(config.num_debate_rounds, 0)) + 0.20

    budget_cap = config.cost_budget.max_cost_per_debate if config.cost_budget else None
    expected = min(total_est, budget_cap) if budget_cap is not None else total_est

    return {
        "opening_estimate": round(opening_base, 2),
        "rebuttal_per_round_estimate": round(per_rebuttal, 2),
        "num_rounds": config.num_debate_rounds,
        "total_estimate": round(total_est, 2),
        "budget_cap": round(budget_cap, 2) if budget_cap is not None else None,
        "expected_capped_total": round(expected, 2),
        "warning": "Rough estimate only; actual cost may vary significantly."
    }


async def run_debate(topic: str, predict_cost: bool = False):
    """Run a complete debate."""
    print(f"\n{'='*60}")
    print("AI DEBATE PLATFORM")
    print(f"{'='*60}")
    print(f"Topic: {topic}")
    print(f"{'='*60}\n")
    
    # Load config
    try:
        config = Config.from_files()
        config.validate()
        print("[OK] Configuration loaded and validated (.env + config.yaml)\n")
    except Exception as e:
        print(f"[ERROR] Configuration error: {e}")
        print("\nPlease ensure:")
        print("  1. .env file exists in project root")
        print("  2. config.yaml exists in project root")
        print("  3. API keys are set in .env")
        return

    if predict_cost:
        est = predict_debate_cost(config)
        print(f"{'='*60}")
        print("COST PREVIEW (OPTIONAL)")
        print(f"{'='*60}")
        print(f"Opening estimate:        ${est['opening_estimate']:.2f}")
        print(f"Rebuttal per round est:  ${est['rebuttal_per_round_estimate']:.2f}")
        print(f"Configured rounds:       {est['num_rounds']}")
        print(f"Total rough estimate:    ${est['total_estimate']:.2f}")
        if est["budget_cap"] is not None:
            print(f"Budget cap:              ${est['budget_cap']:.2f}")
            print(f"Expected capped total:   ${est['expected_capped_total']:.2f}")
        print(f"WARNING: {est['warning']}")
        print(f"{'='*60}\n")

        proceed = input("Proceed with debate? [y/N]: ").strip().lower()
        if proceed not in ("y", "yes"):
            print("Debate cancelled.")
            return
    
    # Create moderator
    moderator = DebateModerator(topic=topic, config=config)
    
    print(f"Debate ID: {moderator.debate_id}")
    print(f"Output directory: debates/{moderator.debate_id}/\n")
    
    # Run the debate!
    try:
        debate_id = await moderator.run_debate()
        
        print(f"\n{'='*60}")
        print("DEBATE COMPLETED SUCCESSFULLY!")
        print(f"{'='*60}")
        print(f"Debate ID: {debate_id}")
        print(f"Total Cost: ${moderator.total_cost:.2f}")
        print(f"Total Turns: {moderator.state.turn_count}")
        print(f"\nOutputs generated:")
        print(f"  - debates/{debate_id}/outputs/transcript_full.md")
        print(f"  - debates/{debate_id}/outputs/citation_ledger.json")
        print(f"  - debates/{debate_id}/outputs/debate_logic_map.json")
        print(f"  - debates/{debate_id}/outputs/voter_sentiment_graph.csv")
        print(f"{'='*60}\n")
        
        return debate_id
        
    except KeyboardInterrupt:
        print("\n\n[WARN] Debate interrupted by user")
        print("Checkpoint saved at:")
        print(f"   debates/{moderator.debate_id}/moderator_checkpoint.json")
        print(f"\nTo resume:")
        print(f"   python resume_debate.py {moderator.debate_id}\n")
        
    except Exception as e:
        print(f"\n{'='*60}")
        print("DEBATE FAILED")
        print(f"{'='*60}")
        print(f"Error: {e}")
        print("\nCheckpoint may have been saved at:")
        print(f"   debates/{moderator.debate_id}/moderator_checkpoint.json")
        print(f"\nTo resume:")
        print(f"   python resume_debate.py {moderator.debate_id}")
        print(f"{'='*60}\n")
        raise


if __name__ == "__main__":
    predict_flag = "--predict-cost" in sys.argv
    args = [a for a in sys.argv[1:] if a != "--predict-cost"]

    # Get topic from command line or use default
    if len(args) > 0:
        topic = " ".join(args)
    else:
        # Default topic
        topic = "Should universal basic income be implemented?"
        print(f"No topic provided, using default:")
        print(f"  \"{topic}\"")
        print(f"\nTo use custom topic: python run_debate.py \"Your topic here\"")
        print(f"To preview cost first: python run_debate.py \"Your topic here\" --predict-cost\n")
    
    asyncio.run(run_debate(topic, predict_cost=predict_flag))
