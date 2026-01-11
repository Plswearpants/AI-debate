# Citation Quality Guide

## Overview

The AI Debate Platform uses a two-stage research and citation process:

1. **Research Phase**: LLM conducts research on the topic
2. **Citation Phase**: Debator extracts and registers sources from research

The quality of citations depends heavily on which models you use for research.

---

## Current Issue (Free Models)

**Symptom**: Citations appear with placeholder URLs or Google Scholar search links

**Root Cause**: Free models (like `meta-llama/llama-3.3-70b-instruct:free`) don't have real-time web access:
- They generate research from training data
- Citations are synthetic/approximate (books, papers they "know about")
- No actual URLs are provided in research output

**What Happens**:
```
1. Research phase → LLM generates research with bibliographic citations (no URLs)
2. Parser extracts citations → Creates Google Scholar links as fallback
3. Debator uses these → Citations have generic/placeholder URLs
4. Fact-checker verifies → Correctly flags placeholders as unreliable
```

---

## Solution: Use Models with Web Search

### Recommended Configuration

For **high-quality, verifiable citations**, use models with real-time web access:

```env
# .env configuration
PERPLEXITY_MODEL=perplexity/llama-3.1-sonar-large-128k-online
# OR
PERPLEXITY_MODEL=perplexity/llama-3.1-sonar-small-128k-online
```

### How It Works

**Perplexity models** (via OpenRouter):
- ✅ Have real-time web search built-in
- ✅ Provide actual source URLs with citations
- ✅ Include recent data (not limited to training cutoff)
- ✅ Automatically cite specific web pages

**Example Output**:
```
According to a 2024 study by MIT [1], UBI could reduce poverty by 24%.

Sources:
1. https://www.mit.edu/research/ubi-poverty-study-2024
```

---

## Model Comparison

| Model Type | Web Access | Citation Quality | Cost | Best For |
|------------|-----------|------------------|------|----------|
| **Perplexity Sonar** | ✅ Real-time | Real URLs, current data | ~$0.005/req | Production debates |
| **Free Llama/Gemini** | ❌ Training data only | Synthetic citations | Free | Testing, development |
| **Gemini Deep Research** | ✅ Real-time | High-quality URLs | ~$0.10/research | Premium debates |

---

## Verification Process

The system handles both cases:

### With Real URLs (Perplexity)
1. Research → Real sources with URLs
2. Parser → Extracts actual URLs
3. Fact-checker → Verifies real sources
4. Voters → See credible citations

### With Free Models (Fallback)
1. Research → Bibliographic citations
2. Parser → Creates Google Scholar links
3. Fact-checker → Flags as low credibility
4. Voters → Discount unreliable sources

**The fact-checking works correctly in both cases!**

---

## How to Improve Citation Quality

### Option 1: Use Perplexity for Research (Recommended)

Update your `.env`:
```env
# For debator research
PERPLEXITY_MODEL=perplexity/llama-3.1-sonar-large-128k-online

# Keep using free models for other agents if budget-conscious
GEMINI_MODEL=google/gemini-2.0-flash-exp:free  # Debator statements
CLAUDE_MODEL=anthropic/claude-3.5-sonnet:free  # Judge analysis
CROWD_MODEL=meta-llama/llama-3.3-70b-instruct:free  # Crowd voting
```

**Cost**: ~$0.20-0.50 per full debate (research only)

### Option 2: Use Paid Models Throughout

For maximum quality:
```env
GEMINI_MODEL=google/gemini-2.0-flash-thinking-exp  # Deep Research capability
PERPLEXITY_MODEL=perplexity/llama-3.1-sonar-large-128k-online
CLAUDE_MODEL=anthropic/claude-3.5-sonnet
```

**Cost**: ~$1-3 per full debate

### Option 3: Accept Synthetic Citations (Free)

Keep current free model setup:
- Good for testing and development
- Citations are synthetic but topic-relevant
- Fact-checker will appropriately downgrade them
- Voters see "placeholder" warnings

---

## Technical Details

### Citation Parser (`_parse_research_sources`)

The improved parser (v2):
```python
def _parse_research_sources(research_report: str):
    """
    Extracts sources from research report:
    
    1. Looks for "Source List:" section
    2. Parses numbered citations (1. Author. Year. Title...)
    3. Extracts URLs if present (Perplexity provides these)
    4. Falls back to Google Scholar links if no URLs
    5. Preserves bibliographic information
    """
```

**Before (v1)**: Returned single hardcoded placeholder  
**After (v2)**: Parses all sources, creates searchable links

### Source Quality Indicators

Citations now include metadata for quality assessment:
- `source_url`: Actual URL or Google Scholar search
- `title`: Extracted from bibliographic citation
- `content`: Full citation text
- `snippet`: Preview for fact-checking

---

## Examples

### Good Citation (Perplexity)
```json
{
  "citation_key": "a_1",
  "source_url": "https://www.brookings.edu/research/universal-basic-income-2024/",
  "source_title": "Universal Basic Income: A 2024 Analysis",
  "relevant_quote": "UBI pilots showed 24% poverty reduction"
}
```

### Fallback Citation (Free Model)
```json
{
  "citation_key": "a_1",
  "source_url": "https://scholar.google.com/scholar?q=Universal+Basic+Income+Analysis",
  "source_title": "Universal Basic Income: A Comprehensive Study",
  "relevant_quote": "Economic Security Project. (2020). The Cost of UBI."
}
```

Both work, but Perplexity citations are:
- ✅ Verifiable (real URLs)
- ✅ Current (real-time data)
- ✅ More credible (fact-checker scores higher)

---

## Recommendations

### For Production Debates
- ✅ Use Perplexity for research
- ✅ Budget $0.50-1.00 per debate
- ✅ Get real, verifiable citations

### For Development/Testing  
- ✅ Use free models
- ✅ Accept synthetic citations
- ✅ Test debate logic without cost

### For Premium Experience
- ✅ Use Gemini Deep Research
- ✅ Use Claude 3.5 Sonnet (paid)
- ✅ Budget $2-5 per debate
- ✅ Get best possible quality

---

## FAQ

**Q: Why are my citations showing placeholder URLs?**  
A: You're likely using free models without web access. Switch to Perplexity models for real URLs.

**Q: Do the synthetic citations affect debate quality?**  
A: The fact-checker correctly identifies them as low-credibility, so voters can discount them appropriately.

**Q: Can I mix free and paid models?**  
A: Yes! Use Perplexity for research only (~$0.005/call) and free models for everything else.

**Q: How do I verify the parser is working?**  
A: Check `raw_model_calls.jsonl` for research output and `citation_pool.json` for parsed sources.

---

## See Also

- `OPENROUTER_INTEGRATION.md` - OpenRouter setup
- `RAW_DATA_LOGGING.md` - Debugging model calls
- `.env.example` - Model configuration examples
