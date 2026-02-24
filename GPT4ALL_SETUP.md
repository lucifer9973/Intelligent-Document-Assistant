# GPT4All Model Installation & Integration Guide

This document details the steps taken to install a GPT4All-compatible local LLM model and integrate it into the Intelligent Document Assistant project, eliminating the need for external API keys.

## ✅ Status: COMPLETE

The local LLM is now fully operational and tested!

## Overview

The project now supports local LLM inference using:
- **llama-cpp-python**: Python bindings for GGML/GGUF models  
- **Model**: Meta's Llama 3.2 1B Instruct (quantized Q4_0)
- **Model Size**: 729.75 MB

---

## Step 1: Install Required Python Packages

### Install gpt4all package
```
bash
pip install gpt4all
```

### Install llama-cpp-python (for local LLM inference)
```
bash
pip install llama-cpp-python
```

Note: llama-cpp-python compiles from source and may take several minutes.

---

## Step 2: Download the Model

### Option A: Using gpt4all Python package (Recommended)

The gpt4all package can automatically download models:

```
python
from gpt4all import GPT4All

# This will download the model automatically
model = GPT4All('Llama-3.2-1B-Instruct-Q4_0')
```

The model will be saved to: `~/.cache/gpt4all/`

### Option B: Manual Download

Download directly from HuggingFace or GPT4All.io:

```
bash
mkdir -p /home/lucifer/models
cd /home/lucifer/models
wget "https://gpt4all.io/models/gguf/Llama-3.2-1B-Instruct-Q4_0.gguf"
```

### Model Location

The downloaded model is located at:
```
/home/lucifer/models/Llama-3.2-1B-Instruct-Q4_0.gguf
```

Model size: ~738MB (quantized Q4_0)

---

## Step 3: Update requirements.txt

Add the following to your `requirements.txt`:

```
txt
# LLM & Agent Orchestration
anthropic>=0.7.1
llama-cpp-python>=0.2.0
```

---

## Step 4: Configure Environment Variable

Set the `LOCAL_LLM_MODEL_PATH` environment variable to point to your model:

### For current session:
```
bash
export LOCAL_LLM_MODEL_PATH=/home/lucifer/models/Llama-3.2-1B-Instruct-Q4_0.gguf
```

### For permanent configuration, add to `.env` file:
```bash
LOCAL_LLM_MODEL_PATH=/home/lucifer/models/Llama-3.2-1B-Instruct-Q4_0.gguf
```

---

## Step 5: Code Modifications

### 5.1 Update config/settings.py

Added local model path configuration:

```
python
class Settings(BaseSettings):
    # ... existing settings ...
    
    # Local LLM Model (GPT4All)
    local_llm_model_path: str = ""
```

### 5.2 Update src/rag_pipeline/generator.py

Modified `ResponseGenerator` class to support local models:

```
python
class ResponseGenerator:
    def __init__(self, api_key: str = "", retriever: DocumentRetriever = None, 
                 model: str = "claude-3-sonnet-20240229",
                 local_model_path: str = ""):
        # ... initialization code ...
        
        # Check if local model is available
        if self.local_model_path and os.path.exists(self.local_model_path):
            self.local_llm = LocalLLM(model_path=self.local_model_path)
            logger.info(f"Initialized local LLM from: {self.local_model_path}")
```

Added local response generation method:

```
python
def _generate_local_response(self, query: str, context_documents: List[Dict] = None,
                           include_citations: bool = True) -> str:
    """Generate response using local LLM (GPT4All)"""
    # ... generates response using local model ...
```

---

## Step 6: Testing the Local Model

### Test from Python REPL:
```
python
import os
os.environ["LOCAL_LLM_MODEL_PATH"] = "/home/lucifer/models/Llama-3.2-1B-Instruct-Q4_0.gguf"

from src.llm.local_model import LocalLLM
llm = LocalLLM()
response = llm.generate("Hello, how are you?")
print(response)
```

### Test via API:
Start the API server:
```
bash
cd /home/lucifer/Documents/Intelligent Document Assistant
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

Then query:
```
bash
curl -X POST http://localhost:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the capital of France?"}'
```

---

## Model Comparison

| Model | Size | RAM Required | Notes |
|-------|------|-------------|-------|
| Llama-3.2-1B-Instruct | 738MB | ~2GB | Current (recommended) |
| Llama-3.2-3B-Instruct | 1.9GB | ~4GB | Better quality |
| GPT4All Falcon | 4.2GB | ~8GB | Original GPT4All model |
| mistral-7b-instruct | 4.1GB | ~8GB | Strong instruction following |

---

## Troubleshooting

### Issue: "libllamamodel-mainline-cuda.so: cannot open shared object"
**Solution**: This is normal if you don't have a CUDA GPU. The model will run on CPU.

### Issue: Model not found
**Solution**: Verify the path:
```
bash
ls -lh /home/lucifer/models/
```

### Issue: Out of memory
**Solution**: Use a smaller model or reduce context size in generator.py

---

## Usage Without API Keys

With the local model configured, you can now:

1. **Query documents** without Anthropic API key
2. **Get AI-powered answers** from local LLM
3. **Use RAG functionality** with retrieved document context

The system will automatically:
1. First try to use local LLM if `LOCAL_LLM_MODEL_PATH` is set
2. Fall back to Anthropic API if API key is provided
3. Use extractive search if neither is available

---

## Files Modified

1. `requirements.txt` - Added llama-cpp-python
2. `config/settings.py` - Added local_llm_model_path setting
3. `src/rag_pipeline/generator.py` - Added local LLM support

## Files Created

- This documentation file (GPT4ALL_SETUP.md)
