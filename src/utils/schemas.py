"""
JSON Schemas for Structured Outputs

Defines JSON schemas for deterministic parsing of agent outputs.
Used with Gemini Interactions API response_format parameter.
"""

from typing import Dict, Any


# Schema for Debator Statement Output
DEBATOR_STATEMENT_SCHEMA = {
    "type": "object",
    "properties": {
        "main_statement": {
            "type": "string",
            "description": "The main debate statement visible to audience. Include all inline citations like [a_1], [a_2]."
        },
        "supplementary_material": {
            "type": "string",
            "description": "Internal notes and analysis for your team only. Not visible to audience or opponent."
        },
        "citations": {
            "type": "array",
            "description": "List of citations used with their source mappings",
            "items": {
                "type": "object",
                "properties": {
                    "citation_key": {
                        "type": "string",
                        "description": "Citation key like 'a_1' or 'b_2'"
                    },
                    "source_url": {
                        "type": "string",
                        "description": "URL of the source"
                    },
                    "source_title": {
                        "type": "string",
                        "description": "Title of the source"
                    },
                    "relevant_quote": {
                        "type": "string",
                        "description": "Relevant quote or data from the source"
                    }
                },
                "required": ["citation_key", "source_url"]
            }
        }
    },
    "required": ["main_statement", "citations"]
}


# Schema for Judge Analysis Output
JUDGE_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "consensus": {
            "type": "array",
            "description": "Points where both sides agree",
            "items": {"type": "string"}
        },
        "disagreement_frontier": {
            "type": "array",
            "description": "Core issues still being contested",
            "items": {
                "type": "object",
                "properties": {
                    "core_issue": {"type": "string"},
                    "a_stance": {"type": "string"},
                    "b_stance": {"type": "string"}
                },
                "required": ["core_issue", "a_stance", "b_stance"]
            }
        }
    },
    "required": ["consensus", "disagreement_frontier"]
}


# Schema for FactChecker Verification Output
FACTCHECKER_VERIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "source_credibility_score": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
            "description": "Credibility of the source (1-10)"
        },
        "content_correspondence_score": {
            "type": "integer",
            "minimum": 1,
            "maximum": 10,
            "description": "How well the source supports the claim (1-10)"
        },
        "adversary_comment": {
            "type": "string",
            "description": "Brief critical analysis of the citation and why the scores are given"
        }
    },
    "required": ["source_credibility_score", "content_correspondence_score", "adversary_comment"]
}


# Schema for Crowd Voting Output
CROWD_VOTE_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {
            "type": "integer",
            "minimum": 0,
            "maximum": 100,
            "description": "Vote score (0-100)"
        },
        "reasoning": {
            "type": "string",
            "description": "Brief explanation for the vote"
        }
    },
    "required": ["score"]
}


def get_schema(agent_type: str, task_type: str = "default") -> Dict[str, Any]:
    """
    Get JSON schema for agent output.
    
    Args:
        agent_type: Type of agent ("debator", "judge", "factchecker", "crowd")
        task_type: Specific task ("statement", "analysis", "verification", "vote")
    
    Returns:
        JSON schema dictionary
    """
    schemas = {
        "debator": {
            "statement": DEBATOR_STATEMENT_SCHEMA,
            "default": DEBATOR_STATEMENT_SCHEMA
        },
        "judge": {
            "analysis": JUDGE_ANALYSIS_SCHEMA,
            "default": JUDGE_ANALYSIS_SCHEMA
        },
        "factchecker": {
            "verification": FACTCHECKER_VERIFICATION_SCHEMA,
            "default": FACTCHECKER_VERIFICATION_SCHEMA
        },
        "crowd": {
            "vote": CROWD_VOTE_SCHEMA,
            "default": CROWD_VOTE_SCHEMA
        }
    }
    
    return schemas.get(agent_type, {}).get(task_type, {})
