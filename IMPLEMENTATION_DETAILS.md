# Implementation Details

**Document Created**: February 15, 2026

This file provides in-depth implementation details for each component of the Intelligent Document Assistant.

---

## Table of Contents
1. [Document Processing](#document-processing)
2. [Vector Database Integration](#vector-database-integration)
3. [RAG Pipeline](#rag-pipeline)
4. [Agent Orchestration](#agent-orchestration)
5. [API Implementation](#api-implementation)
6. [Data Flow](#data-flow)

---

## Document Processing

### DocumentLoader - File Type Support

```python
# Supported formats
PDF    → PyPDF2 library
DOCX   → python-docx library
TXT    → Native Python file I/O
PPTX   → python-pptx library
```

**File Structure Returned**:
```python
Document(
    content: str,          # Full extracted text
    filename: str,         # Original filename
    format: str,          # File extension
    metadata: {
        "file_path": str,
        "file_size": int
    }
)
```

**Error Handling**:
- File not found → Returns None
- Unsupported format → Logs error, returns None
- Read errors → Graceful exception handling with logging

### TextChunker - Overlap Strategy

Two chunking methods implemented:

**1. Character-based Chunking** (Default)
```
Document: "AAAA BBBB CCCC DDDD EEEE"
chunk_size = 4, overlap = 2

Result:
- Chunk 1: "AAAA BB" (chars 0-6)
- Chunk 2: "BB CCCC" (chars 4-10)  ← 2 char overlap
- Chunk 3: "CCCC DD" (chars 8-14)  ← 2 char overlap
```

**2. Sentence-based Chunking** (Intelligent)
```
Preserves sentence boundaries
Prevents splitting mid-sentence
Better for readability and context
```

**Metadata Per Chunk**:
```python
{
    "start_index": int,         # Position in original text
    "end_index": int,           # End position
    "character_count": int,     # Chunk size
    "sentence_count": int       # (Sentence-based only)
}
```

---

## Vector Database Integration

### Embedding Generation Pipeline

```
Text Input
    ↓
Sentence-Transformers (all-MiniLM-L6-v2)
    ↓
384-dimensional Vector
    ↓
Stored in Pinecone with Metadata
```

**Model Choice Rationale**:
```
all-MiniLM-L6-v2:
- Only 22M parameters (lightweight)
- 384-dimensions (balanced: speed ↔ accuracy)
- MTEB benchmark: Top performer in semantic similarity
- Inference: ~100 docs/sec on CPU
- Memory: Fits on any GPU
```

### Pinecone Operations

**Upsert (Create/Update)**:
```python
vectors = [
    {
        'id': 'doc_chunk_001',
        'values': [0.1, 0.2, ..., 0.3],  # 384 floats
        'metadata': {
            'source_doc': 'research_paper.pdf',
            'document_id': 'uuid-...',
            'chunk_id': 0,
            'text': 'chunk content...',
            'start_index': 0
        }
    }
]
index.upsert(vectors=vectors)
```

**Search (Semantic Similarity)**:
```
Query: "What methodology was used?"
    ↓
Generate embedding for query (384-dim vector)
    ↓
Find K nearest neighbors in Pinecone
    ↓
Return with similarity scores (0-1)
```

---

## RAG Pipeline

### Retrieval Flow

```
User Query
    ↓
[DocumentRetriever.retrieve()]
    ├─ Generate query embedding
    ├─ Search Pinecone (top_k results)
    └─ Return with similarity scores

Optional: [Reranking with Cross-Encoder]
    ├─ Re-score all retrieved documents
    ├─ Better ranking than semantic similarity alone
    └─ 60% better relevance (according to literature)
```

### Response Generation Flow

```
Retrieved Documents + Query
    ↓
[ResponseGenerator.generate_response()]
    ├─ Build context from document chunks
    ├─ Create system prompt with instructions
    ├─ Call Claude API with max_tokens=2048
    └─ Return formatted answer with citations
```

**Prompt Engineering**:
```python
prompt = """Based on the following document excerpts, answer the user's question. 
If the answer cannot be found in the documents, say so explicitly.
Include references to the source documents when citing information.

Document Context:
{RETRIEVED_CHUNKS_HERE}

User Question: {QUERY}

Please provide a clear, concise answer with citations where applicable."""
```

---

## Agent Orchestration

### LangGraph Workflow

```
State: COMPLETED/ANALYZING
    ↓
[_analyze_query()]
    ├─ Detect question type (factual/explanatory/summarization)
    ├─ Estimate complexity
    └─ State: RETRIEVING

    ↓
[_retrieve_documents()]
    ├─ Execute semantic search
    ├─ Filter by relevance threshold
    └─ State: PROCESSING

    ↓
[_needs_refinement()?]
    ├─ YES → [_refine_query()] → Search again
    │   └─ State: RETRIEVING
    └─ NO → State: GENERATING

    ↓
[_generate_response()]
    ├─ Create prompt with context
    ├─ Call Claude API
    ├─ Stream or full response
    └─ State: COMPLETED

    ↓
[Memory Management]
    ├─ Add to conversation_history
    ├─ Track query_history
    ├─ Store retrieved_documents
    └─ Ready for next query
```

### Query Type Detection

```python
"What methodology was used?"       → factual
"Why did they choose this?"        → explanatory
"Summarize the findings"           → summarization
"Tell me about X"                  → general
```

### Refinement Strategy

```
Refinement triggered when:
- No documents retrieved
- Average relevance score < 0.5

Refinement approach:
- Remove stop words from query
- Focus on key terms
- Re-execute search
```

---

## API Implementation

### FastAPI Application Structure

```python
app = FastAPI()

# Dependency Injection via app.state
@app.on_event("startup")
def initialize():
    app.state.vector_db = PineconeVectorDB(...)
    app.state.agent = DocumentAssistantAgent(...)

# Routes with dependency
@app.post("/upload")
async def upload_document(file: UploadFile):
    # Access via request.app.state.vector_db
```

### Background Processing

```
POST /upload → Async file handling
    ↓
Save to /tmp/{filename}
    ↓
background_tasks.add_task(_process_document, ...)
    ↓
Return immediately with document_id
    ↓
Background: Load → Chunk → Embed → Upsert

User polls status via document_id (future enhancement)
```

### Streaming Responses

```
POST /query?stream=true
    ↓
[StreamingResponse(generate())]
    ├─ Uses FastAPI's StreamingResponse
    ├─ Yields tokens as they arrive from Claude
    └─ HTTP chunked transfer encoding

Client receives real-time tokens:
"What" → "are" → "the" → "findings?"
```

---

## Data Flow Diagram

### End-to-End Query Flow

```
CLIENT
  │
  ├──① POST /upload (file.pdf)
  │    │
  │    └──→ DOCUMENT PROCESSING
  │           ├─ DocumentLoader.load()
  │           ├─ Split large file
  │           └─ Progress: Loading...
  │
  │    └──→ TEXT CHUNKING
  │           ├─ TextChunker.chunk()
  │           ├─ Overlap strategy
  │           └─ Progress: Chunking...
  │
  │    └──→ EMBEDDING GENERATION
  │           ├─ EmbeddingService.embed_texts()
  │           ├─ Batch processing
  │           └─ Progress: Embedding...
  │
  │    └──→ VECTOR STORAGE
  │           ├─ PineconeVectorDB.upsert()
  │           ├─ Store with metadata
  │           └─ Response: document_id
  │
  ├──② POST /query
  │    │
  │    └──→ AGENT ORCHESTRATION
  │           ├─ State: ANALYZING
  │           ├─ Detect question type
  │           └─ State: RETRIEVING
  │
  │    └──→ SEMANTIC RETRIEVAL
  │           ├─ EmbeddingService.embed_text(query)
  │           ├─ PineconeVectorDB.search()
  │           └─ Return: [{id, score, metadata}, ...]
  │
  │    └──→ OPTIONAL: RERANKING
  │           ├─ CrossEncoder scoring
  │           ├─ Re-sort results
  │           └─ State: PROCESSING
  │
  │    └──→ RESPONSE GENERATION
  │           ├─ Build context from chunks
  │           ├─ Create prompt
  │           ├─ Call Claude API
  │           ├─ Format with citations
  │           └─ State: COMPLETED
  │
  └──③ Return Answer
       {
         "query": "What are findings?",
         "answer": "The main finding is...",
         "sources": [
           {"source_doc": "paper.pdf", "chunk_id": 5}
         ]
       }

AGENT MEMORY
  ├─ conversation_history: [{user, assistant}, ...]
  ├─ query_history: ["query1", "query2", ...]
  └─ retrieved_documents: [{...}, ...]
```

---

## Performance Optimizations

### 1. Vector Similarity Search
```
Traditional: Sequential document scan O(n)
Our approach: HNSW index in Pinecone O(log n)

100 documents  → 100 semantic comparisons
1M documents   → ~20 comparisons (same time!)
```

### 2. Batch Embedding
```python
# ❌ Slow: Individual embeddings
for chunk in chunks:
    emb = model.encode(chunk.text)

# ✅ Fast: Batch processing
embeddings = model.encode([c.text for c in chunks])
# 10-50x faster!
```

### 3. Context Window Optimization
```
1000-page document
    ↓
Extract only top-5 relevant chunks (~5KB)
    ↓
Pass to Claude (saves cost + latency)
    ↓
Get answer in 2-3 seconds instead of 30+ seconds
```

### 4. SageMaker Parallelization (Future)
```
Traditional: Process 100 documents sequentially
    Time: 100 × 5 minutes = 500 minutes

SageMaker: Parallel processing
    Time: 5 minutes (100x speedup!)
    
Implementation:
- Distribute documents across multiple instances
- Process in parallel
- Aggregate results
```

---

## Error Handling Strategy

### Level 1: Input Validation
```python
@app.post("/query")
async def query(request: QueryRequest):
    # Pydantic validates:
    # - query is string
    # - stream is boolean
    # - Raises 422 if invalid
```

### Level 2: Component Error Handling
```python
def load_document(path):
    try:
        return self._load_pdf(path)
    except Exception as e:
        logger.error(f"Error: {e}")
        return None  # Graceful degradation
```

### Level 3: API Error Handling
```python
@app.post("/query")
async def query(...):
    try:
        return agent.process(query)
    except Exception as e:
        logger.error(str(e))
        raise HTTPException(500, str(e))
```

### Level 4: Client Error Handling
```python
# Client should implement retry logic
response = requests.post(url, json=data)
if response.status_code == 503:
    # Service temporarily unavailable
    # Implement exponential backoff
```

---

## Monitoring & Logging

### Logging Strategy
```python
import logging

logger = logging.getLogger(__name__)

logger.info("Processing document: research_paper.pdf")
logger.warning("No documents found for query")
logger.error("Pinecone connection failed")
logger.debug("Embedding 1000 chunks...")
```

### Metrics to Track
```
- Documents processed per hour
- Average query latency
- Cache hit rate
- Error rate per endpoint
- API token usage
- Vector DB query time
```

### Health Check Endpoint
```bash
GET /health

Response:
{
  "status": "healthy",
  "services": {
    "vector_db": "ready",
    "agent": "ready",
    "embedding": "ready"
  }
}
```

---

## Security Considerations

### 1. API Key Management
```
✅ Store in .env (never commit)
✅ Use environment variables
❌ Don't hardcode credentials
❌ Don't pass in query parameters
```

### 2. File Upload Validation
```python
# Check file type
if file.content_type not in ALLOWED_TYPES:
    raise HTTPException(400, "Invalid file type")

# Check file size
if file.size > MAX_SIZE:
    raise HTTPException(413, "File too large")

# Scan for malicious content (future)
```

### 3. Query Injection Prevention
```python
# Pydantic validates input types
# SQL injection not applicable (no SQL)
# Prompt injection: Claude API handles safely
```

---

## Testing Strategy

### Unit Tests
```
test_document_processing/
  ├─ test_loader.py (File loading)
  ├─ test_chunker.py (Text splitting)
  └─ test_embeddings.py (Embedding generation)

test_rag_pipeline/
  ├─ test_retriever.py (Document search)
  └─ test_generator.py (Response generation)

test_agent/
  └─ test_agent.py (Orchestration)
```

### Integration Tests (Future)
```
test_integration/
  ├─ test_upload_and_query.py
  ├─ test_multi_document.py
  └─ test_memory.py
```

### Load Testing (Future)
```python
# Test with 100 concurrent requests
# Measure: latency, throughput, error rate
# Expected: <2s p99 latency, >50 req/sec
```

---

## Deployment Considerations

### Local Development
```bash
uvicorn src.api.main:app --reload --port 8000
```

### Docker Deployment
```dockerfile
FROM python:3.11-slim
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "src.api.main:app"]
```

### Cloud Deployment
```
Option 1: AWS Lambda + API Gateway
Option 2: ECS with ALB
Option 3: Render/Fly.io
Option 4: Custom VPS with Nginx
```

---

## Future Enhancements

### Near-term
1. **Conversation Refinement**: Multi-turn dialogue with context
2. **Document Metadata**: Filter by date, author, topic
3. **Analytics Dashboard**: Query history, performance metrics

### Medium-term
1. **Multi-model Support**: GPT-4, Llama, etc.
2. **Fine-tuning**: Custom embeddings for domain knowledge
3. **Caching**: Redis for frequently asked questions

### Long-term
1. **Visual Document Processing**: Tables, diagrams, images
2. **Real-time Indexing**: Update embeddings as docs change
3. **Collaboration Features**: Share documents and conversations

---

**Last Updated**: February 15, 2026
**Status**: Complete implementation guide ready
