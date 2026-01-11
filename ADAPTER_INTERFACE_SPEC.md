# OpenRouter Adapter Interface Specification

This document defines the unified interface for all OpenRouter adapters to ensure consistency across the platform.

## Overview

All adapters wrap `OpenRouterClient` to provide backward compatibility with existing agent code while using OpenRouter as a unified API gateway.

---

## GeminiAdapter (Debator Agent)

**Used by**: `DebatorAgent`  
**Model**: Configured via `GEMINI_MODEL` (e.g., `google/gemini-2.0-flash-exp:free`)  
**Perplexity Model**: Configured via `PERPLEXITY_MODEL` for web search operations

### Methods

#### `generate(prompt, temperature=0.7, max_tokens=4096, system_prompt=None, system_instruction=None, response_format=None)`

Generate text with the Gemini model.

**Parameters:**
- `prompt` (str): User prompt/query
- `temperature` (float): Sampling temperature (0.0-1.0)
- `max_tokens` (int): Maximum tokens to generate
- `system_prompt` (str, optional): System prompt for context
- `system_instruction` (str, optional): Alternative to system_prompt (takes precedence)
- `response_format` (dict, optional): JSON schema for structured output

**Returns:** `str` - Generated text

**Notes:**
- Accepts both `system_prompt` and `system_instruction` for compatibility
- `system_instruction` takes precedence if both provided

---

#### `generate_with_search(prompt, system_instruction=None, temperature=0.7, max_tokens=2048)`

Generate with web search (quick search fallback).

**Parameters:**
- `prompt` (str): Search query and context
- `system_instruction` (str, optional): System instruction
- `temperature` (float): Sampling temperature
- `max_tokens` (int): Maximum tokens

**Returns:** `str` - Response with web-grounded information

**Notes:**
- Uses Perplexity model (from config) for web search via OpenRouter
- Faster alternative to `deep_research()`

---

#### `deep_research(query, background=True, poll_interval=5, max_wait=300)`

Simulate deep research using web search.

**Parameters:**
- `query` (str): Research query
- `background` (bool): Run in background (compatibility param, ignored)
- `poll_interval` (int): Poll interval (compatibility param, ignored)
- `max_wait` (int): Maximum wait time (compatibility param, ignored)

**Returns:** `str` - Comprehensive research report

**Notes:**
- Approximates Gemini's native Deep Research using Perplexity via OpenRouter
- Background/polling params kept for compatibility but have no effect

---

## ClaudeAdapter (Judge Agent)

**Used by**: `JudgeAgent`  
**Model**: Configured via `CLAUDE_MODEL` (e.g., `anthropic/claude-3.5-sonnet:free`)

### Methods

#### `generate(prompt, temperature=0.3, max_tokens=2048, system_prompt=None, system=None)`

Generate text with the Claude model.

**Parameters:**
- `prompt` (str): User prompt/query
- `temperature` (float): Sampling temperature (0.0-1.0)
- `max_tokens` (int): Maximum tokens to generate
- `system_prompt` (str, optional): System prompt for context
- `system` (str, optional): Alternative to system_prompt (takes precedence)

**Returns:** `str` - Generated text

**Notes:**
- Accepts both `system_prompt` and `system` for compatibility
- `system` takes precedence if both provided

---

## PerplexityAdapter (FactChecker Agent)

**Used by**: `FactCheckerAgent`  
**Model**: Configured via `PERPLEXITY_MODEL` (e.g., `perplexity/llama-3.1-sonar-small-128k-online`)

### Methods

#### `chat(query=None, messages=None, temperature=0.2, max_tokens=1024, search_recency_filter=None)`

Chat with web search capabilities.

**Parameters:**
- `query` (str, optional): Direct query string
- `messages` (list, optional): List of message dicts (alternative to query)
- `temperature` (float): Sampling temperature
- `max_tokens` (int): Maximum tokens to generate
- `search_recency_filter` (str, optional): Recency filter (compatibility param, ignored)

**Returns:** `str` - Response with web-grounded information

**Notes:**
- Accepts both `query` (string) and `messages` (list) calling conventions
- If `messages` provided, extracts user message automatically
- `search_recency_filter` accepted for compatibility but ignored (OpenRouter limitation)

---

#### `verify_source(claim, source_url)`

Verify a claim against a source using web search.

**Parameters:**
- `claim` (str): Claim to verify
- `source_url` (str): Source URL to check against

**Returns:** `str` - Verification analysis

---

## LambdaAdapter (Crowd Agent)

**Used by**: `CrowdAgent`  
**Model**: Configured via `LAMBDA_MODEL` (e.g., `meta-llama/llama-3.1-8b-instruct:free`)

### Methods

#### `generate_single(prompt, temperature=0.8, max_tokens=100)`

Generate a single response.

**Parameters:**
- `prompt` (str): User prompt
- `temperature` (float): Sampling temperature
- `max_tokens` (int): Maximum tokens

**Returns:** `str` - Generated text

---

#### `generate_batch(prompts, temperature=0.8, max_tokens=100)`

Generate batch of responses (for crowd voting).

**Parameters:**
- `prompts` (list[str]): List of prompts
- `temperature` (float): Sampling temperature
- `max_tokens` (int): Maximum tokens per response

**Returns:** `list[str]` - List of generated texts

**Notes:**
- OpenRouter doesn't have native batch API, so makes parallel requests
- For true batch inference, use Lambda GPU directly

---

#### `health_check()`

Check if the client is accessible.

**Returns:** `dict` - Health status dictionary

---

## Unified Parameter Naming

### System Prompts

All adapters accept multiple parameter names for system prompts to ensure compatibility:

| Adapter | Primary | Alternative | Precedence |
|---------|---------|-------------|------------|
| **GeminiAdapter** | `system_prompt` | `system_instruction` | `system_instruction` |
| **ClaudeAdapter** | `system_prompt` | `system` | `system` |
| **PerplexityAdapter** | N/A (chat-based) | N/A | N/A |
| **LambdaAdapter** | N/A (simple prompts) | N/A | N/A |

### Message Formats

| Adapter | Accepts String | Accepts List | Notes |
|---------|---------------|--------------|-------|
| **GeminiAdapter** | ✅ `prompt` | ❌ | String prompts only |
| **ClaudeAdapter** | ✅ `prompt` | ❌ | String prompts only |
| **PerplexityAdapter** | ✅ `query` | ✅ `messages` | Both supported |
| **LambdaAdapter** | ✅ `prompt/prompts` | ❌ | String or list of strings |

---

## Agent Usage Summary

| Agent | Adapter | Main Method | Key Parameters |
|-------|---------|-------------|----------------|
| **DebatorAgent** | GeminiAdapter | `generate()`, `generate_with_search()`, `deep_research()` | `system_instruction`, `response_format` |
| **JudgeAgent** | ClaudeAdapter | `generate()` | `system` |
| **FactCheckerAgent** | PerplexityAdapter | `chat()`, `verify_source()` | `messages`, `search_recency_filter` |
| **CrowdAgent** | LambdaAdapter | `generate_batch()` | `prompts` |

---

## Compatibility Notes

### Parameters Accepted But Ignored

Some parameters are accepted for backward compatibility but have no effect with OpenRouter:

- **GeminiAdapter.deep_research()**: `background`, `poll_interval` - OpenRouter doesn't support async polling
- **PerplexityAdapter.chat()**: `search_recency_filter` - OpenRouter API doesn't expose this parameter

These are kept to maintain interface compatibility with direct API clients.

### Response Formats

- All adapters return plain strings
- Structured output via `response_format` parameter (GeminiAdapter) uses OpenRouter's JSON mode
- Agents are responsible for parsing JSON responses

---

## Testing Adapter Consistency

Use the verification script to ensure all adapters match agent expectations:

```bash
python verify_model_config.py
```

This validates:
- Config loads models from `.env` correctly
- Agents use config models, not hardcoded values
- No hardcoded model IDs in adapter classes

---

**Last Updated**: January 2026  
**Status**: All adapters unified and tested
