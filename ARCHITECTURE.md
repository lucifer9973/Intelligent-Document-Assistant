# System Architecture & Data Flow

This document provides visual representations of how the Intelligent Document Assistant system works.

---

## High-Level System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                          USER / CLIENT                               │
│                    (API Consumer / Browser)                          │
└──────────────────────────┬──────────────────────────────────────────┘
                           │
                   HTTP Requests/Responses
                           │
        ┌──────────────────┴──────────────────┐
        │                                     │
        ▼                                     ▼
    ┌─────────────┐                  ┌──────────────┐
    │   FastAPI   │                  │  Swagger UI  │
    │  (REST API) │                  │   (/docs)    │
    └──────┬──────┘                  └──────────────┘
           │
        Endpoints:
    ┌──────┼──────────────────┬───────┬───────┬─────┐
    │      │                  │       │       │     │
    ▼      ▼                  ▼       ▼       ▼     ▼
 /health /upload            /query /memory /reset /
    │      │                  │       │       │     │
    │      └──────────────────┼───────┼───────┴─────┤
    │                         │       │              │
    └──────────────────┬──────┴───────┴──────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │  Agent Orchestration Layer   │
        │   (DocumentAssistantAgent)   │
        │  - Query Analysis            │
        │  - Workflow Management       │
        │  - Memory Management         │
        └────────┬─────────────┬───────┘
                 │             │
    ┌────────────┘             └─────────────┐
    │                                        │
    ▼                                        ▼
┌──────────────────────┐        ┌──────────────────────┐
│  Document Processing │        │   RAG Pipeline       │
│  - DocumentLoader    │        │  - DocumentRetriever │
│  - TextChunker       │        │  - ResponseGenerator │
└──────────┬───────────┘        └──────┬───────────────┘
           │                           │
           │ Chunks                    │ Retrieved Docs
           │ + Metadata                │ + Query
           ▼                           ▼
        ┌──────────────────────────────────┐
        │   Vector Database Layer          │
        │  - EmbeddingService (ST)         │
        │  - PineconeVectorDB              │
        │    * Upsert                      │
        │    * Search                      │
        │    * Delete                      │
        └──────────┬───────────────────────┘
                   │
                   │  Vector Queries
                   │  Embedding Lookups
                   │
                   ▼
        ┌──────────────────────────┐
        │   External Services      │
        │                          │
        │  1. Pinecone             │
        │     (Vector Database)    │
        │                          │
        │  2. Sentence-Transformers│
        │     (Embeddings)         │
        │                          │
        │  3. Claude API           │
        │     (Response Gen)       │
        │                          │
        │  4. SageMaker (Optional) │
        │     (Scaling)            │
        └──────────────────────────┘
```

---

## Request Flow Diagram

### Document Upload & Processing

```
┌─────────────┐
│   USER      │
│  Uploads    │
│   PDF       │
└──────┬──────┘
       │
       ▼
   ┌───────────┐
   │ FastAPI   │
   │  /upload  │
   └─────┬─────┘
         │
         ├─→ Validate file
         │   (type, size)
         │
         ├─→ Save to /tmp/
         │
         └─→ background_tasks.add_task()
             │
             ├─→ DocumentLoader.load()
             │   ├─ PDF Extract
             │   ├─ Get text
             │   └─ → Document object
             │
             ├─→ TextChunker.chunk()
             │   ├─ Split by size
             │   ├─ Add overlap
             │   └─ → [Chunk, Chunk, ...]
             │
             ├─→ EmbeddingService
             │   ├─ Load ST model
             │   ├─ Embed all chunks
             │   └─ → [Vector, Vector, ...]
             │
             └─→ PineconeVectorDB.upsert()
                 ├─ Create vectors list
                 ├─ Push to Pinecone
                 └─ Response: OK

Client gets: {"status": "success", "document_id": "uuid"}
```

### Query & Answer Flow

```
┌──────────────────┐
│   USER QUERY     │
│  "What is the    │
│   methodology?"  │
└────────┬─────────┘
         │
         ▼
    ┌──────────────┐
    │  FastAPI     │
    │  /query      │
    └───────┬──────┘
            │
            ▼
    ┌─────────────────────────────────────┐
    │  DocumentAssistantAgent.process()   │
    │                                     │
    │  STATE: ANALYZING                   │
    │  ├─ Detect type: explanatory        │
    │  ├─ Estimate complexity             │
    │  ├─ Save to memory                  │
    │  └─→ STATE: RETRIEVING              │
    └─────────────┬───────────────────────┘
                  │
                  ▼
    ┌─────────────────────────────────┐
    │  DocumentRetriever.retrieve()   │
    │                                 │
    │  1. EmbeddingService            │
    │     .embed_text(query)          │
    │     → 384-dim vector            │
    │                                 │
    │  2. PineconeVectorDB            │
    │     .search(vector, top_k=5)    │
    │     → [                         │
    │         {"id": "...",           │
    │          "score": 0.95,         │
    │          "metadata": {...}},    │
    │         ...                     │
    │       ]                         │
    │                                 │
    │  3. (Optional) Reranking        │
    │     CrossEncoder.predict()      │
    │     → Better ranking            │
    └──────────────┬──────────────────┘
                   │
                   ▼
    ┌────────────────────────────────────┐
    │  Agent State Check                 │
    │                                    │
    │  if _needs_refinement():           │
    │    ├─ avg_score < 0.5?  NO        │
    │    ├─ documents_found? YES         │
    │    └─→ Proceed                     │
    │                                    │
    │  STATE: GENERATING                 │
    └────────────────┬───────────────────┘
                     │
                     ▼
    ┌──────────────────────────────────────┐
    │  ResponseGenerator.generate_response()│
    │                                      │
    │  1. Build context string:            │
    │     "[Source: paper.pdf]             │
    │      The methodology used was..."    │
    │                                      │
    │  2. Create prompt with instructions  │
    │     + context + query                │
    │                                      │
    │  3. Call Claude API:                 │
    │     client.messages.create(          │
    │       model="claude-3-sonnet",       │
    │       messages=[{                    │
    │         "role": "user",              │
    │         "content": prompt            │
    │       }]                             │
    │     )                                │
    │                                      │
    │  4. Parse response:                  │
    │     "The methodology section         │
    │      indicates a quantitative        │
    │      approach was employed,          │
    │      as stated in section 2.1        │
    │      of the document."               │
    │                                      │
    │  5. Format with citations:           │
    │     answer + source_references      │
    │                                      │
    │  STATE: COMPLETED                    │
    └──────────────┬───────────────────────┘
                   │
                   ├─→ Save to agent.memory
                   │
                   ▼
    ┌────────────────────────────────────┐
    │  HTTP Response                     │
    │  {                                 │
    │    "query": "What is...",          │
    │    "answer": "The methodology...", │
    │    "sources": [                    │
    │      {                             │
    │        "source_doc": "paper.pdf",  │
    │        "chunk_id": 5               │
    │      }                             │
    │    ]                               │
    │  }                                 │
    └────────────────┬───────────────────┘
                     │
                     ▼
                ┌────────────┐
                │    CLIENT  │
                │   Receives │
                │   Answer   │
                └────────────┘
```

---

## Data Structure Flow

```
DOCUMENT (Uploaded)
  │
  ├─ filename: "research_paper.pdf"
  ├─ content: "Full text of 200 pages..."
  ├─ format: "pdf"
  └─ metadata:
      ├─ file_path: "/tmp/research_paper.pdf"
      └─ file_size: 5242880 bytes
  
  │ (DocumentLoader)
  ▼
  
CHUNKS (Processed)
  │
  ├─ Chunk 0:
  │   ├─ text: "Introduction. This paper..."
  │   ├─ chunk_id: 0
  │   ├─ source_doc: "research_paper.pdf"
  │   └─ metadata:
  │       ├─ start_index: 0
  │       ├─ end_index: 1000
  │       └─ character_count: 1000
  │
  ├─ Chunk 1:
  │   ├─ text: "...background. The study..."
  │   ├─ chunk_id: 1
  │   └─ metadata: {...}
  │
  └─ ... (more chunks)
  
  │ (EmbeddingService)
  ▼
  
EMBEDDINGS (Generated)
  │
  ├─ Vector 0: [0.123, -0.456, 0.789, ..., 0.234]  # 384 dimensions
  ├─ Vector 1: [-0.456, 0.789, 0.234, ..., 0.567]
  ├─ Vector 2: [0.789, 0.234, 0.567, ..., -0.890]
  └─ ... (more vectors)
  
  │ (PineconeVectorDB)
  ▼
  
PINECONE INDEX
  │
  ├─ Vector ID: "pdf_chunk_0"
  │   ├─ values: [0.123, -0.456, ...]
  │   └─ metadata: {source_doc, chunk_id, text, ...}
  │
  ├─ Vector ID: "pdf_chunk_1"
  │   └─ ...
  │
  └─ ... (Indexed for fast search)
  
  │ (Query & Search)
  ▼
  
RETRIEVED DOCUMENTS
  │
  ├─ Match 1: {id: "pdf_chunk_5", score: 0.95, metadata: {...}}
  ├─ Match 2: {id: "pdf_chunk_12", score: 0.87, metadata: {...}}
  ├─ Match 3: {id: "pdf_chunk_8", score: 0.78, metadata: {...}}
  ├─ Match 4: {id: "pdf_chunk_15", score: 0.72, metadata: {...}}
  └─ Match 5: {id: "pdf_chunk_3", score: 0.65, metadata: {...}}
  
  │ (ResponseGenerator)
  ▼
  
CONTEXT BUILT
  │
  └─ "[Source: research_paper.pdf]
      The methodology section states...
      
      [Source: research_paper.pdf]
      The study employed..."
  
  │ (Claude API)
  ▼
  
RESPONSE GENERATED
  │
  └─ "Based on the document, the methodology
      used was a quantitative approach with
      statistical analysis of X variables,
      as detailed in Section 2.1 of the paper."
  
  │
  ▼
  
API RESPONSE
  │
  └─ {
      "query": "What methodology was used?",
      "answer": "Based on the document...",
      "sources": [
        {"source_doc": "research_paper.pdf", "chunk_id": 5}
      ]
    }
```

---

## Component Interaction Diagram

```
                    ┌─────────────────┐
                    │  FastAPI App    │
                    │   (main.py)     │
                    └────────┬────────┘
                             │
        ┌────────────────────┼────────────────────┐
        │                    │                    │
        ▼                    ▼                    ▼
    ┌─────────────┐   ┌──────────────┐   ┌──────────────┐
    │ /upload     │   │ /query       │   │ /memory      │
    └──────┬──────┘   └──────┬───────┘   └──────┬───────┘
           │                 │                  │
           │                 │                  │
    ┌──────▼────────┐ ┌──────▼────────┐ ┌──────▼────────┐
    │DocumentLoader │ │Agent          │ │Agent.memory   │
    │   + Chunker   │ │Orchestration  │ │  (read)       │
    └──────┬────────┘ └──────┬────────┘ └───────────────┘
           │                 │
           │         ┌───────┼────────┐
           │         │       │        │
           ▼         ▼       ▼        ▼
    ┌────────────┐┌───────┬──────┬─────────┐
    │Embedding   ││      │ RAG  │Retriever│
    │Service     ││      │      │+ Gen    │
    └─────┬──────┘└──────┬┬─────┴─────────┘
          │              ││
          │         ┌────┘│
          │         │     │
          └────┬────┴─┐   │
               │      │   │
               ▼      ▼   ▼
            ┌────────────────────┐
            │  PineconeVectorDB  │
            │  (upsert/search)   │
            └────────┬───────────┘
                     │
        Network Call │
                     │
                     ▼
            ┌──────────────────┐
            │   Pinecone API   │
            │  (Vector Index)  │
            └──────────────────┘


            ┌──────────────────┐
            │ ResponseGenerator│
            └────────┬─────────┘
                     │
        Network Call │
                     │
                     ▼
            ┌──────────────────┐
            │   Claude API     │
            │   (LLM)          │
            └──────────────────┘
```

---

## State Machine Diagram

```
                        ┌──────────────┐
                        │  COMPLETED   │◄──────────┐
                        └──────────────┘           │
                               │                   │
                               │ new query         │
                               ▼                   │
                        ┌──────────────┐           │
                        │  ANALYZING   │           │
                        │              │           │
                        │ - Detect     │           │
                        │   type       │           │
                        │ - Check      │           │
                        │   context    │           │
                        └──────┬───────┘           │
                               │                   │
                               ▼                   │
                        ┌──────────────┐           │
                        │  RETRIEVING  │           │
                        │              │           │
                        │ - Search     │           │
                        │   docs       │           │
                        │ - Get scores │           │
                        └──────┬───────┘           │
                               │                   │
                         check:│ needs_refinement?│
                        ┌──────┴──────┐            │
                        │             │            │
                      YES           NO │            │
                        │             │            │
                        ▼             ▼            │
                   ┌──────────┐  ┌──────────────┐  │
                   │PROCESSING│  │  GENERATING  │  │
                   │   │      │  │              │  │
                   │   │ Re-  │  │ - Build      │  │
                   │   │ fine │  │   context    │  │
                   │   │ query│  │ - Call Claude│  │
                   │   │      │  │ - Format ans │  │
                   └───┬──────┘  └──────┬───────┘  │
                       │               │          │
                       └───────┬───────┘          │
                               │                 │
                               │ save to memory  │
                               └────────────────►│
                                                COMPLETED
                                                (return
                                               response)

Error Path:
┌─────────────────────────────┐
│  Any State                  │ ◄─── Exception thrown
│  Catches exception          │
│  Logs error                 │
│  Sets state: ERROR          │
└────────────┬────────────────┘
             │
             ▼
        ┌──────────┐
        │  ERROR   │
        │ Return   │
        │ error msg│
        └──────────┘
```

---

## API Endpoint Interaction Flow

```
                        ┌─────────────┐
                        │  External   │
                        │  Client     │
                        └──────┬──────┘
                               │
                ┌──────────────┼─────────────────┬───────────────┐
                │              │                 │               │
                ▼              ▼                 ▼               ▼
          ┌──────────┐   ┌──────────┐    ┌──────────┐    ┌──────────┐
          │ GET      │   │ POST     │    │ GET      │    │ POST     │
          │ /health  │   │ /upload  │    │ /memory  │    │ /reset   │
          └────┬─────┘   └────┬─────┘    └────┬─────┘    └────┬─────┘
               │              │              │              │
               │          File validation    │ Agent memory │
               │          Background task    │ read         │ Clear all
               ▼              │              │ storage      │
          Service status ┌────▼─────┐        │              ▼
          + component    │ Response │    ┌───▼────┐    ┌──────────┐
          checks         │ document_id    │{hist  │    │Response  │
          1s response    └────┬─────┘    │data}  │    │success   │
                              │          └───────┘    └──────────┘
                              │
                         (async background processing)
                         Chunks → Embed → Store
                         Takes 10-60s depending on doc size

                    ┌──────────────┐
                    │ POST /query  │
                    └──────┬───────┘
                           │
                    Query + stream flag
                           │
                      ┌────┴─────┐
                      │           │
                   stream     no stream
                      │           │
                      ▼           ▼
                ┌──────────┐  ┌──────────┐
                │Streaming │  │Full      │
                │Response  │  │Response  │
                │(SSE)     │  │(JSON)    │
                │Chunks as │  │Complete  │
                │they arrive  │answer    │
                │"token..."  │with      │
                │"by"        │sources   │
                │"token"     │          │
                └──────────┘  └──────────┘
```

---

## Performance & Scalability

```
DOCUMENT PROCESSING SPEED
┌────────────────────────────────────┐
│ Document Size → Processing Time    │
├────────────────────────────────────┤
│  1 page (~3KB)    → 1-2 seconds   │
│ 10 pages (~30KB)  → 3-5 seconds   │
│ 50 pages (~150KB) → 10-20 seconds │
│200 pages (~600KB) → 30-60 seconds │
└────────────────────────────────────┘

QUERY RESPONSE TIME
┌──────────────────────────────────┐
│ Query → Response Time            │
├──────────────────────────────────┤
│ Embedding:  0.1s  (local)        │
│ Search:     0.5s  (Pinecone)     │
│ Rerank:     0.2s  (optional)     │
│ Claude:     1-3s  (API call)     │
│ Streaming:  2-4s  (interactive) │
│ ─────────────────────────────────│
│ Total P99:  ~3-5s                │
└──────────────────────────────────┘

SCALABILITY WITH SAGEMAKER
┌─────────────────────────────┐
│ Parallel Processing         │
├─────────────────────────────┤
│ 1 GPU   : 100 docs/hour    │
│ 10 GPUs : 1,000 docs/hour  │
│ 100 GPUs: 10,000 docs/hour │
│ 1K GPUs : 100K docs/hour   │
│         + autoscaling       │
└─────────────────────────────┘
```

---

## Memory & Storage Architecture

```
┌──────────────────────────────┐
│     Agent Memory (RAM)       │
├──────────────────────────────┤
│ conversation_history:        │
│  [{role, content}, ...]      │  ~10K per 100 turns
│                              │
│ query_history:               │
│  ["query1", "query2", ...]   │  ~1KB per 100 queries
│                              │
│ retrieved_documents:         │
│  [{id, score, metadata}, ..] │  ~5KB per retrieval
│                              │
│ Total per agent: 50-100KB    │
│ (Easily fits in memory)      │
└──────────────────────────────┘

┌──────────────────────────────┐
│   Vector Database (Pinecone) │
├──────────────────────────────┤
│ Per document chunk:          │
│  - Vector (384 floats): 1.5KB│
│  - Metadata: 0.5KB           │
│  - Total per chunk: 2KB      │
│                              │
│ 100-page document (~500):    │
│  500 chunks × 2KB = 1MB      │
│                              │
│ 1M documents:                │
│  2TB storage + indexes       │
│  Price: ~$300/month          │
│  Speed: <500ms per query     │
└──────────────────────────────┘

┌─────────────────────────────────┐
│  Temporary File Storage (/tmp)   │
├─────────────────────────────────┤
│ - Uploaded file: variable       │
│ - Deleted after processing      │
│ - No permanent storage          │
└─────────────────────────────────┘
```

---

## Summary

The Intelligent Document Assistant uses a **layered architecture** with clear separation of concerns:

1. **API Layer** (FastAPI) - HTTP interface
2. **Orchestration Layer** (Agent) - Workflow management
3. **Processing Layer** (Document/Chunking) - Data preparation
4. **Embedding Layer** (ST) - Vectorization
5. **Storage Layer** (Pinecone) - Fast retrieval
6. **Generation Layer** (Claude) - Response creation

Each layer is **loosely coupled**, **independently testable**, and **easily scalable**.

---

**Last Updated:** February 15, 2026
