# Quick Start Guide

Get the Intelligent Document Assistant running in 5 minutes.

## Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- API keys:
  - Anthropic Claude API key (from https://console.anthropic.com)
  - Pinecone API key (from https://app.pinecone.io)

## Step 1: Clone & Enter Directory

```bash
cd "Intelligent Document Assistant"
```

## Step 2: Create Virtual Environment

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

## Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

*This takes 2-3 minutes depending on internet speed*

## Step 4: Setup Environment Variables

```bash
# Copy example to .env
cp .env.example .env

# Edit .env with your credentials
# Required:
# - ANTHROPIC_API_KEY
# - PINECONE_API_KEY
# - PINECONE_ENVIRONMENT
# - AWS_ACCESS_KEY_ID (optional)
# - AWS_SECRET_ACCESS_KEY (optional)
```

## Step 5: Start API Server

```bash
python -m uvicorn src.api.main:app --reload --host 127.0.0.1 --port 8000
```

**Output:**
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

**Access the API:**
- API Server: `http://127.0.0.1:8000`
- Interactive Documentation: `http://127.0.0.1:8000/docs`
- ReDoc Documentation: `http://127.0.0.1:8000/redoc`

## Step 6: Test the System

### Option A: Using curl (Command Line)

```bash
# 1. Check health
curl http://127.0.0.1:8000/health

# 2. Upload a sample document
curl -X POST http://127.0.0.1:8000/upload \
  -F "file=@path/to/your/document.pdf"

# 3. Ask a question
curl -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the main points?", "stream": false}'
```

### Option B: Using Interactive API (Browser)

1. Go to: `http://127.0.0.1:8000/docs`
2. Use Swagger UI to:
   - Upload documents
   - Submit queries
   - View responses

### Option C: Using Python

Create `test_api.py`:

```python
import requests
import json

BASE_URL = "http://127.0.0.1:8000"

# Check health
response = requests.get(f"{BASE_URL}/health")
print("Health:", response.json())

# Upload document
with open("sample.pdf", "rb") as f:
    files = {"file": f}
    response = requests.post(f"{BASE_URL}/upload", files=files)
    print("Upload:", response.json())

# Ask question
query_data = {
    "query": "What are the main findings?",
    "stream": False
}
response = requests.post(
    f"{BASE_URL}/query",
    json=query_data
)
print("Answer:", response.json())
```

Run: `python test_api.py`

## Next Steps

1. **Read the Documentation**
   - [README.md](#) - Project overview
   - [SETUP_DOCUMENTATION.md](#) - Complete guide
   - [IMPLEMENTATION_DETAILS.md](#) - Technical details

2. **Try Different Scenarios**
   - Upload research papers
   - Upload contracts
   - Ask multi-turn questions

3. **Customize**
   - Adjust chunk size in `.env`
   - Change embedding model
   - Add new document types

4. **Deploy**
   - Docker: See SETUP_DOCUMENTATION.md
   - Cloud: AWS, Render, Fly.io

## Troubleshooting

### Error: "ModuleNotFoundError: No module named 'anthropic'"

```bash
# Reinstall dependencies
pip install --upgrade -r requirements.txt
```

### Error: "ANTHROPIC_API_KEY not found"

```bash
# Make sure .env file exists and has the key
cat .env | grep ANTHROPIC_API_KEY
```

### Error: "Connection to Pinecone failed"

```bash
# Verify credentials in .env
# Check Pinecone dashboard for correct environment
# Make sure index exists in Pinecone
```

### API returning 503 "Service Unavailable"

```bash
# Pinecone or Claude API not properly configured
# Check /health endpoint for service status
curl http://127.0.0.1:8000/health
```

## Common Use Cases

### 1. Upload and Analyze a PDF

```bash
# Upload
curl -X POST http://127.0.0.1:8000/upload \
  -F "file=@research_paper.pdf"

# Query
curl -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What methodology was used?"}'
```

### 2. Get Conversation History

```bash
curl http://127.0.0.1:8000/memory
```

### 3. Clear Memory and Start Fresh

```bash
curl -X POST http://127.0.0.1:8000/reset
```

### 4. Stream Responses

```bash
curl -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What are the findings?", "stream": true}'
```

## Performance Tips

1. **Faster Document Processing**
   - Keep `CHUNK_SIZE` reasonable (1000-2000)
   - Use `CHUNK_OVERLAP` of 10-20%

2. **Faster Queries**
   - Query is answered from top-5 documents by default
   - Increase `TOP_K_RETRIEVAL` for broader search

3. **Better Answers**
   - More specific queries get better results
   - Long documents = more chunks = better coverage

## Need Help?

1. Check health endpoint: `GET /health`
2. Read error messages carefully
3. Check API documentation: `GET /docs`
4. Review SETUP_DOCUMENTATION.md
5. Check logs in terminal for detailed errors

## API Reference (Quick)

| Endpoint | Method | Body |
|----------|--------|------|
| `/health` | GET | - |
| `/upload` | POST | `form-data: file` |
| `/query` | POST | `{"query": "...", "stream": false}` |
| `/memory` | GET | - |
| `/reset` | POST | - |
| `/docs` | GET | - |

---

**Ready to go!** 🚀

Your AI Document Assistant is now running and ready to process your documents.
