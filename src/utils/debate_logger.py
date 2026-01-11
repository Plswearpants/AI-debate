"""
Debate Logger - Comprehensive logging for all agent interactions and moderator actions.

Captures:
- All agent responses (raw LLM outputs)
- All moderator decisions
- All file updates
- All errors and warnings
- Timestamps for everything
"""

import json
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from threading import Lock


class DebateLogger:
    """Thread-safe logger for debate execution."""
    
    def __init__(self, debate_id: str, debate_dir: Path):
        """
        Initialize debate logger.
        
        Args:
            debate_id: Unique debate identifier
            debate_dir: Directory for this debate
        """
        self.debate_id = debate_id
        self.log_file = debate_dir / "debate_log.jsonl"  # JSON Lines format
        self.lock = Lock()  # Thread-safe writes
        
        # Initialize log file
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Write header
        self._write_entry({
            "type": "system",
            "event": "logger_initialized",
            "timestamp": datetime.now().isoformat(),
            "debate_id": debate_id
        })
    
    def log_agent_turn(
        self,
        agent_name: str,
        agent_role: str,
        phase: str,
        round_number: int,
        context: Dict[str, Any],
        response: Dict[str, Any],
        raw_llm_output: Optional[str] = None,
        errors: Optional[List[str]] = None
    ):
        """
        Log an agent's turn execution.
        
        Args:
            agent_name: Agent name (e.g., "debator_a")
            agent_role: Agent role (e.g., "debator")
            phase: Current phase
            round_number: Current round
            context: Agent context (input)
            response: Agent response (output)
            raw_llm_output: Raw LLM response before parsing
            errors: List of errors if any
        """
        entry = {
            "type": "agent_turn",
            "timestamp": datetime.now().isoformat(),
            "agent": {
                "name": agent_name,
                "role": agent_role
            },
            "phase": phase,
            "round_number": round_number,
            "context": {
                "topic": context.get("topic", ""),
                "instructions": context.get("instructions", ""),
                "current_state_keys": list(context.get("current_state", {}).keys())
            },
            "response": {
                "success": response.get("success", False),
                "output_keys": list(response.get("output", {}).keys()) if isinstance(response.get("output"), dict) else [],
                "output_preview": str(response.get("output", ""))[:500] if not isinstance(response.get("output"), dict) else "dict",
                "file_updates_count": len(response.get("file_updates", [])),
                "metadata": response.get("metadata", {})
            },
            "raw_llm_output": raw_llm_output[:2000] if raw_llm_output else None,  # Truncate for size
            "errors": errors or []
        }
        
        self._write_entry(entry)
    
    def log_moderator_action(
        self,
        action: str,
        details: Dict[str, Any],
        state_snapshot: Optional[Dict[str, Any]] = None
    ):
        """
        Log moderator action/decision.
        
        Args:
            action: Action name (e.g., "phase_transition", "file_update_applied")
            details: Action details
            state_snapshot: Optional state snapshot
        """
        entry = {
            "type": "moderator_action",
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "details": details,
            "state": state_snapshot
        }
        
        self._write_entry(entry)
    
    def log_file_update(
        self,
        file_type: str,
        operation: str,
        data: Dict[str, Any]
    ):
        """
        Log a file update operation.
        
        Args:
            file_type: File type (e.g., "history_chat")
            operation: Operation type (e.g., "ADD_STATEMENT")
            data: Update data
        """
        entry = {
            "type": "file_update",
            "timestamp": datetime.now().isoformat(),
            "file_type": file_type,
            "operation": operation,
            "data_preview": self._preview_data(data)
        }
        
        self._write_entry(entry)
    
    def log_error(
        self,
        error_type: str,
        message: str,
        traceback: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Log an error.
        
        Args:
            error_type: Error type (e.g., "agent_error", "file_error")
            message: Error message
            traceback: Full traceback if available
            context: Additional context
        """
        entry = {
            "type": "error",
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "message": message,
            "traceback": traceback[:2000] if traceback else None,  # Truncate
            "context": context
        }
        
        self._write_entry(entry)
    
    def log_llm_request(
        self,
        agent_name: str,
        model: str,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048
    ):
        """
        Log LLM API request (before sending).
        
        Args:
            agent_name: Agent making the request
            model: Model being used
            prompt: User prompt
            system_prompt: System prompt if any
            temperature: Temperature setting
            max_tokens: Max tokens setting
        """
        entry = {
            "type": "llm_request",
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "model": model,
            "prompt_preview": prompt[:1000],  # First 1000 chars
            "prompt_length": len(prompt),
            "system_prompt_preview": system_prompt[:500] if system_prompt else None,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        self._write_entry(entry)
    
    def log_llm_response(
        self,
        agent_name: str,
        model: str,
        response: str,
        tokens_used: Optional[int] = None,
        cost: Optional[float] = None
    ):
        """
        Log LLM API response (after receiving).
        
        Args:
            agent_name: Agent that made the request
            model: Model used
            response: Raw response text
            tokens_used: Tokens used if available
            cost: Cost if available
        """
        entry = {
            "type": "llm_response",
            "timestamp": datetime.now().isoformat(),
            "agent": agent_name,
            "model": model,
            "response_preview": response[:2000],  # First 2000 chars
            "response_length": len(response),
            "tokens_used": tokens_used,
            "cost": cost
        }
        
        self._write_entry(entry)
    
    def _preview_data(self, data: Any, max_depth: int = 2, max_items: int = 10) -> Any:
        """
        Create a preview of data structure (avoid logging huge objects).
        
        Args:
            data: Data to preview
            max_depth: Maximum nesting depth
            max_items: Maximum items in lists/dicts
        
        Returns:
            Preview version of data
        """
        if max_depth <= 0:
            return "..."
        
        if isinstance(data, dict):
            preview = {}
            for i, (key, value) in enumerate(data.items()):
                if i >= max_items:
                    preview["..."] = f"{len(data) - max_items} more items"
                    break
                preview[key] = self._preview_data(value, max_depth - 1, max_items)
            return preview
        elif isinstance(data, list):
            preview = []
            for i, item in enumerate(data):
                if i >= max_items:
                    preview.append(f"... {len(data) - max_items} more items")
                    break
                preview.append(self._preview_data(item, max_depth - 1, max_items))
            return preview
        elif isinstance(data, str):
            if len(data) > 500:
                return data[:500] + "... (truncated)"
            return data
        else:
            return str(data)[:200] if len(str(data)) > 200 else data
    
    def _write_entry(self, entry: Dict[str, Any]):
        """Write log entry to file (thread-safe)."""
        with self.lock:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    
    def get_log_path(self) -> Path:
        """Get path to log file."""
        return self.log_file
