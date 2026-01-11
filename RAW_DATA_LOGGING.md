# 📁 Raw Model Call Logging

**Complete LLM input/output logging for every model call**

---

## Overview

The Raw Data Logger captures **every single LLM API call** with complete details including full prompts and responses. This provides unprecedented visibility into model behavior for debugging, analysis, and optimization.

---

## What Gets Logged

Every model call captures:

| Field | Description |
|-------|-------------|
| **Timestamp** | When the call was made (UTC) |
| **Agent Name** | Which agent made the call (`debator_a`, `judge`, etc.) |
| **Model ID** | Exact model used (e.g., `google/gemini-2.0-flash-exp:free`) |
| **Parameters** | Temperature, max_tokens |
| **System Prompt** | Full system prompt (if provided) |
| **User Prompt** | Full user prompt |
| **Response** | Complete model response |
| **Metadata** | Response length (chars, lines), batch info |

---

## File Location

```
debates/{debate_id}/raw_model_calls.jsonl
```

Each line is a JSON object representing one model call or batch.

---

## Why This Is Valuable

### **1. Prompt Engineering**
- See exactly what prompts are sent to models
- Identify prompt issues causing unexpected outputs
- Test and refine prompt templates

###2. **Response Analysis**
- Analyze model outputs for quality and consistency
- Compare responses across different models
- Identify patterns in model behavior

### **3. **Debugging**
- Understand why a model produced unexpected output
- Trace issues back to specific inputs
- Reproduce problems with exact inputs

### **4. Cost Optimization**
- Analyze token usage patterns
- Identify expensive calls
- Optimize prompt lengths

### **5. Model Comparison**
- Compare outputs across different models
- A/B test model changes
- Validate model selection

### **6. Training Data**
- Create datasets from real debate interactions
- Build fine-tuning datasets
- Generate synthetic training examples

---

## Log Format

### Single Call Example

```json
{
  "timestamp": "2026-01-11T20:30:45Z",
  "debate_id": "abc123...",
  "agent_name": "debator_a",
  "model": "google/gemini-2.0-flash-exp:free",
  "parameters": {
    "temperature": 0.7,
    "max_tokens": 4096
  },
  "input": {
    "system_prompt": "You are a skilled debater representing the AGAINST position...",
    "user_prompt": "Generate an opening argument about universal basic income...",
    "full_input": "[SYSTEM]\nYou are...\n\n[USER]\nGenerate..."
  },
  "output": {
    "response": "{\"argument\": \"Universal basic income represents...\", ...}",
    "length_chars": 2847,
    "length_lines": 42
  }
}
```

### Batch Call Example (Crowd Voting)

```json
{
  "timestamp": "2026-01-11T20:31:15Z",
  "debate_id": "abc123...",
  "agent_name": "crowd",
  "model": "meta-llama/llama-3.1-8b-instruct:free",
  "call_type": "batch",
  "parameters": {
    "temperature": 0.8,
    "max_tokens": 100
  },
  "input": {
    "batch_size": 10,
    "prompts": [
      "You are: Conservative business owner...",
      "You are: Progressive activist..."
    ]
  },
  "output": {
    "batch_size": 10,
    "responses": [
      "{\"score\": 35, \"reasoning\": \"...\"}",
      "{\"score\": 78, \"reasoning\": \"...\"}"
    ],
    "avg_length_chars": 85.4
  }
}
```

---

## Viewing Raw Calls

### **Basic View**

```bash
# View all calls for a debate
python view_raw_calls.py <debate_id>

# View most recent debate
python view_raw_calls.py last
```

### **Filtered Views**

```bash
# Filter by agent
python view_raw_calls.py <debate_id> --agent debator_a
python view_raw_calls.py <debate_id> --agent judge
python view_raw_calls.py <debate_id> --agent crowd

# Filter by model
python view_raw_calls.py <debate_id> --model gemini
python view_raw_calls.py <debate_id> --model perplexity
python view_raw_calls.py <debate_id> --model claude

# Hide summary statistics
python view_raw_calls.py <debate_id> --no-summary
```

---

## Example Output

```
================================================================================
RAW MODEL CALLS - Debate abc123
================================================================================
Total calls: 47

Calls by agent:
  - crowd: 2
  - debator_a: 8
  - debator_b: 8
  - factchecker_a: 7
  - factchecker_b: 7
  - judge: 15

Calls by model:
  - google/gemini-2.0-flash-exp:free: 16
  - perplexity/llama-3.1-sonar-small-128k-online: 14
  - anthropic/claude-3.5-sonnet:free: 15
  - meta-llama/llama-3.1-8b-instruct:free: 2

================================================================================
CALL #1
================================================================================
Timestamp:  2026-01-11 20:30:45
Agent:      debator_a
Model:      google/gemini-2.0-flash-exp:free
Parameters: temp=0.7, max_tokens=4096
Response:   2847 chars, 42 lines

----------------------------------------------------------------------------------------------------
SYSTEM PROMPT:
You are a skilled debater representing the AGAINST position on the topic:
"Should universal basic income be implemented?"

Your goal is to construct compelling arguments that persuade the audience...

----------------------------------------------------------------------------------------------------
USER PROMPT:
Generate an opening statement for the debate topic: "Should universal basic income be implemented?"

Your statement should:
1. Clearly state your position (AGAINST)
2. Provide 3-5 strong arguments
3. Include credible sources and data
4. Be persuasive and engaging

Return your response in JSON format...

----------------------------------------------------------------------------------------------------
RESPONSE:
{
  "argument": "Universal basic income represents a fundamentally flawed approach to economic security...",
  "sources": [
    {"id": "a_1", "text": "According to the World Bank (2023)...", "url": "..."},
    {"id": "a_2", "text": "A MIT study found...", "url": "..."}
  ],
  ...
}
```

---

## Manual Inspection

You can directly read the JSONL file using command-line tools:

```bash
# View raw file
cat debates/{debate_id}/raw_model_calls.jsonl

# Count total calls
wc -l debates/{debate_id}/raw_model_calls.jsonl

# Search for specific agent
grep "debator_a" debates/{debate_id}/raw_model_calls.jsonl | wc -l

# Pretty print first call
head -1 debates/{debate_id}/raw_model_calls.jsonl | python -m json.tool

# Find all calls to a specific model
grep '"model": "google/gemini' debates/{debate_id}/raw_model_calls.jsonl
```

---

## Use Cases

### **Debug Unexpected Agent Behavior**

1. View all calls from the problematic agent
2. Examine the input prompts sent
3. Check if response format matches expectations
4. Identify prompt engineering issues

```bash
python view_raw_calls.py <debate_id> --agent debator_a
```

### **Analyze Model Performance**

1. Filter by specific model
2. Compare response quality
3. Measure consistency
4. Identify failure patterns

```bash
python view_raw_calls.py <debate_id> --model gemini
```

### **Optimize Prompts**

1. Review actual prompts being sent
2. Identify verbose or redundant sections
3. Test prompt variations
4. Measure impact on response quality

### **Cost Analysis**

1. Count total model calls
2. Identify most expensive agents/phases
3. Calculate token usage
4. Find optimization opportunities

### **Model Migration**

1. Capture baseline outputs with current model
2. Switch to new model
3. Compare outputs side-by-side
4. Validate migration success

---

## File Size Considerations

Raw model call logs can grow large:

- **Typical debate**: 1-5 MB
- **Long debate**: 10-20 MB
- **With many rounds**: 50+ MB

The files are automatically created per debate, so they won't grow indefinitely. Old debates can be archived or deleted as needed.

---

## Privacy & Security

**Important**: Raw logs contain complete model inputs and outputs, which may include:

- Sensitive debate topics
- Research data
- Model behavior patterns

**Recommendations**:
- Don't commit raw logs to version control (already in `.gitignore`)
- Be careful when sharing debate directories
- Sanitize logs before using for training data
- Consider encryption for sensitive debates

---

## Technical Implementation

### Logger Class

Location: `src/utils/raw_data_logger.py`

```python
from src.utils.raw_data_logger import RawDataLogger

# Create logger
logger = RawDataLogger(debate_id, debate_dir)

# Log a single call
logger.log_model_call(
    agent_name="debator_a",
    model="google/gemini-2.0-flash-exp:free",
    prompt="Generate an opening statement...",
    response="{...}",
    system_prompt="You are a skilled debater...",
    temperature=0.7,
    max_tokens=4096
)

# Log a batch call (crowd voting)
logger.log_batch_call(
    agent_name="crowd",
    model="meta-llama/llama-3.1-8b-instruct:free",
    prompts=[...],
    responses=[...],
    temperature=0.8,
    max_tokens=100
)
```

### Integration Points

The logger is automatically integrated at:

1. **OpenRouterClient.generate()** - Logs all single model calls
2. **OpenRouterClient.generate_batch()** - Logs batch calls
3. **All adapters** - Set agent context before calling client

No manual logging needed in agent code!

---

## Related Documentation

- **[LOGGING_GUIDE.md](LOGGING_GUIDE.md)** - High-level debate event logging
- **[ADAPTER_INTERFACE_SPEC.md](ADAPTER_INTERFACE_SPEC.md)** - Adapter specifications
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - System deployment

---

**Last Updated**: January 2026  
**Status**: Fully implemented and production-ready
