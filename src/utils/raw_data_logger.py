"""
Raw Data Logger - Captures all LLM input/output for debugging and analysis.

Logs every model call with:
- Timestamp
- Agent name
- Model ID
- Full input prompt (system + user)
- Full output response
- Token counts (if available)
- Temperature and other parameters

Saves to: debates/{debate_id}/raw_model_calls.jsonl
"""

import json
import os
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class RawDataLogger:
    """Logger for capturing raw LLM input/output data."""
    
    def __init__(self, debate_id: str, debate_dir: str):
        """
        Initialize raw data logger.
        
        Args:
            debate_id: Debate identifier
            debate_dir: Path to debate directory
        """
        self.debate_id = debate_id
        self.debate_dir = debate_dir
        self.log_file = os.path.join(debate_dir, "raw_model_calls.jsonl")
        
        # Ensure directory exists
        Path(debate_dir).mkdir(parents=True, exist_ok=True)
    
    def log_model_call(
        self,
        agent_name: str,
        model: str,
        prompt: str,
        response: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log a model call with full input/output.
        
        Args:
            agent_name: Name of agent making the call
            model: Model ID used
            prompt: User prompt
            response: Model response
            system_prompt: System prompt (if any)
            temperature: Sampling temperature
            max_tokens: Max tokens setting
            metadata: Additional metadata
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "debate_id": self.debate_id,
            "agent_name": agent_name,
            "model": model,
            "parameters": {
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            "input": {
                "system_prompt": system_prompt,
                "user_prompt": prompt,
                "full_input": self._format_full_input(system_prompt, prompt)
            },
            "output": {
                "response": response,
                "length_chars": len(response),
                "length_lines": len(response.split('\n'))
            }
        }
        
        # Add optional metadata
        if metadata:
            entry["metadata"] = metadata
        
        # Append to log file
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    def log_batch_call(
        self,
        agent_name: str,
        model: str,
        prompts: list,
        responses: list,
        temperature: float = 0.8,
        max_tokens: int = 100,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Log a batch model call (for crowd voting).
        
        Args:
            agent_name: Name of agent making the call
            model: Model ID used
            prompts: List of prompts
            responses: List of responses
            temperature: Sampling temperature
            max_tokens: Max tokens setting
            metadata: Additional metadata
        """
        entry = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "debate_id": self.debate_id,
            "agent_name": agent_name,
            "model": model,
            "call_type": "batch",
            "parameters": {
                "temperature": temperature,
                "max_tokens": max_tokens
            },
            "input": {
                "batch_size": len(prompts),
                "prompts": prompts
            },
            "output": {
                "batch_size": len(responses),
                "responses": responses,
                "avg_length_chars": sum(len(r) for r in responses) / len(responses) if responses else 0
            }
        }
        
        # Add optional metadata
        if metadata:
            entry["metadata"] = metadata
        
        # Append to log file
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry, ensure_ascii=False) + '\n')
    
    def _format_full_input(self, system_prompt: Optional[str], user_prompt: str) -> str:
        """
        Format the complete input as it would appear to the model.
        
        Args:
            system_prompt: System prompt
            user_prompt: User prompt
            
        Returns:
            Formatted full input
        """
        parts = []
        if system_prompt:
            parts.append(f"[SYSTEM]\n{system_prompt}")
        parts.append(f"[USER]\n{user_prompt}")
        return "\n\n".join(parts)


def get_raw_data_logger(debate_id: str, debate_dir: str) -> RawDataLogger:
    """
    Get or create raw data logger for a debate.
    
    Args:
        debate_id: Debate identifier
        debate_dir: Path to debate directory
        
    Returns:
        RawDataLogger instance
    """
    return RawDataLogger(debate_id, debate_dir)
