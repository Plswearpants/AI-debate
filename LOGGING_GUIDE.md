# 📊 Debate Logging System

**Comprehensive logging for debugging and monitoring debate execution.**

---

## 🎯 What Gets Logged

The logger captures **everything** that happens during a debate:

### **Agent Turns**
- Agent name, role, phase, round
- Input context (topic, instructions, state keys)
- Response output (success, output keys, preview)
- File updates count
- Errors if any
- Raw LLM output (when available)

### **Moderator Actions**
- Phase transitions
- Vote 0 results
- Checkpoint saves
- Debate start/end

### **File Updates**
- File type and operation
- Data preview (truncated for size)

### **Errors**
- Error type and message
- Full traceback
- Context when error occurred

### **LLM Requests/Responses** (Future)
- Model used
- Prompt preview
- Response preview
- Tokens and cost

---

## 📁 Log File Location

**Location**: `debates/<debate-id>/debate_log.jsonl`

**Format**: JSON Lines (one JSON object per line)

**Example path**:
```
debates/86e4bc7c-1269-4d7f-9228-468218c243d9/debate_log.jsonl
```

---

## 🔍 Viewing Logs

### **Basic View**

```bash
python view_debate_log.py <debate-id>
```

**Example**:
```bash
python view_debate_log.py 86e4bc7c-1269-4d7f-9228-468218c243d9
```

### **View Most Recent Debate**

```bash
# Automatically finds and views the most recent debate
python view_debate_log.py last
```

**Example**:
```bash
python view_debate_log.py last
python view_debate_log.py last --filter error
python view_debate_log.py last --raw
```

### **Filter by Type**

```bash
# Only agent turns
python view_debate_log.py <debate-id> --filter agent_turn

# Only errors
python view_debate_log.py <debate-id> --filter error

# Only moderator actions
python view_debate_log.py <debate-id> --filter moderator_action
```

### **Filter by Agent**

```bash
# Only debator_a logs
python view_debate_log.py <debate-id> --agent debator_a

# Only crowd logs
python view_debate_log.py <debate-id> --agent crowd
```

### **Show Raw Outputs**

```bash
# Show full raw LLM outputs (can be very long)
python view_debate_log.py <debate-id> --raw
```

### **Combined Filters**

```bash
# Agent turns for debator_a with raw output
python view_debate_log.py <debate-id> --filter agent_turn --agent debator_a --raw
```

---

## 📋 Log Entry Types

### **1. agent_turn**

```json
{
  "type": "agent_turn",
  "timestamp": "2026-01-10T12:34:56",
  "agent": {
    "name": "debator_a",
    "role": "debator"
  },
  "phase": "opening",
  "round_number": 1,
  "context": {...},
  "response": {
    "success": true,
    "output_keys": ["statement", "citations"],
    "output_preview": "...",
    "file_updates_count": 2
  },
  "raw_llm_output": "...",
  "errors": []
}
```

### **2. moderator_action**

```json
{
  "type": "moderator_action",
  "timestamp": "2026-01-10T12:34:56",
  "action": "phase_transition",
  "details": {
    "from": "opening",
    "to": "debate_rounds"
  },
  "state": {...}
}
```

### **3. file_update**

```json
{
  "type": "file_update",
  "timestamp": "2026-01-10T12:34:56",
  "file_type": "history_chat",
  "operation": "APPEND_TURN",
  "data_preview": {...}
}
```

### **4. error**

```json
{
  "type": "error",
  "timestamp": "2026-01-10T12:34:56",
  "error_type": "agent_failure",
  "message": "Agent failed: ...",
  "traceback": "...",
  "context": {...}
}
```

---

## 🔧 Manual Log Inspection

### **View as JSON**

```bash
# Pretty print entire log
python -c "import json; [print(json.dumps(json.loads(line), indent=2)) for line in open('debates/<id>/debate_log.jsonl')]"
```

### **Count Entries**

```bash
# Count total entries
wc -l debates/<id>/debate_log.jsonl

# Count by type
python -c "import json; types = [json.loads(l)['type'] for l in open('debates/<id>/debate_log.jsonl')]; from collections import Counter; print(Counter(types))"
```

### **Extract Specific Data**

```python
# Python script to extract all agent outputs
import json

with open('debates/<id>/debate_log.jsonl') as f:
    for line in f:
        entry = json.loads(line)
        if entry['type'] == 'agent_turn':
            print(f"{entry['agent']['name']}: {entry['response']['output_preview']}")
```

---

## 🎯 Common Use Cases

### **1. Debug a Failed Debate**

```bash
# See all errors
python view_debate_log.py <id> --filter error --raw

# See what happened before the error
python view_debate_log.py <id> | tail -100
```

### **2. Check Agent Responses**

```bash
# See all debator responses
python view_debate_log.py <id> --filter agent_turn --agent debator_a

# See raw LLM outputs
python view_debate_log.py <id> --filter agent_turn --raw
```

### **3. Track File Updates**

```bash
# See all file operations
python view_debate_log.py <id> --filter file_update
```

### **4. Monitor Phase Transitions**

```bash
# See all phase transitions
python view_debate_log.py <id> --filter moderator_action | grep phase_transition
```

---

## 📊 Log File Size

**Typical sizes**:
- Small debate (1 round): ~50-100 KB
- Full debate (2 rounds): ~200-500 KB
- Very verbose (with --raw): ~1-2 MB

**Note**: Logs are truncated to prevent huge files:
- Prompts: First 1000 chars
- Responses: First 2000 chars
- Tracebacks: First 2000 chars

---

## 🔍 Finding Your Debate ID

**From terminal output**:
```
Debate ID: 86e4bc7c-1269-4d7f-9228-468218c243d9
```

**From checkpoint file**:
```bash
# List all debates
ls debates/

# Check checkpoint for ID
cat debates/*/moderator_checkpoint.json | grep debate_id
```

---

## 💡 Tips

1. **Use filters** - Logs can be long, filter to what you need
2. **Start with summary** - Run without filters first to see overview
3. **Use --raw sparingly** - Raw outputs are very long
4. **Check errors first** - If debate failed, check error entries
5. **Follow timeline** - Entries are chronological, read top to bottom

---

## 🚀 Quick Start

```bash
# 1. Run a debate
python run_debate.py "Your topic"

# 2. View the log (use "last" for most recent)
python view_debate_log.py last

# Or use the Debate ID from output
python view_debate_log.py <debate-id>

# 3. Filter if needed
python view_debate_log.py last --filter error
```

---

**The logger is automatically enabled** - no configuration needed!  
**Logs are created** in `debates/<id>/debate_log.jsonl` during execution.
