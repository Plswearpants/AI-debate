"""
View Raw Model Calls - Display logged LLM input/output data.

This script reads and displays raw_model_calls.jsonl files with full prompts and responses.

Usage:
    python view_raw_calls.py <debate_id>          # View all calls
    python view_raw_calls.py <debate_id> --agent debator_a   # Filter by agent
    python view_raw_calls.py <debate_id> --model gemini      # Filter by model
    python view_raw_calls.py last                  # View most recent debate
"""

import argparse
import json
import os
from pathlib import Path
from datetime import datetime


def find_most_recent_debate():
    """
    Find the most recent debate by checking debate directories.
    
    Returns:
        str: Most recent debate ID, or None if no debates found
    """
    debates_dir = Path("debates")
    if not debates_dir.exists():
        return None
    
    # Get all debate directories with raw_model_calls.jsonl
    debate_dirs = [
        d for d in debates_dir.iterdir() 
        if d.is_dir() and (d / "raw_model_calls.jsonl").exists()
    ]
    
    if not debate_dirs:
        return None
    
    # Sort by modification time of raw_model_calls.jsonl
    most_recent = max(
        debate_dirs,
        key=lambda d: (d / "raw_model_calls.jsonl").stat().st_mtime
    )
    
    return most_recent.name


def load_calls(debate_id):
    """
    Load raw model calls from debate log file.
    
    Args:
        debate_id: Debate identifier
        
    Returns:
        list: List of call entries
    """
    log_file = Path(f"debates/{debate_id}/raw_model_calls.jsonl")
    
    if not log_file.exists():
        return []
    
    entries = []
    with open(log_file, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    return entries


def format_timestamp(iso_timestamp):
    """Format ISO timestamp for display."""
    try:
        dt = datetime.fromisoformat(iso_timestamp.replace('Z', '+00:00'))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return iso_timestamp


def print_call(entry, index, show_full=True):
    """
    Print a single model call entry.
    
    Args:
        entry: Call entry dictionary
        index: Entry number
        show_full: Whether to show full prompts/responses
    """
    print(f"\n{'='*100}")
    print(f"CALL #{index+1}")
    print(f"{'='*100}")
    
    # Basic info
    print(f"Timestamp:  {format_timestamp(entry['timestamp'])}")
    print(f"Agent:      {entry['agent_name']}")
    print(f"Model:      {entry['model']}")
    print(f"Parameters: temp={entry['parameters']['temperature']}, max_tokens={entry['parameters']['max_tokens']}")
    
    # Check if batch call
    if entry.get('call_type') == 'batch':
        print(f"\nBATCH CALL: {entry['input']['batch_size']} prompts")
        print(f"Average response length: {entry['output']['avg_length_chars']:.0f} chars")
        
        if show_full:
            print(f"\n{'-'*100}")
            print("PROMPTS:")
            for i, prompt in enumerate(entry['input']['prompts'], 1):
                print(f"\n[Prompt {i}]")
                print(prompt[:500] + "..." if len(prompt) > 500 else prompt)
            
            print(f"\n{'-'*100}")
            print("RESPONSES:")
            for i, response in enumerate(entry['output']['responses'], 1):
                print(f"\n[Response {i}]")
                print(response[:500] + "..." if len(response) > 500 else response)
    else:
        # Single call
        print(f"Response:   {entry['output']['length_chars']} chars, {entry['output']['length_lines']} lines")
        
        if show_full:
            # System prompt
            if entry['input'].get('system_prompt'):
                print(f"\n{'-'*100}")
                print("SYSTEM PROMPT:")
                print(entry['input']['system_prompt'][:1000] + "..." if len(entry['input']['system_prompt']) > 1000 else entry['input']['system_prompt'])
            
            # User prompt
            print(f"\n{'-'*100}")
            print("USER PROMPT:")
            print(entry['input']['user_prompt'][:2000] + "..." if len(entry['input']['user_prompt']) > 2000 else entry['input']['user_prompt'])
            
            # Response
            print(f"\n{'-'*100}")
            print("RESPONSE:")
            print(entry['output']['response'][:2000] + "..." if len(entry['output']['response']) > 2000 else entry['output']['response'])


def view_calls(debate_id, agent_filter=None, model_filter=None, show_summary=True):
    """
    View raw model calls for a debate.
    
    Args:
        debate_id: Debate identifier
        agent_filter: Optional agent name to filter by
        model_filter: Optional model name to filter by
        show_summary: Whether to show summary statistics
    """
    entries = load_calls(debate_id)
    
    if not entries:
        print(f"No raw model calls found for debate: {debate_id}")
        print(f"Expected file: debates/{debate_id}/raw_model_calls.jsonl")
        return
    
    # Apply filters
    if agent_filter:
        entries = [e for e in entries if agent_filter.lower() in e['agent_name'].lower()]
    if model_filter:
        entries = [e for e in entries if model_filter.lower() in e['model'].lower()]
    
    # Show summary
    if show_summary:
        print(f"\n{'='*100}")
        print(f"RAW MODEL CALLS - Debate {debate_id}")
        print(f"{'='*100}")
        print(f"Total calls: {len(entries)}")
        
        # Group by agent
        agents = {}
        for entry in entries:
            agent = entry['agent_name']
            agents[agent] = agents.get(agent, 0) + 1
        
        print("\nCalls by agent:")
        for agent, count in sorted(agents.items()):
            print(f"  - {agent}: {count}")
        
        # Group by model
        models = {}
        for entry in entries:
            model = entry['model']
            models[model] = models.get(model, 0) + 1
        
        print("\nCalls by model:")
        for model, count in sorted(models.items()):
            print(f"  - {model}: {count}")
    
    # Show entries
    for i, entry in enumerate(entries):
        print_call(entry, i, show_full=True)
    
    print(f"\n{'='*100}\n")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="View raw model call data from debates")
    parser.add_argument("debate_id", help="Debate ID to view (or 'last' for most recent)")
    parser.add_argument("--agent", help="Filter by agent name")
    parser.add_argument("--model", help="Filter by model")
    parser.add_argument("--no-summary", action="store_true", help="Don't show summary")
    
    args = parser.parse_args()
    
    # Handle "last" special case
    debate_id = args.debate_id
    if debate_id.lower() == "last":
        debate_id = find_most_recent_debate()
        if not debate_id:
            print("No debates found with raw_model_calls.jsonl")
            return
        print(f"Viewing most recent debate: {debate_id}\n")
    
    view_calls(
        debate_id,
        agent_filter=args.agent,
        model_filter=args.model,
        show_summary=not args.no_summary
    )


if __name__ == "__main__":
    main()
