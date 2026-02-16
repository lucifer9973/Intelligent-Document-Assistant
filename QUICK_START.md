# Quick Start Guide

## 30-Second Setup

### 1. Start Backend (Terminal 1)
```bash
cd "C:\Users\Shobhit Raj\Documents\Projects\Intelligent Document Assistant"
.\venv\Scripts\Activate.ps1
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### 2. Open Frontend (Browser)
```
http://localhost:8000
```

You should see a purple gradient interface with:
- Left sidebar: Upload area, document list, Memory/Reset buttons
- Right side: Chat interface

---

## Basic Workflow

### Step 1: Upload a Document
1. Click the upload area or drag-and-drop a file
2. Supported formats: PDF, DOCX, TXT, PPTX
3. Wait for "✓ Successfully uploaded" message

### Step 2: Ask a Question
1. Type a question in the chat input box
2. Click Send or press Enter
3. Wait for response (3-5 seconds)

### Step 3: View Memory (Optional)
1. Click "📋 Memory" button
2. See all past questions and answers
3. Click X or outside to close

### Step 4: Reset (Optional)
1. Click "🔄 Reset" button
2. Confirm in popup
3. Conversation history cleared

---

## Troubleshooting

### Backend won't start
```
Error: No module named uvicorn
→ Solution: Make sure venv is activated
".\venv\Scripts\Activate.ps1"
```

### Can't access http://localhost:8000
```
Error: ERR_ADDRESS_INVALID at 0.0.0.0:8000
→ Solution: Use localhost, not 0.0.0.0
Correct: http://localhost:8000
```

### "Credit balance too low" error
```
Error: Your credit balance is too low to access the Anthropic API
→ Solution: Add credits at https://console.anthropic.com/account/billing/overview
→ Purchase credits and refresh the page
```

### File upload failing (old issue, now fixed)
```
Error: No such file or directory: '/tmp/...'
→ Solution: Already fixed - using tempfile.gettempdir()
```

---

## Testing the System

### Quick Health Check
```bash
# Any terminal
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "healthy", "services": {"vector_db": "ready", "agent": "ready", "embedding": "ready"}}
```

### Upload Test File
```bash
# In PowerShell
$file = Get-Item "test_document.txt"
curl -X POST -H "Content-Type: multipart/form-data" `
  -F "file=@test_document.txt" `
  http://localhost:8000/upload
```

### Query Test
```bash
curl -X POST -H "Content-Type: application/json" `
  -d '{"query":"What is in the document?","stream":false}' `
  http://localhost:8000/query
```

---

## Features Explained

### Upload & Processing
- Files are automatically chunked into searchable segments
- Chunks are converted to 1536-dimensional vectors
- Vectors stored in Pinecone for semantic search

### Query & Response
- Question converted to vector
- Similar document chunks retrieved from Pinecone
- Claude AI generates response based on retrieved chunks

### Memory System
- Every question and answer is tracked
- Memory viewer shows conversation history
- Reset clears all conversation data

### CORS & Frontend
- Backend serves the HTML directly
- No separate frontend server needed
- All requests made from same origin (localhost:8000)

---

## File Organization

### Important Files
- `index.html` - Web UI (access at http://localhost:8000)
- `src/api/main.py` - API backend
- `.env` - Configuration (API keys)
- `requirements.txt` - Python dependencies

### To Access Logs
- Backend terminal shows all API calls and errors
- Browser console (F12) shows frontend errors

---

## Configuration

### API Keys in .env
```env
ANTHROPIC_API_KEY=sk-...         # Required for AI responses
PINECONE_API_KEY=pcsk_...        # Required for vector database
PINECONE_INDEX_NAME=llama-text-embed-v2-index
```

### To Change Port
Edit the startup command:
```bash
# Change 8000 to your port
python -m uvicorn src.api.main:app --port 9000
# Then access: http://localhost:9000
```

---

## Common Tasks

### Upload a PDF
1. Open http://localhost:8000
2. Click "📄 Click to upload or drag & drop"
3. Select a PDF file
4. Wait for success message

### Ask about your document
1. Type: "What is the main topic?"
2. Press Enter
3. Claude will analyze and respond

### See what was asked before
1. Click "📋 Memory" button
2. Scroll through past conversations
3. Click X to close

### Start over
1. Click "🔄 Reset" button
2. Confirm "Are you sure?"
3. All data cleared, ready for new documents

---

## Next Steps

1. ✓ Backend is running
2. ✓ Frontend is accessible
3. ✓ All tests passed
4. ➜ Upload your first document
5. ➜ Ask your first question
6. ➜ Add Anthropic credits if needed

---

## Get Help

### Check Logs
1. Backend terminal: See API calls and errors
2. Browser console (F12): See JavaScript errors

### Review Documentation
- `SYSTEM_READY.md` - Full system status
- `CONNECTION_GUIDE.md` - Connection troubleshooting
- `TROUBLESHOOTING.md` - Known issues and fixes

### Verify Setup
```bash
# All these should return 200 OK:
curl http://localhost:8000/health
curl http://localhost:8000/
curl http://localhost:8000/memory
```

---

## That's It!

Your Intelligent Document Assistant is ready to use.

**Access:** http://localhost:8000

Happy document analyzing! 📚🤖
