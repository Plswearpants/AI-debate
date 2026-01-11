# AI Debate Platform

An AI-driven debate platform that simulates high-fidelity, text-based argumentation between AI agents on complex social topics.

**Status**: ✅ **Stable** | Recent fixes applied (Jan 2026) | Ready for testing

---

## ⚡ Quick Start

### Option 1: OpenRouter (Recommended - Easiest Setup)

```bash
# 1. Get API key: https://openrouter.ai/keys (free tier available)

# 2. Create .env file:
echo "OPENROUTER_API_KEY=sk-or-v1-your-key-here" > .env
echo "USE_OPENROUTER_FOR_CROWD=true" >> .env
echo "GEMINI_MODEL=google/gemini-2.0-flash-exp:free" >> .env
echo "CLAUDE_MODEL=anthropic/claude-3.5-sonnet:free" >> .env
echo "PERPLEXITY_MODEL=perplexity/llama-3.1-sonar-small-128k-online" >> .env
echo "CROWD_MODEL=meta-llama/llama-3.3-70b-instruct:free" >> .env
echo "NUM_DEBATE_ROUNDS=2" >> .env
echo "NUM_VOTERS=10" >> .env

# 3. Install dependencies
pip install -r requirements.txt

# 4. Test configuration
python test_openrouter.py

# 5. Run your first debate!
python run_debate.py "Should universal basic income be implemented?"
```

### Option 2: Direct API Keys (More Control)

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for setup with individual API keys (Gemini, Claude, Perplexity).

---

## 🎯 What It Does

The AI Debate Platform simulates structured debates with:

- **2 Debating Teams** (for/against) with research capabilities
- **Fact-Checking** of citations by opposing teams
- **Neutral Judge** analyzing arguments and mapping disagreements
- **Diverse Crowd** of 10-100 voters with different perspectives
- **Comprehensive Outputs**: Transcripts, logic maps, sentiment graphs, citation ledgers

**Use Cases:**
- Explore complex policy questions
- Test argument quality
- Study persuasion dynamics
- Generate balanced analysis on controversial topics

---

## 🏗️ Architecture

### Multi-Agent System (6 Agent Types)

```
Phase 0: Initialization
└─ Crowd votes on stance preference → Team assignment

Phase 1: Opening Statements
├─ Debator A: Research + Opening (with citations)
├─ FactChecker B: Verify A's citations
├─ Debator B: Research + Opening (with citations)
├─ FactChecker A: Verify B's citations
├─ Judge: Analyze arguments, map disagreements
└─ Crowd: Vote (based on opening statements)

Phase 2: Debate Rounds (2x by default)
├─ [FactChecker checks previous citations]
├─ Debator A: Rebuttal with new research
├─ FactChecker B: Verify new citations
├─ Debator B: Counter-rebuttal
├─ FactChecker A: Verify
├─ Judge: Update disagreement frontier
└─ Crowd: Vote (track opinion shifts)

Phase 3: Closing
├─ Judge: Final analysis
└─ Crowd: Final vote

Phase 4: Outputs
└─ Generate transcripts, graphs, JSON summaries
```

### Key Features

✅ **OpenRouter Integration** - 200+ models, single API key  
✅ **Cost Controls** - Budget limits, cost tracking  
✅ **Checkpoint/Resume** - Recover from failures without re-running  
✅ **Comprehensive Logging** - Event logs + raw LLM call logs  
✅ **Citation Management** - Source tracking with fact-checking  
✅ **Adversarial Fact-Checking** - Opponents verify each other's sources  
✅ **Diverse Voter Personas** - 10 archetypes (political, professional, demographic)  
✅ **Structured Outputs** - JSON, Markdown, CSV for analysis

---

## 📊 Sample Output

After running a debate, you'll find in `debates/<debate-id>/outputs/`:

- **`transcript_full.md`** - Complete debate transcript
- **`debate_logic_map.json`** - Structured argument analysis
- **`citation_ledger.json`** - All sources with verification scores
- **`voter_sentiment_graph.csv`** - Opinion shifts over time

Plus internal files:
- `history_chat.json` - Full debate history
- `citation_pool.json` - Citation database
- `crowd_opinion.json` - Voter data with personas
- `debate_log.jsonl` - Event log
- `raw_model_calls.jsonl` - All LLM interactions (for debugging)

---

## 🔧 Configuration

### Environment Variables (`.env`)

**Essential:**
```env
OPENROUTER_API_KEY=sk-or-v1-...      # Required: OpenRouter API key
```

**Models (all optional, defaults to free tier):**
```env
GEMINI_MODEL=google/gemini-2.0-flash-exp:free
CLAUDE_MODEL=anthropic/claude-3.5-sonnet:free
PERPLEXITY_MODEL=perplexity/llama-3.1-sonar-small-128k-online
CROWD_MODEL=meta-llama/llama-3.3-70b-instruct:free
```

**Debate Settings:**
```env
NUM_DEBATE_ROUNDS=2                  # Number of rebuttal rounds (default: 2)
NUM_VOTERS=10                        # Crowd size (default: 10)
DEBATE_BUDGET_USD=5.00               # Max cost per debate (default: 5.00)
```

**Advanced:**
```env
USE_OPENROUTER_FOR_CROWD=true        # Use OpenRouter for crowd (recommended)
DEEP_RESEARCH_ENABLED=true           # Enable research phase (default: true)
```

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for complete configuration options.

---

## 📚 Documentation

### Getting Started
- **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Complete setup guide (all deployment options)
- **[CHANGELOG.md](CHANGELOG.md)** - Recent fixes and changes

### Technical Reference
- **[ARCHITECTURE.md](ARCHITECTURE.md)** - System design and data flow
- **[AGENTS_COMPLETE.md](AGENTS_COMPLETE.md)** - Agent implementation details
- **[MODERATOR_COMPLETE.md](MODERATOR_COMPLETE.md)** - Orchestration engine

### Guides
- **[CITATION_QUALITY.md](CITATION_QUALITY.md)** - Understanding citation behavior with different models
- **[RAW_DATA_LOGGING.md](RAW_DATA_LOGGING.md)** - Troubleshooting with raw LLM logs
- **[LOGGING_GUIDE.md](LOGGING_GUIDE.md)** - Debate logging system
- **[COST_CONTROLS.md](COST_CONTROLS.md)** - Budget management

### API Specs
- **[ADAPTER_INTERFACE_SPEC.md](ADAPTER_INTERFACE_SPEC.md)** - OpenRouter adapter specifications

### Planning
- **[MVP.md](MVP.md)** - Product specification
- **[ROADMAP.md](ROADMAP.md)** - Future development plans

### Index
- **[DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)** - Complete documentation map

---

## 🚀 Usage Examples

### Basic Debate
```bash
python run_debate.py "Should universal basic income be implemented?"
```

### Longer Debate (more rounds)
```bash
# Set NUM_DEBATE_ROUNDS=5 in .env
python run_debate.py "Should we ban social media for children under 16?" 5
```

### Resume Failed Debate
```bash
# If a debate crashes or is interrupted
python resume_debate.py <debate-id>
```

### View Debate Logs
```bash
# High-level events
python view_debate_log.py <debate-id>

# Or view most recent
python view_debate_log.py last

# Raw LLM calls (for debugging)
python view_raw_calls.py <debate-id>
```

### Verify Configuration
```bash
# Check which models are configured
python verify_model_config.py
```

---

## 🐛 Known Issues & Limitations

### Citation Quality with Free Models
- **Issue**: Free models generate synthetic citations (no real web access)
- **Impact**: Citations get Google Scholar links instead of real URLs
- **Solution**: Use Perplexity models for research (~$0.005/call)
- **Status**: ⚠️ Expected behavior (not a bug)
- **Docs**: See [CITATION_QUALITY.md](CITATION_QUALITY.md)

### Rate Limiting
- **Issue**: Free tier models have rate limits
- **Impact**: Debates may pause briefly between calls
- **Solution**: Use paid tier models or add delays
- **Status**: ⚠️ API limitation

### Structured Output Adherence
- **Issue**: Some free models wrap JSON in markdown code blocks
- **Impact**: Parser handles it (robust JSON extraction)
- **Solution**: Use paid models for perfect adherence
- **Status**: ✅ Handled by parser

---

## 🔍 Recent Improvements (Jan 2026)

See [CHANGELOG.md](CHANGELOG.md) for complete details:

✅ **Fixed**: Duplicate batch logging (voter calls)  
✅ **Fixed**: Citation parser rewrite (extracts all sources)  
✅ **Fixed**: Sentiment graph generation error  
✅ **Fixed**: Resume checkpoint missing logger  
✅ **Fixed**: Resume overwriting debate data (CRITICAL)  
✅ **Fixed**: Windows Unicode errors  
✅ **Added**: Raw data logging for all LLM calls  
✅ **Added**: Citation quality documentation  
✅ **Improved**: Robust JSON parsing for LLM responses  

---

## 🧪 Testing

### Run Test Suite
```bash
# All tests
pytest tests/ -v

# Specific test file
pytest tests/test_moderator.py -v
```

### Integration Tests
```bash
# Quick test (1 round)
python run_debate.py "Test topic" 1

# Full test (resume functionality)
# 1. Start debate
python run_debate.py "Test topic" 2
# 2. Kill it mid-debate (Ctrl+C)
# 3. Resume
python resume_debate.py <debate-id>
# 4. Verify data preserved
```

---

## 💰 Cost Estimates

### Free Tier (Development)
- **Cost**: $0.00
- **Models**: All free tier models
- **Limitations**: Synthetic citations, rate limits
- **Use Case**: Testing, development

### Budget Tier (Production)
- **Cost**: ~$0.50-1.00 per debate
- **Models**: Perplexity for research, free for others
- **Benefits**: Real citations, better quality
- **Use Case**: Production debates

### Premium Tier
- **Cost**: ~$2.00-5.00 per debate
- **Models**: Paid tier for all agents
- **Benefits**: Best quality, no rate limits
- **Use Case**: High-stakes analysis

---

## 🤝 Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/YourFeature`)
3. Make your changes with tests
4. Run the test suite (`pytest tests/ -v`)
5. Commit your changes (`git commit -am 'Add YourFeature'`)
6. Push to the branch (`git push origin feature/YourFeature`)
7. Create a Pull Request

See [ARCHITECTURE.md](ARCHITECTURE.md) for system design details.

---

## 📝 License

[Add your license here]

---

## 🙋 Support

### Common Issues

**Q: Citations show placeholder URLs?**  
A: You're using free models without web access. Use Perplexity models for real URLs. See [CITATION_QUALITY.md](CITATION_QUALITY.md).

**Q: Debate failed with "string indices must be integers"?**  
A: This was a bug fixed in Jan 2026. Update to latest version.

**Q: Resume overwrote my debate data?**  
A: This critical bug was fixed in Jan 2026. Update to latest version. Corrupted debates cannot be recovered.

**Q: Rate limit errors?**  
A: Free tier models have limits. Add delays or use paid tier.

**Q: Which models should I use?**  
A: For development: all free tier. For production: Perplexity for research, free for others. See [CITATION_QUALITY.md](CITATION_QUALITY.md).

### Debugging

1. **Check configuration**: `python verify_model_config.py`
2. **View event logs**: `python view_debate_log.py <debate-id>`
3. **View raw LLM calls**: `python view_raw_calls.py <debate-id>`
4. **Read documentation**: Check [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)

---

## 🎓 Academic Context

This platform implements:
- **Multi-agent argumentation** with adversarial dynamics
- **Citation verification** through cross-examination
- **Crowd simulation** with diverse ideological perspectives
- **Disagreement frontier mapping** (identifying core contested issues)
- **Opinion dynamics** tracking over debate progression

Potential research applications:
- Argument quality assessment
- Persuasion dynamics
- Fact-checking automation
- Opinion formation modeling
- Deliberative AI systems

---

## 🔮 Roadmap

See [ROADMAP.md](ROADMAP.md) for future development plans.

**Upcoming:**
- Web interface
- Debate comparison tools
- Custom voter personas
- Multi-turn fact-checking
- Argument graph visualization
- Real-time debates

---

## ⭐ Credits

AI Debate Platform Team  
January 2026

**Built with:**
- OpenRouter (unified LLM access)
- Google Gemini (debators with research)
- Anthropic Claude (neutral judge)
- Perplexity (fact-checking with web search)
- Meta Llama (crowd simulation)

---

## 📬 Contact

[Add your contact information or links here]

---

**Ready to start?** → [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)  
**Need help?** → [DOCUMENTATION_INDEX.md](DOCUMENTATION_INDEX.md)  
**Found a bug?** → [CHANGELOG.md](CHANGELOG.md)
