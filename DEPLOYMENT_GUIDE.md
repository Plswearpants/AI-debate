# 🚀 Deployment Guide - Run Your First Debate

**Goal**: Run one complete debate end-to-end with real APIs  

---

## 🎯 Choose Your Setup Path

### **Recommended: OpenRouter Setup** ⭐
- **Time**: 20 minutes
- **Complexity**: Simple (1 API key)
- **Cost**: $0.90-2.50 per debate
- **Best for**: Most users, quick testing, easy management

👉 **See "Quick OpenRouter Setup" section below**

### Alternative: Direct API Setup
- **Time**: 2-3 hours
- **Complexity**: Complex (3-4 API keys)
- **Cost**: $2-3 per debate
- **Best for**: Advanced users, need Gemini Deep Research specifically

Continue reading below for direct API setup instructions.

---

## 📋 Pre-Deployment Checklist (OpenRouter)

### What You'll Need

1. ✅ **API Key** (1 provider only!)
   - [ ] OpenRouter API key (covers all models)

2. ✅ **Development Environment**
   - [ ] Python 3.11+
   - [ ] Git
   - [ ] Text editor / IDE
   - [ ] Terminal access

3. ✅ **Budget Allocation**
   - [ ] ~$10-20 for OpenRouter credits

### Quick OpenRouter Setup

```bash
# 1. Get API key from https://openrouter.ai/keys
# 2. Create .env file:
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# 3. Test it:
python test_openrouter.py

# 4. Run debate:
python run_debate.py "Your topic"
```

**That's it!** Continue reading this guide for details.

---

## 📋 Pre-Deployment Checklist (Direct APIs)

**Note**: Only follow this if you specifically need direct API access.

### What You'll Need

1. ✅ **API Keys** (3-4 providers)
   - [ ] Google Gemini API key (or use OpenRouter)
   - [ ] Anthropic Claude API key (or use OpenRouter)
   - [ ] Perplexity AI API key (or use OpenRouter)
   - [ ] Lambda GPU endpoint (optional)

2. ✅ **Development Environment**
   - [ ] Python 3.11+
   - [ ] Git
   - [ ] Text editor / IDE
   - [ ] Terminal access

3. ✅ **Budget Allocation**
   - [ ] ~$10-20 for API credits (testing + first debates)
   - [ ] Lambda GPU credits (if using Lambda Labs)

---

## 🔑 Option A: OpenRouter Setup (Recommended)

**See above** for complete OpenRouter setup steps.

### Quick Steps

1. **Get OpenRouter Key** (5 min)
   - Go to [OpenRouter](https://openrouter.ai/)
   - Sign up and add $10-20 credits
   - Copy API key from [Keys page](https://openrouter.ai/keys)

2. **Create `.env` + `config.yaml`** (2 min)
   ```bash
   # .env (keys only)
   OPENROUTER_API_KEY=sk-or-v1-your-key-here

   # config.yaml (runtime settings)
   models:
     debator: google/gemini-2.0-flash-exp:free
     judge: anthropic/claude-3.5-sonnet
     factchecker: perplexity/llama-3.1-sonar-large-128k-online
     crowd: meta-llama/llama-3.1-8b-instruct:free
     use_openrouter_for_crowd: true
   debate:
     num_rounds: 2
   ```

3. **Test Setup** (5 min)
   ```bash
   pip install -r requirements.txt
   python test_openrouter.py
   ```

4. **Run Debate** (10 min)
   ```bash
   python run_debate.py "Should universal basic income be implemented?"
   ```

**Done!** Skip to [Step 5: Run Your First Debate](#step-5-run-your-first-debate)

---

## 🔑 Option B: Direct API Setup (Advanced)

**Only if you need direct API access or Gemini Deep Research specifically.**

### Step 1: Obtain API Keys

### 1.1 Google Gemini API (Optional with OpenRouter)

**Purpose**: Powers debaters with Deep Research

**Steps**:
1. Go to [Google AI Studio](https://aistudio.google.com/app/apikey)
2. Sign in with Google account
3. Click "Get API Key" → "Create API Key"
4. Copy the key (starts with `AIza...`)
5. **Important**: Ensure you have access to:
   - `gemini-1.5-pro` model
   - `deep-research-pro-preview-12-2025` agent (Interactions API)

**Pricing**:
- Gemini 1.5 Pro: $3.50/1M input tokens, $10.50/1M output tokens
- Deep Research: ~$0.08 per research (includes grounding + thinking)
- **Budget**: $5-10 should cover 50+ debates

**Test it**:
```bash
curl https://generativelanguage.googleapis.com/v1/models/gemini-1.5-pro:generateContent?key=YOUR_KEY \
  -H 'Content-Type: application/json' \
  -d '{"contents":[{"parts":[{"text":"Hello"}]}]}'
```

---

### 1.2 Anthropic Claude API

**Purpose**: Powers the neutral judge

**Steps**:
1. Go to [Anthropic Console](https://console.anthropic.com/)
2. Sign up / Sign in
3. Go to "API Keys" section
4. Click "Create Key"
5. Copy the key (starts with `sk-ant-...`)

**Pricing**:
- Claude 3.5 Sonnet: $3/1M input tokens, $15/1M output tokens
- **Budget**: $5 should cover 50+ debates (judge uses ~2k tokens per turn)

**Test it**:
```bash
curl https://api.anthropic.com/v1/messages \
  -H "x-api-key: YOUR_KEY" \
  -H "anthropic-version: 2023-06-01" \
  -H "content-type: application/json" \
  -d '{"model":"claude-3-5-sonnet-20241022","max_tokens":100,"messages":[{"role":"user","content":"Hello"}]}'
```

---

### 1.3 Perplexity AI API

**Purpose**: Powers fact-checkers with web-grounded verification

**Steps**:
1. Go to [Perplexity Settings](https://www.perplexity.ai/settings/api)
2. Sign in to Perplexity account
3. Click "Generate API Key"
4. Copy the key (starts with `pplx-...`)

**Pricing**:
- Sonar Pro: $5/1000 requests (model), $5/1000 searches (grounding)
- **Budget**: $5-10 should cover 50+ debates (~8 fact-checks per debate)

**Test it**:
```bash
curl https://api.perplexity.ai/chat/completions \
  -H "Authorization: Bearer YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model":"sonar-pro","messages":[{"role":"user","content":"Hello"}]}'
```

---

### 1.4 Lambda GPU / Llama Server

**Purpose**: Powers the crowd agent (100 persona batch voting)

**Option A: Lambda Labs GPU (Recommended)**

**Steps**:
1. Go to [Lambda Labs](https://lambdalabs.com/)
2. Sign up for Cloud account
3. Add credits ($50-100 recommended)
4. Launch an instance:
   - GPU: RTX 4090 or A6000 (cheapest options)
   - Image: "PyTorch" or "CUDA"
   - Region: Any available
5. SSH into instance
6. Deploy Llama server (see Step 3 below)

**Pricing**:
- RTX 4090: ~$0.50/hour ($12/day if running 24/7)
- A6000: ~$0.80/hour
- **Tip**: Only run when needed, shutdown after debates

**Option B: Other GPU Providers**

Alternatives if Lambda is unavailable:
- **RunPod**: Similar pricing, good availability
- **Vast.ai**: Cheapest option, but variable quality
- **Together AI**: Hosted API (easiest, but more expensive)
- **Local GPU**: If you have RTX 3090/4090

**Option C: Use OpenAI Instead (Temporary)**

For initial testing, you can use OpenAI's API instead of Lambda:
- Model: `gpt-4o-mini` (fast + cheap for crowd voting)
- Cost: ~$0.15/1M tokens
- Modify `src/clients/lambda_client.py` to use OpenAI endpoint

---

## 🛠️ Step 2: Environment Setup

### 2.1 Install Dependencies

```bash
cd c:\Users\CAD\Documents\GitHub\AI-debate

# Install Python packages
pip install -r requirements.txt

# Verify installation
python -c "import aiohttp; print('✅ All packages installed')"
```

### 2.2 Create .env File

**Choose based on your setup:**

#### Option A: OpenRouter Setup (Recommended)

Create `.env` in project root:

```bash
# OpenRouter API Key (replaces Gemini, Claude, Perplexity)
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

```yaml
# config.yaml
models:
  use_openrouter_for_crowd: true
  debator: google/gemini-2.0-flash-exp:free
  judge: anthropic/claude-3.5-sonnet
  factchecker: perplexity/llama-3.1-sonar-large-128k-online
  crowd: meta-llama/llama-3.1-8b-instruct:free
debate:
  num_rounds: 2
  crowd_size: 100
  resource_multiplier_threshold: 0.6
budget:
  max_cost_per_debate: 5.0
```

**See**: Full model list at [OpenRouter Models](https://openrouter.ai/models)

#### Option B: Direct API Setup

Create `.env` in project root:

```bash
# API Keys (Direct)
GEMINI_API_KEY=AIza...your-key-here...
CLAUDE_API_KEY=sk-ant-...your-key-here...
PERPLEXITY_API_KEY=pplx-...your-key-here...

# Lambda GPU Endpoint (optional)
LAMBDA_GPU_ENDPOINT=http://your-lambda-ip:8000
LAMBDA_GPU_API_KEY=optional-if-you-set-one
```

```yaml
# config.yaml
models:
  debator: gemini-1.5-pro
  judge: claude-3-5-sonnet-20241022
  factchecker: sonar-pro
  crowd: meta-llama/Llama-3.1-8B-Instruct
debate:
  num_rounds: 2
  crowd_size: 100
  resource_multiplier_threshold: 0.6
generation:
  temperature:
    debator: 0.7
    judge: 0.3
    factchecker: 0.2
    crowd: 0.8
budget:
  max_cost_per_debate: 5.0
```

#### Option C: Hybrid (OpenRouter + Lambda GPU)

```bash
# OpenRouter for most agents
OPENROUTER_API_KEY=sk-or-v1-your-key-here

# Lambda GPU for crowd (better batch performance)
LAMBDA_GPU_ENDPOINT=http://your-lambda-ip:8000
```

```yaml
# config.yaml
models:
  use_openrouter_for_crowd: false
  debator: google/gemini-2.0-flash-exp:free
  judge: anthropic/claude-3.5-sonnet
  factchecker: perplexity/llama-3.1-sonar-large-128k-online
  crowd: meta-llama/Llama-3.1-8B-Instruct
debate:
  num_rounds: 2
  crowd_size: 100
```

**Important**: Add `.env` to `.gitignore` if not already there!

### 2.3 Verify Configuration

#### If using OpenRouter:

```bash
# Test OpenRouter setup
python test_openrouter.py
```

Expected output:
```
✅ PASS - Config
✅ PASS - Gemini
✅ PASS - Claude
✅ PASS - Perplexity
✅ PASS - Lambda
✅ PASS - Files

🎉 ALL TESTS PASSED!
```

**If all tests pass**: Skip to [Step 5: Run Your First Debate](#step-5-run-your-first-debate)

#### If using Direct APIs:

Create a test script `test_config.py`:

```python
from src.config import Config

try:
    config = Config.from_env()
    config.validate()
    print("✅ Configuration valid!")
    
    # Check which APIs are configured
    if hasattr(config, 'openrouter_api_key'):
        print(f"   OpenRouter API: {config.openrouter_api_key[:20]}...")
    else:
        print(f"   Gemini API: {config.gemini_api_key[:20]}...")
        print(f"   Claude API: {config.claude_api_key[:20]}...")
        print(f"   Perplexity API: {config.perplexity_api_key[:20]}...")
    
    print(f"   Lambda GPU: {config.lambda_gpu_endpoint}")
except Exception as e:
    print(f"❌ Configuration error: {e}")
```

Run it:
```bash
python test_config.py
```

---

## 🖥️ Step 3: Deploy Lambda GPU Server (Optional)

**Skip this step if**:
- You're using OpenRouter with `models.use_openrouter_for_crowd: true`
- You're using OpenAI/other hosted API for crowd

**Only needed if**:
- You want cost-effective batch inference for crowd
- You prefer self-hosted models

### 3.1 SSH into Lambda Instance

```bash
ssh ubuntu@your-lambda-ip
```

### 3.2 Install Dependencies

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python and tools
sudo apt install -y python3-pip git

# Install PyTorch (if not pre-installed)
pip3 install torch torchvision torchaudio

# Install vLLM (fast inference server)
pip3 install vllm
```

### 3.3 Download Llama Model

```bash
# Option A: Use HuggingFace CLI
pip3 install huggingface-hub
huggingface-cli login  # Enter your HF token

# Download model (this will take a while - ~16GB)
huggingface-cli download meta-llama/Llama-3.1-8B-Instruct --local-dir ./llama-3.1-8b
```

### 3.4 Start vLLM Server

Create `start_server.sh`:

```bash
#!/bin/bash

python3 -m vllm.entrypoints.openai.api_server \
    --model meta-llama/Llama-3.1-8B-Instruct \
    --host 0.0.0.0 \
    --port 8000 \
    --tensor-parallel-size 1 \
    --max-model-len 4096 \
    --dtype auto \
    --gpu-memory-utilization 0.9
```

Make executable and run:
```bash
chmod +x start_server.sh
./start_server.sh
```

**Keep this terminal open!** The server needs to stay running.

### 3.5 Test Server

From your local machine:

```bash
curl http://your-lambda-ip:8000/v1/models
```

Should return:
```json
{
  "object": "list",
  "data": [
    {
      "id": "meta-llama/Llama-3.1-8B-Instruct",
      "object": "model",
      ...
    }
  ]
}
```

---

## 🧪 Step 4: Integration Testing

### 4.1 Test Your Setup

#### If using OpenRouter:

```bash
# Comprehensive test of all models
python test_openrouter.py
```

This will test:
- ✅ API connection
- ✅ Gemini model (debators)
- ✅ Claude model (judge)
- ✅ Perplexity model (fact-checkers)
- ✅ Llama model (crowd)
- ✅ Batch generation (for 100 personas)

If all tests pass, you're ready! Skip to [Step 5](#step-5-run-your-first-debate).

#### If using Direct APIs:

Create `test_clients.py`:

```python
import asyncio
from src.config import Config
from src.clients.gemini_client import GeminiClient
from src.clients.claude_client import ClaudeClient
from src.clients.perplexity_client import PerplexityClient
from src.clients.lambda_client import LambdaGPUClient

async def test_all_clients():
    config = Config.from_env()
    
    # Test Gemini
    print("Testing Gemini...")
    gemini = GeminiClient(config.gemini_api_key)
    response = await gemini.generate("Say hello in one sentence")
    print(f"✅ Gemini: {response[:50]}...")
    
    # Test Claude
    print("\nTesting Claude...")
    claude = ClaudeClient(config.claude_api_key)
    response = await claude.generate("Say hello in one sentence")
    print(f"✅ Claude: {response[:50]}...")
    
    # Test Perplexity
    print("\nTesting Perplexity...")
    perplexity = PerplexityClient(config.perplexity_api_key)
    response = await perplexity.chat("What is the capital of France?")
    print(f"✅ Perplexity: {response[:50]}...")
    
    # Test Lambda GPU
    print("\nTesting Lambda GPU...")
    lambda_client = LambdaGPUClient(config.lambda_gpu_endpoint)
    health = await lambda_client.health_check()
    print(f"✅ Lambda GPU: {health}")
    response = await lambda_client.generate_single("Say hello")
    print(f"✅ Lambda Response: {response[:50]}...")

if __name__ == "__main__":
    asyncio.run(test_all_clients())
```

Run:
```bash
python test_clients.py
```

**Expected output**:
```
Testing Gemini...
✅ Gemini: Hello! I'm an AI assistant...

Testing Claude...
✅ Claude: Hello! How can I help you today?...

Testing Perplexity...
✅ Perplexity: The capital of France is Paris...

Testing Lambda GPU...
✅ Lambda GPU: {'status': 'ok'}
✅ Lambda Response: Hello! Nice to meet you...
```

### 4.2 Test File Manager

Create `test_file_ops.py`:

```python
import os
from pathlib import Path
from src.utils.file_manager import FileManager

# Create test debate directory
test_dir = Path("debates/test-debate")
test_dir.mkdir(parents=True, exist_ok=True)

# Initialize file manager
fm = FileManager(str(test_dir))
fm.initialize_files("test-debate", "Test Topic")

# Test read/write
data = fm.read_for_agent("moderator", "history_chat")
print(f"✅ FileManager: Read {len(data)} keys from history_chat")

# Test citation management
fm.add_citation("a", "test_cite", {
    "source": "Test Source",
    "content": "Test content",
    "url": "http://test.com"
})

citations = fm.read_for_agent("moderator", "citation_pool")
print(f"✅ FileManager: Citations structure looks good")

# Cleanup
import shutil
shutil.rmtree(test_dir)
print("✅ FileManager: All tests passed")
```

Run:
```bash
python test_file_ops.py
```

---

## 🎯 Step 5: Run Your First Debate!

### 5.1 Run the Debate

The debate runner script (`run_debate.py`) is already included in the project.

**Basic usage**:

```python
import asyncio
import sys
from pathlib import Path
from src.moderator import DebateModerator
from src.config import Config

async def run_debate(topic: str):
    """Run a complete debate."""
    print(f"\n{'='*60}")
    print(f"🎭 AI DEBATE PLATFORM")
    print(f"{'='*60}")
    print(f"Topic: {topic}")
    print(f"{'='*60}\n")
    
    # Load config
    config = Config.from_env()
    config.validate()
    print("✅ Configuration loaded and validated\n")
    
    # Create moderator
    moderator = DebateModerator(topic=topic, config=config)
    
    print(f"Debate ID: {moderator.debate_id}")
    print(f"Output directory: debates/{moderator.debate_id}/\n")
    
    # Run the debate!
    try:
        debate_id = await moderator.run_debate()
        
        print(f"\n{'='*60}")
        print(f"✅ DEBATE COMPLETED SUCCESSFULLY!")
        print(f"{'='*60}")
        print(f"Debate ID: {debate_id}")
        print(f"Total Cost: ${moderator.total_cost:.2f}")
        print(f"Total Turns: {moderator.state.turn_count}")
        print(f"\nOutputs generated:")
        print(f"  📄 debates/{debate_id}/outputs/transcript_full.md")
        print(f"  📊 debates/{debate_id}/outputs/citation_ledger.json")
        print(f"  🗺️  debates/{debate_id}/outputs/debate_logic_map.json")
        print(f"  📈 debates/{debate_id}/outputs/voter_sentiment_graph.csv")
        print(f"{'='*60}\n")
        
        return debate_id
        
    except Exception as e:
        print(f"\n❌ Debate failed: {e}")
        print(f"\n💾 Checkpoint may have been saved at:")
        print(f"   debates/{moderator.debate_id}/moderator_checkpoint.json")
        print(f"\nTo resume:")
        print(f"   python resume_debate.py {moderator.debate_id}")
        raise

if __name__ == "__main__":
    # Get topic from command line or use default
    if len(sys.argv) > 1:
        topic = " ".join(sys.argv[1:])
    else:
        topic = "Should universal basic income be implemented?"
    
    asyncio.run(run_debate(topic))
```

### 5.2 Available Commands

**Start the debate**:
```bash
python run_debate.py "Should universal basic income be implemented?"
```

**Or with a custom topic**:
```bash
python run_debate.py "Is artificial intelligence an existential risk to humanity?"
```

**If it crashes, resume it**:
```bash
python resume_debate.py <debate-id>
```

### 5.3 What to Expect

**Timeline** (approximate):
```
[0:00] Phase 0: Initialization
       └─> Vote 0 (1-2 seconds)

[0:02] Phase 1: Opening Statements
       ├─> Debator A: Research (30s-5min depending on setup)
       ├─> FactChecker B: Verify (10-20 seconds)
       ├─> Debator B: Research (30s-5min)
       ├─> FactChecker A: Verify (10-20 seconds)
       ├─> Judge: Analyze (5-10 seconds)
       └─> Crowd: Vote (1-5 seconds)

[~5:00] Phase 2: Round 1 (2-3 minutes)
[~8:00] Phase 2: Round 2 (2-3 minutes)
[~10:00] Phase 3: Closing (30-60 seconds)
[~11:00] Output Generation (1-2 seconds)

Total: ~5-12 minutes (faster with OpenRouter, slower with Deep Research)
```

**Cost breakdown**:

#### With OpenRouter (Free Tier):
```
Vote 0:           $0.00 (free model)
Opening (×2):     $0.00 (Gemini Flash free)
Fact-checks (×4): $0.60 (Perplexity)
Judge (×3):       $0.30 (Claude Sonnet)
Crowd (×3):       $0.00 (Llama free)
--------------------
Total:           ~$0.90 per debate
```

#### With OpenRouter (Premium):
```
Vote 0:           $0.00 (free model)
Opening (×2):     $0.50 (Gemini 1.5 Pro)
Fact-checks (×4): $0.80 (Perplexity Huge)
Judge (×3):       $0.30 (Claude Sonnet)
Crowd (×3):       $0.20 (Llama 70B)
--------------------
Total:           ~$1.80 per debate
```

#### With Direct APIs:
```
Vote 0:           $0.02
Opening (×2):     $0.16 (Gemini Deep Research)
Fact-checks (×4): $0.60
Judge (×3):       $0.75
Crowd (×3):       $0.06
--------------------
Total:           ~$2.60 per debate
```

**OpenRouter saves ~65% cost with free tier!**

---

## 📊 Step 6: Review Outputs

### 6.1 Transcript

Open `debates/<debate-id>/outputs/transcript_full.md`:

```markdown
# Debate Transcript

**Topic**: Should universal basic income be implemented?
**Debate ID**: abc-123-def-456
**Date**: 2026-01-10 16:30:00 UTC

---

## Round 1 - debator_a (opening)

Universal Basic Income (UBI) represents a transformative solution to...

[Comprehensive opening statement with citations]

---

## Round 1 - debator_b (opening)

While UBI may seem appealing, the economic reality tells a different story...

[Counter-arguments with citations]

---

[... Full debate continues ...]
```

### 6.2 Citation Ledger

Open `debates/<debate-id>/outputs/citation_ledger.json`:

```json
{
  "debate_id": "abc-123",
  "citations": {
    "team a": {
      "cite_a_1": {
        "source": "Stanford Basic Income Study",
        "content": "Pilot program showed 23% reduction in poverty...",
        "url": "https://...",
        "verification": {
          "source_credibility_score": 9,
          "content_correspondence_score": 8,
          "adversary_comment": "Credible source, accurate data",
          "verified_by": "factchecker_b"
        }
      }
    },
    "team b": { ... }
  }
}
```

### 6.3 Logic Map

Open `debates/<debate-id>/outputs/debate_logic_map.json`:

Shows how consensus and disagreement evolved across rounds.

### 6.4 Sentiment Graph

Open `debates/<debate-id>/outputs/voter_sentiment_graph.csv`:

Import into Excel/Python to visualize how voters changed opinions over time.

---

## 🐛 Troubleshooting

### Common Issues

#### 1. "API Key Invalid"
**Solution**: Double-check keys in `.env`, ensure no extra spaces

#### 2. "Lambda GPU Connection Refused"
**Solutions**:
- Check Lambda instance is running
- Verify port 8000 is open in firewall
- Test with `curl http://your-lambda-ip:8000/v1/models`
- Check vLLM server logs

#### 3. "Deep Research Not Available"
**Solution**: Ensure you're using `gemini-1.5-pro` and have access to Interactions API

#### 4. "Out of Memory" (Lambda GPU)
**Solutions**:
- Use smaller max_model_len (2048 instead of 4096)
- Reduce gpu-memory-utilization to 0.8
- Upgrade to larger GPU (A6000 or A100)

#### 5. "Debate Crashes Midway"
**Solution**: Just resume it!
```bash
python resume_debate.py <debate-id>
```
Checkpoints save after every expensive operation, so you won't lose much.

#### 6. "Rate Limit Exceeded"
**Solutions**:
- Wait a few minutes and retry
- Add retry logic with exponential backoff
- Upgrade API tier if needed

---

## 💰 Cost Management

### Monitor Costs in Real-Time

The moderator tracks costs automatically:
```
💾 Checkpoint saved (Total: $0.10)
💾 Checkpoint saved (Total: $0.92)
💾 Checkpoint saved (Total: $1.87)
```

### Set Budget Limits

In `.env`:
```bash
COST_BUDGET_PRESET=conservative  # Max $2/debate
# or
COST_BUDGET_PRESET=balanced     # Max $5/debate
# or
COST_BUDGET_PRESET=premium       # Max $15/debate
```

### Reduce Costs

**Option 1**: Use fewer debate rounds
```yaml
debate:
  num_rounds: 1  # Instead of 2
```

**Option 2**: Use cheaper models for crowd
- Replace Lambda GPU with `gpt-4o-mini` (cheaper)

**Option 3**: Use conservative budget preset
```bash
COST_BUDGET_PRESET=conservative
```

---

## 🚀 Production Deployment (Optional)

### For Running Many Debates

**Option A: Docker Compose**

Create `docker-compose.yml`:
```yaml
version: '3.8'

services:
  lambda-gpu:
    image: vllm/vllm-openai:latest
    ports:
      - "8000:8000"
    command: ["--model", "meta-llama/Llama-3.1-8B-Instruct"]
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  debate-api:
    build: .
    ports:
      - "5000:5000"
    environment:
      - LAMBDA_GPU_ENDPOINT=http://lambda-gpu:8000
    env_file:
      - .env
    depends_on:
      - lambda-gpu
```

**Option B: Kubernetes**

For high availability and scaling (advanced).

**Option C: Serverless**

Deploy each component as serverless function (very advanced).

---

## ✅ Deployment Checklist

### OpenRouter Setup Checklist

Before running your first debate, verify:

- [ ] OpenRouter API key obtained
- [ ] `.env` file created with `OPENROUTER_API_KEY`
- [ ] Models selected in `.env` file
- [ ] `pip install -r requirements.txt` completed
- [ ] `python test_openrouter.py` passes all tests ✅
- [ ] Ready to run: `python run_debate.py "Your Topic"`

**Estimated time**: 20 minutes  
**Estimated cost**: $0.90-1.80 per debate

### Direct API Setup Checklist

Before running your first debate, verify:

- [ ] All 3-4 API keys obtained and tested
- [ ] Lambda GPU server deployed (if using)
- [ ] `.env` file created with all keys
- [ ] `pip install -r requirements.txt` completed
- [ ] All unit tests passing (`pytest tests/unit/`)
- [ ] All clients tested
- [ ] Ready to run: `python run_debate.py "Your Topic"`

**Estimated time**: 2-3 hours  
**Estimated cost**: $2-3 per debate

---

## 🎉 Success Criteria

Your deployment is successful when:

1. ✅ Debate completes all 4 phases
2. ✅ All 4 output files generated
3. ✅ Cost tracking shows expected range
4. ✅ Transcript is coherent and well-structured
5. ✅ Citations are properly verified
6. ✅ Voter sentiment data looks reasonable

---

## 🆚 Setup Comparison

### OpenRouter vs Direct APIs

| Aspect | OpenRouter ⭐ | Direct APIs |
|--------|--------------|-------------|
| **API Keys** | 1 key | 3-4 keys |
| **Setup Time** | 20 minutes | 2-3 hours |
| **Complexity** | Simple | Complex |
| **Cost (Free Tier)** | $0.90/debate | Not available |
| **Cost (Premium)** | $1.80/debate | $2.60/debate |
| **Billing** | Unified dashboard | Multiple dashboards |
| **Model Switching** | Easy (edit .env) | Requires code changes |
| **Maintenance** | Single provider | Multiple providers |
| **Best For** | Most users | Advanced users |

### When to Use OpenRouter

✅ You want simplest setup  
✅ You're testing the system  
✅ You prefer unified billing  
✅ You want flexibility to switch models  
✅ You don't need Gemini Deep Research specifically  

**Recommendation**: Start with OpenRouter, switch to direct APIs only if needed!

### When to Use Direct APIs

Use direct APIs only if:
- You specifically need Gemini Deep Research agent
- You need absolute lowest latency (50-100ms difference)
- You have existing provider credits to use
- You need provider-specific features

---

## 📞 Need Help?

### Common Resources

**OpenRouter**:
- Website: https://openrouter.ai/
- Models: https://openrouter.ai/models
- Docs: https://openrouter.ai/docs
- Discord: https://discord.gg/openrouter

**Direct APIs** (if needed):
- Google Gemini Docs: https://ai.google.dev/gemini-api/docs
- Anthropic Claude Docs: https://docs.anthropic.com/
- Perplexity API Docs: https://docs.perplexity.ai/
- vLLM Docs: https://docs.vllm.ai/

### Debugging

- Check `debates/<debate-id>/moderator_checkpoint.json` for state
- Check terminal logs for detailed error messages
- Run with Python debugger: `python -m pdb run_debate.py`
- Test setup: `python test_openrouter.py` (OpenRouter) or `python test_clients.py` (Direct)

---

## 🚀 Ready to Launch!

### **Recommended Path: OpenRouter** ⭐

1. ✅ Get API key from [OpenRouter](https://openrouter.ai/keys)
2. ✅ Create `.env` with `OPENROUTER_API_KEY`
3. ✅ Run `python test_openrouter.py`
4. ✅ Run `python run_debate.py "Your topic"`
5. ✅ Review outputs and celebrate! 🎉

**Time**: 20 minutes | **Cost**: $0.90-1.80/debate

### Alternative Path: Direct APIs

1. ✅ Get 3-4 API keys from providers
2. ✅ Deploy Lambda GPU (optional)
3. ✅ Create `.env` with all keys
4. ✅ Run `python test_clients.py`
5. ✅ Run `python run_debate.py "Your topic"`

**Time**: 2-3 hours | **Cost**: $2.60/debate

---

You now have everything you need to run your first AI debate. The system is production-ready with:
- ✅ Crash recovery via checkpoints
- ✅ Real-time cost tracking
- ✅ Comprehensive logging
- ✅ Quality outputs

**Let's make history with AI-moderated debates!** 🎭⚖️🤖
