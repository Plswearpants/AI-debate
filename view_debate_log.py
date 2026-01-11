"""
View Debate Log - Read and display comprehensive debate logs.

Usage:
    python view_debate_log.py <debate_id>
    python view_debate_log.py last
    python view_debate_log.py <debate_id> --filter agent_turn
    python view_debate_log.py <debate_id> --agent debator_a
    python view_debate_log.py <debate_id> --raw
"""

import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


def find_most_recent_debate() -> Optional[str]:
    """
    Find the most recent debate by checking modification times of log files.
    
    Returns:
        Most recent debate ID, or None if no debates found
    """
    debates_dir = Path("debates")
    
    if not debates_dir.exists():
        return None
    
    most_recent_id = None
    most_recent_time = 0
    
    # Check each debate directory
    for debate_dir in debates_dir.iterdir():
        if not debate_dir.is_dir():
            continue
        
        debate_id = debate_dir.name
        
        # Check for log file (most reliable indicator of recent activity)
        log_file = debate_dir / "debate_log.jsonl"
        if log_file.exists():
            mtime = log_file.stat().st_mtime
            if mtime > most_recent_time:
                most_recent_time = mtime
                most_recent_id = debate_id
        else:
            # Fallback: check checkpoint file
            checkpoint_file = debate_dir / "moderator_checkpoint.json"
            if checkpoint_file.exists():
                mtime = checkpoint_file.stat().st_mtime
                if mtime > most_recent_time:
                    most_recent_time = mtime
                    most_recent_id = debate_id
    
    return most_recent_id


def load_logs(debate_id: str) -> List[Dict[str, Any]]:
    """Load all log entries from debate log file."""
    log_file = Path(f"debates/{debate_id}/debate_log.jsonl")
    
    if not log_file.exists():
        print(f"❌ Log file not found: {log_file}")
        print(f"\nMake sure:")
        print(f"  1. Debate ID is correct: {debate_id}")
        print(f"  2. Debate has been run (logs are created during execution)")
        sys.exit(1)
    
    entries = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    
    return entries


def format_timestamp(iso_string: str) -> str:
    """Format ISO timestamp to readable format."""
    try:
        dt = datetime.fromisoformat(iso_string.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        return iso_string


def print_entry(entry: Dict[str, Any], show_raw: bool = False):
    """Print a single log entry in readable format."""
    entry_type = entry.get("type", "unknown")
    timestamp = format_timestamp(entry.get("timestamp", ""))
    
    print(f"\n{'='*80}")
    print(f"[{timestamp}] {entry_type.upper()}")
    print(f"{'='*80}")
    
    if entry_type == "agent_turn":
        agent = entry.get("agent", {})
        print(f"Agent: {agent.get('name', 'unknown')} ({agent.get('role', 'unknown')})")
        print(f"Phase: {entry.get('phase', 'unknown')} | Round: {entry.get('round_number', 'unknown')}")
        
        response = entry.get("response", {})
        print(f"\nResponse:")
        print(f"  Success: {response.get('success', False)}")
        print(f"  Output keys: {', '.join(response.get('output_keys', []))}")
        
        if response.get("output_preview"):
            print(f"\n  Output preview:")
            print(f"  {response['output_preview'][:500]}")
        
        if entry.get("raw_llm_output"):
            if show_raw:
                print(f"\n  Raw LLM Output:")
                print(f"  {entry['raw_llm_output']}")
            else:
                print(f"\n  Raw LLM Output: {len(entry['raw_llm_output'])} chars (use --raw to see)")
        
        if entry.get("errors"):
            print(f"\n  Errors:")
            for error in entry["errors"]:
                print(f"    - {error}")
        
        file_updates = response.get("file_updates_count", 0)
        if file_updates > 0:
            print(f"\n  File updates: {file_updates}")
    
    elif entry_type == "moderator_action":
        print(f"Action: {entry.get('action', 'unknown')}")
        details = entry.get("details", {})
        if details:
            print(f"\nDetails:")
            for key, value in details.items():
                print(f"  {key}: {value}")
    
    elif entry_type == "file_update":
        print(f"File: {entry.get('file_type', 'unknown')}")
        print(f"Operation: {entry.get('operation', 'unknown')}")
        data = entry.get("data_preview", {})
        if data:
            print(f"\nData preview:")
            print(f"  {json.dumps(data, indent=2)[:500]}")
    
    elif entry_type == "llm_request":
        print(f"Agent: {entry.get('agent', 'unknown')}")
        print(f"Model: {entry.get('model', 'unknown')}")
        print(f"Prompt length: {entry.get('prompt_length', 0)} chars")
        if show_raw:
            print(f"\nPrompt preview:")
            print(f"  {entry.get('prompt_preview', '')}")
        else:
            print(f"  Prompt: {entry.get('prompt_preview', '')[:200]}...")
    
    elif entry_type == "llm_response":
        print(f"Agent: {entry.get('agent', 'unknown')}")
        print(f"Model: {entry.get('model', 'unknown')}")
        print(f"Response length: {entry.get('response_length', 0)} chars")
        if entry.get("tokens_used"):
            print(f"Tokens used: {entry.get('tokens_used')}")
        if entry.get("cost"):
            print(f"Cost: ${entry.get('cost'):.4f}")
        if show_raw:
            print(f"\nResponse:")
            print(f"  {entry.get('response_preview', '')}")
        else:
            print(f"  Response preview: {entry.get('response_preview', '')[:200]}...")
    
    elif entry_type == "error":
        print(f"Error Type: {entry.get('error_type', 'unknown')}")
        print(f"Message: {entry.get('message', 'unknown')}")
        if entry.get("traceback") and show_raw:
            print(f"\nTraceback:")
            print(f"  {entry['traceback']}")
    
    elif entry_type == "system":
        print(f"Event: {entry.get('event', 'unknown')}")
    
    else:
        print(f"Raw entry:")
        print(json.dumps(entry, indent=2))


def view_logs(
    debate_id: str,
    filter_type: Optional[str] = None,
    filter_agent: Optional[str] = None,
    show_raw: bool = False
):
    """View debate logs with optional filtering."""
    entries = load_logs(debate_id)
    
    if not entries:
        print(f"❌ No log entries found for debate {debate_id}")
        return
    
    print(f"\n{'='*80}")
    print(f"DEBATE LOG VIEWER")
    print(f"{'='*80}")
    print(f"Debate ID: {debate_id}")
    print(f"Total entries: {len(entries)}")
    print(f"{'='*80}\n")
    
    # Apply filters
    filtered_entries = entries
    if filter_type:
        filtered_entries = [e for e in filtered_entries if e.get("type") == filter_type]
        print(f"Filtered by type: {filter_type} ({len(filtered_entries)} entries)\n")
    
    if filter_agent:
        filtered_entries = [
            e for e in filtered_entries
            if e.get("agent", {}).get("name") == filter_agent or e.get("agent") == filter_agent
        ]
        print(f"Filtered by agent: {filter_agent} ({len(filtered_entries)} entries)\n")
    
    # Print entries
    for entry in filtered_entries:
        print_entry(entry, show_raw=show_raw)
    
    # Summary
    print(f"\n{'='*80}")
    print(f"SUMMARY")
    print(f"{'='*80}")
    
    type_counts = {}
    for entry in entries:
        entry_type = entry.get("type", "unknown")
        type_counts[entry_type] = type_counts.get(entry_type, 0) + 1
    
    for entry_type, count in sorted(type_counts.items()):
        print(f"  {entry_type}: {count}")
    
    print(f"{'='*80}\n")


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python view_debate_log.py <debate_id|last> [options]")
        print("\nOptions:")
        print("  --filter <type>     Filter by entry type (agent_turn, llm_request, etc.)")
        print("  --agent <name>      Filter by agent name")
        print("  --raw               Show full raw outputs")
        print("\nExamples:")
        print("  python view_debate_log.py abc-123")
        print("  python view_debate_log.py last")
        print("  python view_debate_log.py last --filter agent_turn")
        print("  python view_debate_log.py abc-123 --agent debator_a --raw")
        sys.exit(1)
    
    debate_id = sys.argv[1]
    
    # Handle "last" keyword to find most recent debate
    if debate_id.lower() == "last":
        most_recent = find_most_recent_debate()
        if most_recent is None:
            print("❌ No debates found in debates/ directory")
            print("\nMake sure you have run at least one debate.")
            sys.exit(1)
        debate_id = most_recent
        print(f"📋 Using most recent debate: {debate_id}\n")
    
    # Parse options
    filter_type = None
    filter_agent = None
    show_raw = False
    
    i = 2
    while i < len(sys.argv):
        if sys.argv[i] == "--filter" and i + 1 < len(sys.argv):
            filter_type = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--agent" and i + 1 < len(sys.argv):
            filter_agent = sys.argv[i + 1]
            i += 2
        elif sys.argv[i] == "--raw":
            show_raw = True
            i += 1
        else:
            i += 1
    
    view_logs(debate_id, filter_type, filter_agent, show_raw)


if __name__ == "__main__":
    main()
