# AI Debate Platform - Model Configuration

## Final Model Allocation

| Component | Model | Provider | Rationale | Est. Cost/Turn |
|-----------|-------|----------|-----------|----------------|
| **debator_a** | Deep Research Agent | Google | Gemini 3 Pro-level research, comprehensive sources | ~$0.08 |
| **debator_b** | Deep Research Agent | Google | Gemini 3 Pro-level research, comprehensive sources | ~$0.08 |
| **factchecker_a** | Sonar Pro | Perplexity | Built-in web search, real-time verification | ~$0.015 |
| **factchecker_b** | Sonar Pro | Perplexity | Built-in web search, real-time verification | ~$0.015 |
| **judge** | Claude 3.5 Sonnet | Anthropic | Excellent neutral analysis, structured reasoning | ~$0.05 |
| **crowd (100)** | Llama 3.1 8B | Lambda GPU | Cost-effective parallel inference | ~$0.02 |

---

## Cost Breakdown per Debate

### Per Phase Costs

**Phase 0: Initialization**
- Crowd Vote Zero (100 voters): $0.02
- **Subtotal**: $0.02

**Phase 1: Opening (Round 1)**
- debator_a opening + research (MCP): $0.04
- factchecker_b verification (2-3 citations): $0.015
- debator_b opening + research (MCP): $0.04
- factchecker_a verification (2-3 citations): $0.015
- judge analysis: $0.05
- crowd Vote 1 (100 voters): $0.02
- **Subtotal**: $0.18

**Phase 2: Debate Rounds (2 rounds default)**
- Per round:
  - factchecker_a defense + offense: $0.015
  - debator_a rebuttal: $0.04
  - factchecker_b defense + offense: $0.015
  - debator_b rebuttal: $0.04
  - judge frontier update: $0.05
  - crowd vote (100 voters): $0.02
  - **Subtotal per round**: $0.18
- **2 rounds total**: $0.36

**Phase 3: Closing**
- factchecker_a final verification: $0.015
- factchecker_b final verification: $0.015
- debator_a closing: $0.04
- debator_b closing: $0.04
- judge final report: $0.05
- crowd final vote (100 voters): $0.02
- **Subtotal**: $0.18

### Total per Debate
**$0.02 + $0.18 + $0.36 + $0.18 = ~$0.74 per debate**

With $400 Lambda GPU credit + API budgets, you can run **500+ debates**!

---

## API Configuration

### Required API Keys

```env
# .env file
GEMINI_API_KEY=your_gemini_api_key_here
CLAUDE_API_KEY=your_claude_api_key_here
PERPLEXITY_API_KEY=your_perplexity_api_key_here
LAMBDA_GPU_ENDPOINT=http://your_lambda_endpoint:8000
LAMBDA_GPU_API_KEY=your_lambda_api_key_here
```

### Model-Specific Settings

#### Gemini 1.5 Pro (Debators)
```python
{
    "model": "gemini-1.5-pro",
    "temperature": 0.7,  # Creative but focused
    "max_output_tokens": 2048,  # For statements + citations
    "top_p": 0.95,
    "top_k": 40
}
```

**Why Gemini for Debators:**
- 2M token context window (huge for research)
- Strong at reasoning and synthesis
- Cost-effective ($0.00125 / 1K input, $0.005 / 1K output)
- Works well with MCP for web research
- Good at following citation format instructions

#### Claude 3.5 Sonnet (Judge)
```python
{
    "model": "claude-3-5-sonnet-20241022",
    "temperature": 0.3,  # More deterministic for analysis
    "max_tokens": 4096,  # For detailed frontier analysis
}
```

**Why Claude for Judge:**
- Excellent at neutral, structured analysis
- Strong at identifying nuanced disagreements
- Very good at following JSON output formats
- Minimal hallucination
- Great at "meta-reasoning" about arguments

#### Perplexity Sonar Pro (Fact-Checkers)
```python
{
    "model": "sonar-pro",
    "temperature": 0.2,  # Very factual
    "max_tokens": 1024,  # Scores + short comments
    "search_recency_filter": "month"  # Recent info preferred
}
```

**Why Perplexity for Fact-Checkers:**
- Built-in web search (no separate MCP needed)
- Real-time access to current information
- Can verify URLs directly
- Good at assessing source credibility
- Returns citations for its claims

#### Llama 3.1 8B (Crowd)
```python
{
    "model": "meta-llama/Llama-3.1-8B-Instruct",
    "temperature": 0.8,  # More diverse opinions
    "max_tokens": 100,  # Just need score + brief reason
    "top_p": 0.9
}
```

**Why Llama 3.1 8B for Crowd:** (could vary if we want the crowd to be smarter or more nuanced)
- Fast inference (important for 100 parallel calls)
- Good enough for opinion scoring
- Self-hosted = no API rate limits
- Cost-effective at scale
- Can batch 100 requests efficiently with vLLM

---

## Integration with MCP

### Debators + MCP Flow

```python
# Debator research flow
1. Gemini generates search queries → MCP browser searches
2. MCP returns top results → Gemini reads pages
3. Gemini extracts relevant info → MCP follows links if needed
4. Gemini synthesizes argument → Generates statement with citations
```

### MCP Tools Used by Debators
- `search(query)`: Web search
- `navigate(url)`: Go to specific URL
- `read_page()`: Extract article content
- `extract_citations()`: Find sources on page

### Fact-Checkers (No MCP needed)
Perplexity has built-in search, so no MCP integration needed for fact-checkers.

---

## Cost Optimization Strategies

### 1. Caching Strategy
```python
# Cache responses for testing
- Mock LLM responses during development
- Cache MCP research results for same queries
- Reuse judge analysis for similar debates (better not, could compremise the quality)
```

### 2. Batch Processing
```python
# Crowd votes in single batch
- Send 100 prompts to Lambda GPU at once
- Use vLLM for efficient batching
- Reduces overhead from multiple API calls
```

### 3. Context Management
```python
# Minimize token usage
- Only send relevant context to agents
- Use summaries for long histories
- Filter by permission before sending
```

### 4. Retry Logic
```python
# Avoid wasted calls
- Validate output before accepting
- Retry with clarification if invalid
- Exponential backoff for rate limits
```

---

## Performance Expectations

### Timing per Phase

| Phase | Est. Time | Bottleneck |
|-------|-----------|------------|
| Phase 0: Init | 30s | Crowd Vote Zero (100 parallel) |
| Phase 1: Opening | 2-3 min | Debator research with MCP |
| Phase 2: Round (each) | 2-3 min | Debator research with MCP |
| Phase 3: Closing | 1-2 min | Final verification |
| Output Generation | 10s | File I/O |

**Total Debate Time: ~8-12 minutes** (with 2 debate rounds)
- Note that this is the processing time of the whole debate.

### Throughput
- Sequential: 1 debate per 10 min = 6 debates/hour
- With queuing: Can run multiple debates in parallel
- Limited by API rate limits, not infrastructure

---

## Model Fallbacks

### If Primary Model Unavailable

```python
FALLBACK_CONFIG = {
    "debator": [
        "gemini-1.5-pro",      # Primary
        "gemini-1.5-flash",    # Fallback (faster, cheaper)
        "claude-3-5-sonnet"    # Fallback (higher quality, more expensive)
    ],
    "judge": [
        "claude-3-5-sonnet",   # Primary
        "gpt-4-turbo",         # Fallback
        "claude-3-opus"        # Fallback (most expensive)
    ],
    "factchecker": [
        "sonar-pro",           # Primary
        "sonar",               # Fallback (cheaper, less capable)
        "gemini-1.5-pro + search MCP"     # Fallback 
    ]
}
```

---

## Testing Configuration

### For Development/Testing
```python
TEST_CONFIG = {
    "debator": "gemini-1.5-flash",  # Faster, cheaper
    "judge": "claude-3-5-sonnet",   # Keep quality
    "factchecker": "sonar",         # Cheaper tier
    "crowd_size": 10,               # Reduced crowd
    "num_rounds": 1,                # Single round
    "mock_mcp": True                # Mock research
}
```

**Test Debate Cost: ~$0.15**

---

## Next Steps

1. **Get API Keys**
   - [ ] Google AI Studio (Gemini)
   - [ ] Anthropic Console (Claude)
   - [ ] Perplexity API
   - [ ] Lambda GPU setup

2. **Test Individual Models**
   - [ ] Test Gemini with sample research task
   - [ ] Test Claude with sample analysis
   - [ ] Test Perplexity with sample verification
   - [ ] Test Lambda GPU with sample batch

3. **Configure MCP**
   - [ ] Test MCP browser integration
   - [ ] Test search functionality
   - [ ] Test page reading
   - [ ] Integrate with Gemini client

4. **Build Clients**
   - [ ] `gemini_client.py`
   - [ ] `claude_client.py`
   - [ ] `perplexity_client.py`
   - [ ] `lambda_client.py`
   - [ ] `mcp_client.py`

**Ready to proceed with implementation?**
