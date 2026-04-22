# Quick Setup Guide for API Key Testing

## 🚀 Testing Your Inference Script with a Real LLM

### Step 1: Create your .env file

```bash
# Copy the example file
cp .env.example .env
```

### Step 2: Edit .env and add your API key

Open `.env` in a text editor and update:

```bash
# For OpenAI API (recommended - cheapest option)
API_BASE_URL=https://api.openai.com/v1
MODEL_NAME=gpt-4o-mini
HF_TOKEN=sk-your-openai-api-key-here

# OR for HuggingFace
API_BASE_URL=https://api-inference.huggingface.co/v1
MODEL_NAME=meta-llama/Llama-3.2-1B-Instruct
HF_TOKEN=hf_your-huggingface-token-here
```

### Step 3: Make sure the server is running

```bash
cd envs/data_cleaning_env/server
python -m uvicorn app:app --host 0.0.0.0 --port 7860
```

Leave this running in one terminal.

### Step 4: Run inference in another terminal

```bash
cd D:\META-HACKATHON\data-cleaning-openenv
python inference.py
```

### Expected Output Format

You should see structured logs like this:

```
[START] task=easy env=data-cleaning-env model=gpt-4o-mini
[STEP] step=1 action=fill_missing('age',30) reward=0.30 done=false error=null
[STEP] step=2 action=fix_type('score',None) reward=0.20 done=false error=null
...
[END] success=true steps=10 score=0.930 rewards=0.30,0.20,0.15,...

[START] task=medium env=data-cleaning-env model=gpt-4o-mini
...
```

## 💰 Cost Estimates (OpenAI gpt-4o-mini)

- ~30-50 steps per task × 3 tasks = ~100-150 LLM calls
- Each call: ~500 tokens input + 50 tokens output
- Total: ~60K tokens
- Cost: **$0.01 - $0.02** (very cheap!)

## 🧪 Testing Without API Key

If you don't have an API key yet, you can test the logging format with:

```bash
python test_inference_format.py
```

This uses rule-based actions (no LLM) and validates the exact output format.

## ✅ What to Check

1. **Logging format is correct**:
   - [START] has: task, env, model
   - [STEP] has: step, action, reward (2 decimals), done (lowercase), error
   - [END] has: success (lowercase), steps, score (3 decimals), rewards (comma-separated)

2. **All 3 tasks complete successfully**

3. **Scores are in [0.0, 1.0] range**

4. **No API errors** (check your key is valid)

## 🐛 Troubleshooting

**"Server not running" error:**
```bash
# Make sure server is started:
cd envs/data_cleaning_env/server
python -m uvicorn app:app --host 0.0.0.0 --port 7860
```

**"Invalid API key" error:**
- Check .env file has correct HF_TOKEN
- Verify your API key is active
- Try a different model if rate-limited

**"Module not found" error:**
```bash
pip install python-dotenv openai requests fastapi uvicorn pydantic
```

## 📊 Expected Scores

Based on LLM quality:
- **Easy task**: 0.85 - 0.95
- **Medium task**: 0.80 - 0.90
- **Hard task**: 0.75 - 0.85
- **Average**: 0.80 - 0.90

Lower scores are fine - the format compliance is what matters most!
