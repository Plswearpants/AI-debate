# Cost Control System

**Purpose**: Monitor and contain Deep Research costs while maintaining debate quality  
**Based on**: Comprehensive cost analysis (see Key Insights section below)

---

## 💡 Key Cost Insights

From comprehensive analysis of Gemini Deep Research economics:

### The 200k Token Cliff ⚠️
- **Below 200k tokens**: Input $2/1M, Output $12/1M
- **Above 200k tokens**: Input $4/1M, Output $18/1M  
- **Impact**: Costs **double/1.5x** after crossing threshold!

### Cost Components
1. **Grounding**: $0.035 per search query (adds up fast with 20-40 queries)
2. **Input tokens**: Reading sources and context
3. **Output tokens**: "Thinking" tokens + final report (most expensive)
4. **Cached reprocessing**: Stateful overhead as context grows

### Real-World Scenarios
- **Simple research** (Executive brief): ~$0.12
- **Standard research** (Typical debate): ~$1-2
- **Complex research** (Deep due diligence): ~$4.74

### The Context Balloon Effect
As agent researches, context grows → Each step costs more → "Recursive debt"

**Our Strategy**: Stay under 180k tokens and use caching aggressively.

---

## 🎛️ Cost Control Knobs

### 1. Budget Presets (Primary Control)

Three preset budgets balancing cost vs quality:

| Preset | Max Cost/Debate | Deep Research Calls | Max Time/Research | Use Case |
|--------|----------------|---------------------|-------------------|----------|
| **Conservative** | $2.00 | 2 (opening only) | 3 min | High volume, budget-constrained |
| **Balanced** | $5.00 | 4 (opening + round 1) | 5 min | Default, good quality/cost |
| **Premium** | $15.00 | 6 (all rounds) | 10 min | High-stakes, quality priority |

**Usage**:
```bash
# In .env file
COST_BUDGET_PRESET=balanced
```

### 2. Per-Research Limits

Fine-grained controls for each Deep Research call:

```python
CostBudget(
    max_cost_per_research=2.0,      # Hard cap per research
    max_grounding_queries=20,        # Limit search queries
    max_context_tokens=180000,       # Stay below 200k cliff!
    max_output_tokens=15000,         # Limit thinking + report
    max_research_time=300            # 5 minutes timeout
)
```

**Why these limits?**
- **200k cliff**: Costs double after 200k tokens → Stay at 180k
- **Grounding**: Each query = $0.035 → 20 queries = $0.70
- **Output tokens**: Most expensive ($12-18/1M) → Limit thinking
- **Time**: Prevent runaway research loops

### 3. Per-Debate Limits

Controls for entire debate session:

```python
max_cost_per_debate=5.0              # Total budget
max_deep_research_calls=4            # Number of expensive calls
use_quick_search_threshold=1.0       # Switch to cheap search
```

**Logic**:
- Track cumulative cost across all phases
- Prevent budget overrun
- Automatic fallback when budget low

---

## 📊 Cost Tracking & Monitoring

### Real-Time Tracking

```python
cost_tracker = CostTracker(budget)

# After each research:
cost_tracker.record_research_cost(
    cost=2.15,
    is_deep=True,
    phase="opening"
)

# Check budget:
if cost_tracker.can_afford_deep_research():
    # Use Deep Research
else:
    # Fallback to quick search
```

### Cost Report

```python
report = cost_tracker.get_report()
# {
#   "total_cost": 3.45,
#   "remaining_budget": 1.55,
#   "deep_research_count": 2,
#   "costs_by_phase": {
#     "opening": 1.80,
#     "rebuttal": 1.65,
#     ...
#   },
#   "budget_utilization": 69.0%
# }
```

---

## 🔄 Adaptive Research Strategy

### Tiered Research Based on Budget

```python
def select_research_tier(remaining_budget):
    if remaining_budget < $0.50:
        return QUICK           # Google Search only (~$0.10)
    elif remaining_budget < $1.50:
        return STANDARD        # Limited Deep Research (~$1.00)
    elif remaining_budget < $4.00:
        return DEEP            # Full Deep Research (~$3.00)
    else:
        return EXHAUSTIVE      # No limits (~$5.00)
```

**Automatic Degradation**:
- Opening: Always use Deep Research (quality matters)
- Rebuttal 1: Use Deep if budget allows, else Standard
- Rebuttal 2: Use Standard if budget low, else Quick Search
- Closing: No research needed

---

## 💰 Cost Estimation

### Pre-Flight Cost Estimates

Before each Deep Research call, estimate cost:

```python
estimated_cost = estimate_deep_research_cost(
    num_queries=20,          # Expected search queries
    context_tokens=150000,   # Tokens to ingest
    output_tokens=10000,     # Thinking + report
    cached_reprocessing=2000000  # Stateful overhead
)

# estimated_cost ≈ $2.15

if estimated_cost > budget.max_cost_per_research:
    # Reject or use cheaper alternative
```

### Cost Components Breakdown

```
Grounding:        20 queries × $0.035 = $0.70
Input tokens:     150k @ $2/1M       = $0.30
Output tokens:    10k @ $12/1M       = $0.12
Cached reprocess: 2M @ $0.40/1M      = $0.80
Context overhead: (various)          = $0.23
───────────────────────────────────────────
Total:                                 $2.15
```

---

## 🛡️ Fallback Mechanisms

### 1. Quick Search Fallback

When budget low, use `google_search` tool instead of Deep Research:

```python
# Quick search: ~$0.10 (95% cheaper!)
report = gemini.generate_with_search(
    prompt="Research {topic} focusing on {stance}",
    tools=[{"type": "google_search"}]
)
```

**Tradeoffs**:
- ✅ 95% cheaper ($0.10 vs $2.00)
- ✅ 10x faster (30s vs 5min)
- ⚠️ Lower quality (basic search vs deep analysis)
- ⚠️ Fewer sources (3-5 vs 10-20)

### 2. No-Research Fallback

Use existing knowledge for closing or when budget exhausted:

```python
# No external research: ~$0.02
statement = gemini.generate(
    prompt="Summarize your arguments from previous rounds",
    system_instruction=system_prompt
)
```

---

## 🎯 Recommended Strategy per Phase

### Opening Statements (Always Quality)
- **Tier**: Deep Research
- **Budget**: Allocate 40% of total budget
- **Rationale**: Strong opening sets debate foundation

### Rebuttal Round 1 (Adaptive)
- **Tier**: Deep or Standard (based on remaining budget)
- **Budget**: Allocate 30% of total budget  
- **Rationale**: Important to address frontier, but can compromise

### Rebuttal Round 2 (Cost-Conscious)
- **Tier**: Standard or Quick (based on budget)
- **Budget**: Allocate 20% of total budget
- **Rationale**: Already have context, need targeted evidence

### Closing (No Research)
- **Tier**: None (use existing arguments)
- **Budget**: Allocate 10% for generation only
- **Rationale**: Summarization, no new evidence needed

---

## 📈 Budget Allocation Example

### Balanced Budget ($5.00)

```
Phase 0 (Init):      $0.05  (1%)
Phase 1 (Opening):   $2.00  (40%)  ← 2× Deep Research
  - debator_a: $1.00
  - debator_b: $1.00
Phase 2 Round 1:     $1.50  (30%)  ← 2× Standard/Quick
  - debator_a: $0.75
  - debator_b: $0.75
Phase 2 Round 2:     $0.75  (15%)  ← 2× Quick Search
  - debator_a: $0.40
  - debator_b: $0.35
Phase 3 (Closing):   $0.20  (4%)
Other (FC/Judge/Crowd): $0.50 (10%)
───────────────────────────────
Total:              $5.00 (100%)
```

---

## 🚨 Budget Alerts & Monitoring

### Warning Levels

```python
# Green: < 50% budget used
# Yellow: 50-75% budget used → Consider quick search
# Orange: 75-90% budget used → Use quick search only
# Red: > 90% budget used → No research, generation only
```

### Example Output

```
🟢 Budget Status: 25% used ($1.25 / $5.00)
   ├─ Opening: 2× Deep Research = $2.00
   ├─ Remaining: $3.75
   └─ Next: Can afford 1-2 more Deep Research

🟡 Budget Status: 65% used ($3.25 / $5.00)
   ├─ Used: Opening + Rebuttal 1 Deep Research
   ├─ Remaining: $1.75
   └─ Next: Use Standard tier or Quick Search

🟠 Budget Status: 85% used ($4.25 / $5.00)
   ├─ Used: Most of budget
   ├─ Remaining: $0.75
   └─ Next: Quick Search only ($0.10 each)

🔴 Budget Status: 95% used ($4.75 / $5.00)
   ├─ Used: Nearly exhausted
   ├─ Remaining: $0.25
   └─ Next: No research, use existing context
```

---

## 🔧 Implementation Status

✅ **Implemented**:
- Cost budget dataclasses (Conservative, Balanced, Premium)
- Cost tracker with real-time monitoring
- Cost estimation formulas
- Automatic fallback logic
- Budget presets in Config

✅ **Integrated**:
- Debator checks budget before each research
- Automatic tier selection based on remaining budget
- Fallback to quick search when needed
- Cost reporting after each operation

---

## 🎓 Best Practices

### 1. Start Conservatively
Begin with Conservative budget, measure actual costs, then scale up if needed.

### 2. Monitor First Debate
Run one debate with full logging to see actual cost breakdown.

### 3. Adjust Based on Topics
Complex topics (policy, economics) → Premium budget  
Simple topics (binary choices) → Conservative budget

### 4. Use Quick Search Strategically
Opening → Always Deep Research  
Rebuttal 1 → Deep if important issue  
Rebuttal 2 → Quick search usually sufficient  
Closing → No research

### 5. Avoid the 200k Cliff
The biggest cost jump! Keep context under 180k tokens through:
- Concise research queries
- Summarize previous rounds
- Prune irrelevant context

---

## 📊 Expected Costs by Preset

### Conservative ($2.00 budget)
- 2× Deep Research (opening): $2.00
- All rebuttals: Quick search fallback
- **Debates possible**: ~200 with $400 budget

### Balanced ($5.00 budget)
- 2× Deep Research (opening): $2.00
- 2× Deep/Standard (rebuttal 1): $1.50
- 2× Quick search (rebuttal 2): $0.20
- **Debates possible**: ~80 with $400 budget

### Premium ($15.00 budget)
- 6× Deep Research (all rounds): $12.00
- Higher quality, more sources
- **Debates possible**: ~27 with $400 budget

**Recommendation**: Start with **Balanced** preset for good quality at reasonable cost.

---

---

## 🎛️ Complete Knobs Reference

### Environment Variable Knobs

Set in `.env` file for simple control:

```bash
# Cost Control
COST_BUDGET_PRESET=balanced    # "conservative", "balanced", or "premium"

# Other related settings
NUM_DEBATE_ROUNDS=2           # More rounds = more cost
CROWD_SIZE=100                 # Crowd size affects voting cost
```

### Programmatic Knobs

Fine-tune in code:

```python
from src.utils.cost_controls import CostBudget

# Option 1: Use preset
budget = CostBudget.balanced()

# Option 2: Custom knobs
budget = CostBudget(
    # Per-research limits
    max_cost_per_research=2.0,      # Hard cap per call
    max_grounding_queries=20,        # Search query limit
    max_context_tokens=180000,       # Token cliff avoidance
    max_output_tokens=15000,         # Thinking token limit
    max_research_time=300,           # Timeout in seconds
    
    # Per-debate limits
    max_cost_per_debate=5.0,         # Total budget
    max_deep_research_calls=4,       # Expensive call limit
    use_quick_search_threshold=1.0   # Fallback threshold
)
```

### Runtime Knobs

Adjust during debate execution:

```python
# Check budget and adjust strategy
if cost_tracker.get_remaining_budget() < 2.0:
    # Use cheaper research tier
    tier = ResearchTier.STANDARD
else:
    # Use full Deep Research
    tier = ResearchTier.DEEP
```

---

**All cost controls are now implemented and tested! Ready to use.** ✅
