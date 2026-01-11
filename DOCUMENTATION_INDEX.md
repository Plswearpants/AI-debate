# 📚 Documentation Index

**Quick navigation for all project documentation.**

---

## 🚀 Getting Started

| File | Purpose | Read When |
|------|---------|-----------|
| **[README.md](README.md)** | Main entry point with quick start | First time here |
| **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** | Complete setup guide (all options) | Ready to deploy |
| **[CHANGELOG.md](CHANGELOG.md)** | Recent fixes and improvements | After updating code |

---

## 🏗️ Architecture & Design

| File | Purpose |
|------|---------|
| **[ARCHITECTURE.md](ARCHITECTURE.md)** | System design and data flow |
| **[MVP.md](MVP.md)** | Product specification and requirements |
| **[ROADMAP.md](ROADMAP.md)** | Development timeline and future plans |

---

## 🤖 Implementation Details

| File | Purpose |
|------|---------|
| **[AGENTS_COMPLETE.md](AGENTS_COMPLETE.md)** | All 6 agent implementations |
| **[MODERATOR_COMPLETE.md](MODERATOR_COMPLETE.md)** | Orchestration engine details |
| **[COST_CONTROLS.md](COST_CONTROLS.md)** | Budget management system |

---

## 📖 User Guides

| File | Purpose |
|------|---------|
| **[CITATION_QUALITY.md](CITATION_QUALITY.md)** | Understanding citations with different models |
| **[RAW_DATA_LOGGING.md](RAW_DATA_LOGGING.md)** | Troubleshooting with raw LLM logs |
| **[LOGGING_GUIDE.md](LOGGING_GUIDE.md)** | Debate logging system documentation |

---

## 🔧 Technical Reference

| File | Purpose |
|------|---------|
| **[ADAPTER_INTERFACE_SPEC.md](ADAPTER_INTERFACE_SPEC.md)** | OpenRouter adapter specifications |

---

## 📝 Configuration

| File | Purpose |
|------|---------|
| `.env.example` | Environment configuration template |
| `requirements.txt` | Python dependencies |
| `.gitignore` | Git exclusions |

---

## 🧪 Testing & Debugging

| Script | Purpose |
|--------|---------|
| `test_openrouter.py` | Test OpenRouter connection and models |
| `verify_model_config.py` | Verify model configuration |
| `view_debate_log.py` | View high-level debate events |
| `view_raw_calls.py` | View raw LLM interaction logs |

---

## 🎮 Execution Scripts

| Script | Purpose |
|--------|---------|
| `run_debate.py` | Start a new debate |
| `resume_debate.py` | Resume from checkpoint |

---

## 📂 Directory Structure

```
AI-debate/
├── src/                       # Source code
│   ├── agents/               # Agent implementations
│   ├── clients/              # API clients
│   ├── utils/                # Utilities
│   ├── config.py             # Configuration management
│   └── moderator.py          # Orchestration engine
├── tests/                     # Test suite
├── debates/                   # Generated debate data (gitignored)
│   └── <debate-id>/
│       ├── outputs/          # Human-readable outputs
│       ├── *.json            # Structured data
│       └── *.jsonl           # Log files
├── docs/                      # Additional documentation
├── *.md                       # Core documentation
├── .env                       # Your configuration (gitignored)
├── .env.example              # Configuration template
└── requirements.txt          # Dependencies
```

---

## 🔍 Finding What You Need

### "I want to..."

**...set up the platform** → [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)  
**...understand the architecture** → [ARCHITECTURE.md](ARCHITECTURE.md)  
**...improve citation quality** → [CITATION_QUALITY.md](CITATION_QUALITY.md)  
**...debug a failed debate** → [RAW_DATA_LOGGING.md](RAW_DATA_LOGGING.md)  
**...see recent changes** → [CHANGELOG.md](CHANGELOG.md)  
**...understand agents** → [AGENTS_COMPLETE.md](AGENTS_COMPLETE.md)  
**...control costs** → [COST_CONTROLS.md](COST_CONTROLS.md)  
**...customize models** → [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md#configuration)  

### "I'm getting..."

**..."placeholder" citations** → [CITATION_QUALITY.md](CITATION_QUALITY.md)  
**...rate limit errors** → [CHANGELOG.md](CHANGELOG.md#known-limitations)  
**...checkpoint errors** → [CHANGELOG.md](CHANGELOG.md#major-fixes)  
**...configuration errors** → Run `python verify_model_config.py`  

---

## 📌 Essential Reading

For first-time users, read in this order:

1. **[README.md](README.md)** - Overview and quick start
2. **[DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)** - Complete setup
3. **[CITATION_QUALITY.md](CITATION_QUALITY.md)** - Understanding model behavior
4. **[ARCHITECTURE.md](ARCHITECTURE.md)** - How it works (optional)

---

## 🆕 Recent Documentation (Jan 2026)

- ✅ **[CHANGELOG.md](CHANGELOG.md)** - Consolidated bug fixes and improvements
- ✅ **[CITATION_QUALITY.md](CITATION_QUALITY.md)** - New guide on citation behavior
- ✅ **[RAW_DATA_LOGGING.md](RAW_DATA_LOGGING.md)** - Troubleshooting guide
- ✅ **Updated [README.md](README.md)** - Current status and streamlined docs

---

## 📧 Contributing to Documentation

When adding documentation:

1. **Use clear, descriptive titles**
2. **Add to this index** in appropriate section
3. **Cross-reference related docs**
4. **Include examples where relevant**
5. **Keep technical reference separate from guides**

---

**Last Updated**: January 2026  
**Maintained by**: AI Debate Platform Team
