# Frontend & Backend Connection Guide

This guide shows how to connect and run the Intelligent Document Assistant frontend with the backend API.

## 🚀 Quick Start (Both Together)

### Step 1: Open Two Terminals

You need **two separate terminal windows**.

### Step 2: Terminal 1 - Start the Backend API

```bash
# Navigate to project directory
cd "C:\Users\Shobhit Raj\Documents\Projects\Intelligent Document Assistant"

# Activate virtual environment
& "./venv/Scripts/Activate.ps1"

# Start the API server
python -m uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000
```

**Expected Output:**
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

### Step 3: Terminal 2 - Open the Frontend

**Option A: Double-click the file**
1. Navigate to: `C:\Users\Shobhit Raj\Documents\Projects\Intelligent Document Assistant`
2. Find `index.html`
3. Double-click it to open in your browser

**Option B: Open via URL in browser**
```
file:///C:/Users/Shobhit%20Raj/Documents/Projects/Intelligent%20Document%20Assistant/index.html
```

---

## ✅ Verify Connection

1. **Check Backend Health**
   - Open new browser tab
   - Go to: `http://localhost:8000/health`
   - You should see JSON response with status

2. **Check Frontend**
   - The index.html should load without errors
   - You should see the purple gradient UI
   - Check browser console (F12) for any errors

3. **Test Upload**
   - Click upload area in left sidebar
   - Select a PDF/DOCX file
   - You should see upload success message

---

## 🔧 Troubleshooting

### "Cannot connect to API" Error

**Problem:** Frontend shows error message about connecting to API

**Causes & Solutions:**

1. **Backend not running**
   - Check Terminal 1 is still running
   - Should show "Uvicorn running on..."
   - If stopped, restart it with uvicorn command

2. **Port 8000 already in use**
   - Close any other programs using port 8000
   - Or change port and update frontend:
     ```javascript
     // In index.html, line 271:
     const API_BASE = 'http://localhost:9000';  // Change to different port
     ```

3. **CORS issues**
   - Make sure backend has CORS enabled (we added it)
   - Check browser console for CORS errors
   - API should accept requests from file:// URLs

### Upload Failed

**Problem:** Document won't upload

**Check:**
1. Backend is running (Terminal 1)
2. File is correct format (PDF, DOCX, TXT, PPTX)
3. File is not too large
4. Check browser console (F12) for error details
5. Check backend terminal for error messages

### No Response After Asking Question

**Problem:** Spinner keeps loading, no answer

**Check:**
1. API key configured in `.env`
   - `ANTHROPIC_API_KEY` for Claude
   - `PINECONE_API_KEY` for vector database
2. Backend logs for errors
3. Upload at least one document first
4. Check browser console for network errors

---

## 📋 Full Architecture

```
Your Computer
├─ Frontend (index.html)
│  └─ Opens in your browser
│  └─ Sends requests to localhost:8000
│
└─ Backend (FastAPI)
   └─ Terminal 1 runs `python -m uvicorn ...`
   └─ Listens on port 8000
   └─ Processes requests
   └─ Returns responses to frontend
```

---

## 🌐 What Happens When You Upload a Document

```
1. Frontend: User clicks upload, selects file
   ↓
2. Frontend: Sends file to POST http://localhost:8000/upload
   ↓
3. Backend: Receives file, loads document
   ↓
4. Backend: Chunks text into pieces
   ↓
5. Backend: Generates embeddings for chunks
   ↓
6. Backend: Stores in Pinecone vector database
   ↓
7. Backend: Returns success with file_id
   ↓
8. Frontend: Shows "Upload successful" message
```

---

## 🎯 What Happens When You Ask a Question

```
1. Frontend: User types question and clicks Send
   ↓
2. Frontend: Sends to POST http://localhost:8000/query
   ↓
3. Backend: Receives query
   ↓
4. Backend: Searches Pinecone for relevant documents
   ↓
5. Backend: Gets top 5 matching chunks
   ↓
6. Backend: Sends to Claude API with context
   ↓
7. Claude: Analyzes documents and generates answer
   ↓
8. Backend: Returns answer to frontend
   ↓
9. Frontend: Displays answer in chat
```

---

## 🔐 Security Notes

For **development only**, the backend has CORS enabled for all origins. For production:

1. Restrict CORS origins:
   ```python
   app.add_middleware(
       CORSMiddleware,
       allow_origins=["https://yourdomain.com"],  # Specific domain
       ...
   )
   ```

2. Configure proper authentication
3. Use HTTPS
4. Validate all inputs
5. Limit file upload sizes

---

## 📊 Monitoring

**Backend Terminal Shows:**
- All incoming requests
- Processing status
- Errors and warnings
- API response times

**Browser Console (F12) Shows:**
- Network requests/responses
- JavaScript errors
- Frontend log messages
- CORS issues

---

## 🆘 Common Issues Reference

| Issue | Solution |
|-------|----------|
| "Cannot connect to API" | Restart backend in Terminal 1 |
| "Port 8000 in use" | Find process using port 8000, close it, or change port |
| "No documents uploaded" | Upload a file first before asking questions |
| "Pinecone connection error" | Check PINECONE_API_KEY in .env |
| "Anthropic API error" | Check ANTHROPIC_API_KEY in .env |
| "File upload fails" | Check file format (PDF, DOCX, TXT, PPTX) |
| "CORS error in console" | Make sure backend is running and CORS middleware is added |

---

## 🎓 Learning Resources

**Frontend Code:**
- `index.html` - Entire frontend (HTML, CSS, JavaScript)
- Simple fetch() API calls to backend
- No build tools or dependencies needed

**Backend Code:**
- `src/api/main.py` - FastAPI endpoints
- `src/vector_db/` - Vector database and embeddings
- `src/rag_pipeline/` - Retrieval and generation logic
- `src/agent_orchestration/` - Agent orchestration

---

**Everything is working correctly when:**
✅ Backend shows "Application startup complete"
✅ Frontend loads without errors
✅ Upload succeeds
✅ Questions return answers
✅ Memory button shows conversation history

Enjoy using your Intelligent Document Assistant! 🎉
