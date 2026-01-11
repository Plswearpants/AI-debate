"""
JSON Parser Utilities - Robust JSON parsing for LLM responses.

Handles common LLM response formats:
- Plain JSON
- JSON wrapped in markdown code blocks (```json ... ```)
- Malformed JSON with fallback extraction
"""

import json
import re
from typing import Any, Dict, Optional


def strip_markdown_code_blocks(text: str) -> str:
    """
    Strip markdown code blocks from text.
    
    Handles formats like:
    - ```json\n{...}\n```
    - ```\n{...}\n```
    - {...}
    
    Args:
        text: Text possibly containing markdown code blocks
        
    Returns:
        Cleaned text without markdown wrappers
    """
    cleaned = text.strip()
    
    # Remove opening ```json or ``` with optional newline
    if cleaned.startswith('```'):
        cleaned = re.sub(r'^```(?:json|JSON)?\s*\n?', '', cleaned)
        # Remove closing ``` with optional newline
        cleaned = re.sub(r'\n?```\s*$', '', cleaned)
    
    return cleaned.strip()


def parse_json_response(response: str, fallback: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Parse JSON from LLM response, handling various formats.
    
    Args:
        response: LLM response text
        fallback: Optional fallback dict if parsing fails completely
        
    Returns:
        Parsed JSON dictionary
        
    Raises:
        json.JSONDecodeError: If parsing fails and no fallback provided
    """
    # Strip markdown code blocks
    cleaned = strip_markdown_code_blocks(response)
    
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        if fallback is not None:
            return fallback
        raise


def safe_json_loads(response: str, default: Any = None) -> Any:
    """
    Safely parse JSON with a default return value.
    
    Args:
        response: LLM response text
        default: Value to return if parsing fails
        
    Returns:
        Parsed JSON or default value
    """
    try:
        return parse_json_response(response)
    except json.JSONDecodeError:
        return default
