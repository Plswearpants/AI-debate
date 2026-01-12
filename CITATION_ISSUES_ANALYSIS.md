# Citation Issues Analysis

## Problem Identified

When analyzing raw debator input/output, several critical citation mapping issues were discovered.

---

## Issues Found

### 1. **Single Source Fallback** ⚠️ CRITICAL
**Problem**: Research report contains multiple numbered citations [1], [2], [3], [4], [5], [6] referencing different studies, but only ONE source was provided to the LLM.

**Root Cause**: 
- `_parse_research_sources()` only looks for "Source List:" section
- Research reports from free models don't include this section
- Parser falls back to creating ONE generic source
- LLM correctly uses [a_1] for everything because that's all that's available

**Impact**:
- All claims cite the same generic Google Scholar link
- Fact-checkers can't verify which specific study each claim comes from
- Different studies (Stockton pilot, Roosevelt Institute, Pew Research) all get the same citation
- Makes fact-checking meaningless

**Example from Raw Log**:
```json
"citations": [{
  "citation_key": "a_1",
  "source_url": "https://scholar.google.com/scholar?q=universal+basic+income",
  "source_title": "Research compilation on topic",
  "relevant_quote": "More than 150 guaranteed income pilot programs... Stockton's pilot... Roosevelt Institute... Pew Research..."
}]
```
All different sources cited as the same!

---

### 2. **Citation Number Mismatch**
**Problem**: Research findings use [1], [2], [3] but prompt mapping wasn't explicit enough.

**Root Cause**:
- Research report: "150 pilot programs [1]"
- Prompt shows: "[Source 1] → Use as [a_1]"
- LLM should map: [1] → [a_1], [2] → [a_2], etc.
- But mapping wasn't explicit, causing confusion

**Impact**:
- LLM might use wrong citation numbers
- Or use same citation for multiple sources

---

### 3. **Inconsistent Citation Usage in Research**
**Problem**: Research report uses same citation number [1] for multiple different sources.

**Example**:
- [1] used for: "150 pilot programs", "$2.35 billion", "Austin, Texas", "Stockton, California"
- [5] also used for: "Stockton's pilot program", "Alaska program", "administrative issues"

**Root Cause**: Free models generate research without proper source attribution - they use citation numbers inconsistently.

**Impact**:
- Even with improved parser, can't perfectly separate sources
- Some sources will still be conflated

---

### 4. **Missing Source Context**
**Problem**: When parser extracts citations, it doesn't have enough context to identify what each citation refers to.

**Example**:
- Research says: "Stockton's pilot program [5]"
- Parser needs to know [5] = Stockton, not just "citation 5"

**Impact**:
- Sources get generic titles like "Research Source 5"
- Can't create meaningful search queries
- Fact-checkers can't verify specific claims

---

## Fixes Applied

### 1. **Improved Citation Parser** ✅
**File**: `src/agents/debator.py` - `_parse_research_sources()`

**Changes**:
- Now extracts numbered citations [1], [2], [3] from report body (not just source list)
- Extracts context around each citation to identify what it refers to
- Creates separate sources for each citation number
- Identifies common sources (Stockton, Roosevelt Institute, Pew, etc.) from context
- Creates searchable URLs for each source

**Result**: Multiple sources extracted instead of one fallback.

### 2. **Explicit Citation Mapping** ✅
**File**: `src/agents/debator.py` - `_build_user_prompt()`

**Changes**:
- Added explicit mapping instructions: "[1] → [a_1], [2] → [a_2], etc."
- Emphasized that each distinct source should get its own citation
- Added warning: "Do NOT use the same citation [a_1] for multiple different sources"
- Shows context snippet for each source to help LLM identify them

**Result**: Clear mapping from research citations to debate citations.

---

## Remaining Limitations

### 1. **Free Model Research Quality**
Free models generate research with:
- Inconsistent citation numbering
- Same number used for multiple sources
- No proper source list
- Generic citations

**Solution**: Use Perplexity models for research to get:
- Real URLs with citations
- Proper source attribution
- Verifiable claims

### 2. **Citation Number Reuse**
Even with improved parser, if research uses [1] for multiple different things, we can't perfectly separate them.

**Mitigation**: 
- Parser extracts context around each citation
- Creates separate sources when possible
- But some conflation may remain

### 3. **Context Extraction Limitations**
Parser uses regex to find context, which may:
- Miss some citations
- Extract wrong context
- Create duplicate sources

**Mitigation**:
- Multiple extraction methods (forward and reverse patterns)
- Fallback to generic source if can't identify
- At least creates multiple sources instead of one

---

## Expected Improvements

### Before Fix
- **1 source** extracted (fallback)
- All claims cite same generic link
- Fact-checking impossible

### After Fix
- **6+ sources** extracted (one per citation number)
- Each source has context to identify it
- Better mapping instructions for LLM
- Fact-checkers can verify specific claims

### Still Not Perfect
- Some citation numbers may still be conflated
- Generic Google Scholar links (not real URLs)
- But MUCH better than before

---

## Testing Recommendations

### Test Citation Extraction
```bash
# Run a debate and check citation_pool.json
python run_debate.py "Test topic" 1

# Check if multiple sources were extracted
cat debates/<debate-id>/citation_pool.json | grep -c "source_url"
# Should show 6+ sources, not just 1
```

### Test Citation Mapping
```bash
# Check raw model calls to see if LLM uses different citations
python view_raw_calls.py <debate-id> | grep debator_a

# Look for:
# - Multiple different citation_keys (a_1, a_2, a_3, etc.)
# - Different source_urls for each
# - Proper mapping from research [1], [2] to debate [a_1], [a_2]
```

### Verify Source Quality
```bash
# Check if sources have meaningful titles
cat debates/<debate-id>/citation_pool.json | grep "source_title"
# Should see: "Stockton UBI Pilot", "Roosevelt Institute Analysis", etc.
# Not just: "Research compilation on topic"
```

---

## Best Practices Going Forward

### For Production
1. **Use Perplexity for research** - Gets real URLs and proper citations
2. **Verify citation quality** - Check `citation_pool.json` after each debate
3. **Monitor fact-checker scores** - Low scores may indicate citation issues

### For Development
1. **Accept limitations** - Free models will have citation issues
2. **Use improved parser** - Better than before, but not perfect
3. **Focus on debate logic** - Citations are secondary for testing

---

## Related Files

- `src/agents/debator.py` - Citation extraction and mapping
- `src/agents/factchecker.py` - Citation verification
- `CITATION_QUALITY.md` - Model recommendations for citation quality

---

## Summary

**Fixed**:
- ✅ Parser now extracts multiple sources from numbered citations
- ✅ Explicit citation mapping instructions
- ✅ Context extraction to identify sources

**Remaining Issues**:
- ⚠️ Free models still generate inconsistent citations
- ⚠️ Some citation numbers may be reused for different sources
- ⚠️ Generic URLs instead of real source links

**Recommendation**: Use Perplexity models for research in production to get real, verifiable citations.
