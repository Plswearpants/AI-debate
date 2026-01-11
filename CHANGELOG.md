# Changelog

All notable changes and bug fixes for the AI Debate Platform.

---

## [Unreleased] - 2026-01-11

### Major Fixes

#### 1. Duplicate Batch Logging
- **Fixed**: Voter calls were logged 11 times (10 individual + 1 batch) instead of once
- **Impact**: Raw logs are now clean and efficient
- **Files**: `src/clients/openrouter_client.py`

#### 2. Citation Parser Rewrite
- **Fixed**: All citations showed placeholder URLs instead of extracting from research
- **Impact**: Citations now properly parsed (22 sources instead of 1 placeholder)
- **Details**: 
  - Free models: Creates Google Scholar search links
  - Perplexity models: Extracts real URLs
- **Files**: `src/agents/debator.py`
- **Docs**: See `CITATION_QUALITY.md` for details

#### 3. Sentiment Graph Generation Error
- **Fixed**: `TypeError: string indices must be integers` in output generation
- **Cause**: Incorrect persona data structure access
- **Files**: `src/moderator.py`

#### 4. Resume Checkpoint Missing Logger
- **Fixed**: `AttributeError: 'DebateModerator' object has no attribute 'raw_data_logger'`
- **Impact**: Debates can now be resumed successfully
- **Files**: `src/moderator.py`

#### 5. Resume Data Loss (CRITICAL)
- **Fixed**: Resume was reinitializing all files, wiping debate data
- **Impact**: Resume now preserves all existing data
- **Solution**: Added phase-skip logic to only run incomplete phases
- **Files**: `src/moderator.py`
- **Warning**: Debates resumed before this fix were corrupted

#### 6. Windows Unicode Errors
- **Fixed**: Emoji characters causing crashes on Windows
- **Files**: `resume_debate.py`, `verify_model_config.py`

### Features Added

#### Raw Data Logging
- Comprehensive logging of all LLM inputs/outputs
- Stored in `debates/<id>/raw_model_calls.jsonl`
- Includes batch calls, model parameters, timestamps
- See `RAW_DATA_LOGGING.md` for details

#### Citation Quality Documentation
- New guide explaining citation behavior with different models
- Recommendations for production vs development
- Model comparison and cost analysis
- See `CITATION_QUALITY.md`

#### Improved JSON Parsing
- Robust parser handles markdown-wrapped JSON
- Fallback regex for score extraction
- Handles free model response inconsistencies
- Files: `src/utils/json_parser.py`

### Configuration Updates

#### Voter Scoring Scheme
- Clarified 1-100 scale (1-50 AGAINST, 51-100 FOR)
- Updated prompts to explicitly communicate scheme
- Added sub-ranges and important notes
- Files: `src/agents/crowd.py`

#### Model Configuration
- All hardcoded models removed
- Full `.env` configuration support
- Perplexity model for research configurable
- See `DEPLOYMENT_GUIDE.md` for setup

---

## System Status

### Working Features ✅
- Complete debate flow (initialization → closing)
- Multi-agent coordination (6 agents)
- OpenRouter integration (200+ models)
- Cost tracking and budget controls
- Checkpoint/resume functionality
- Comprehensive logging (events + raw data)
- Citation management
- Fact-checking with adversarial comments
- Crowd voting with diverse personas
- Output generation (transcripts, graphs, JSON)

### Known Limitations
1. **Citation Quality**: Free models generate synthetic citations (expected behavior)
2. **Model Adherence**: Free models may not perfectly follow structured output requests
3. **Rate Limits**: Free tier models subject to rate limiting

### Recommended Setup
- **Production**: Use Perplexity models for research (~$0.50/debate)
- **Development**: Free models work fine for testing
- **Budget**: Set `DEBATE_BUDGET_USD` in `.env` for cost controls

---

## Migration Guide

### From Corrupted Debates
If you have debates corrupted by the resume bug (before 2026-01-11):
1. The data cannot be recovered (files were overwritten)
2. Raw logs (`raw_model_calls.jsonl`) still exist but processed data is lost
3. **Solution**: Run fresh debates with the fixes applied

### Testing Fixes
```bash
# Test full debate
python run_debate.py "Should UBI be implemented?" 2

# Test resume
# 1. Start debate and kill mid-way (Ctrl+C)
# 2. Resume with: python resume_debate.py <debate-id>
# 3. Verify all data preserved
```

---

## Technical Details

### Phase Skip Logic
Resume now checks current phase before executing:
```python
phase_order = ["initialization", "opening", "debate_rounds", "closing", "completed"]
current_phase_index = phase_order.index(self.state.phase.value)

if current_phase_index < 1:
    await self._phase_0_initialization()  # Only if not done
# ...etc
```

### Citation Parsing
Improved regex-based parser extracts bibliographic citations:
- Finds "Source List:" section in research reports
- Parses numbered citations (1. Author. Year. Title...)
- Extracts titles and URLs
- Creates Google Scholar links if no URL present

### Batch Logging
Prevents duplicate logs by temporarily disabling individual logging:
```python
# Disable individual logging
original_agent = self._current_agent
self._current_agent = None

# Run batch
results = await asyncio.gather(*tasks)

# Log batch once
self._current_agent = original_agent
self.raw_data_logger.log_batch_call(...)
```

---

## Contributors

- AI Debate Platform Team
- Date: January 2026

---

## See Also

- `CITATION_QUALITY.md` - Citation quality guide
- `RAW_DATA_LOGGING.md` - Troubleshooting with raw logs
- `DEPLOYMENT_GUIDE.md` - Setup and configuration
- `ARCHITECTURE.md` - System design
