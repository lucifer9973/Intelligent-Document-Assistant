"""
FastAPI Application - Main API endpoints for Document Assistant
"""
import logging
import re
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import os
import uuid
import tempfile
from pathlib import Path

from config.settings import settings
from src.document_processing import DocumentLoader, TextChunker
from src.document_processing.loader import Document
from src.vector_db import EmbeddingService, LocalVectorDB, PineconeVectorDB
from src.rag_pipeline import DocumentRetriever, ResponseGenerator
from src.agent_orchestration import DocumentAssistantAgent
from src.llm.local_model import LocalLLM, is_local_llm_available

# Configure logging
logging.basicConfig(level=settings.log_level)
logger = logging.getLogger(__name__)


# Pydantic Models
class QueryRequest(BaseModel):
    """User query request"""
    query: str
    stream: bool = False


class DocumentResponse(BaseModel):
    """Response model for document operations"""
    status: str
    message: str
    file_id: Optional[str] = None
    document_id: Optional[str] = None


class AnswerResponse(BaseModel):
    """Response model for queries"""
    query: str
    response: str
    answer: Optional[str] = None  # For backward compatibility
    sources: Optional[List[dict]] = None


# Initialize components
def create_app() -> FastAPI:
    """Create and configure FastAPI application"""
    app = FastAPI(
        title="Intelligent Document Assistant",
        description="AI-powered document analysis and Q&A system",
        version="1.0.0"
    )
    
    # Add CORS middleware for frontend access
    cors_origins = settings.cors_origins_list or ["*"]
    allow_credentials = settings.cors_allow_credentials and "*" not in cors_origins
    if settings.cors_allow_credentials and "*" in cors_origins:
        logger.warning("CORS credentials are disabled because CORS origins include '*'")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=allow_credentials,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize services
    logger.info("Initializing Document Assistant services...")
    
    document_loader = DocumentLoader(settings.supported_formats_list)
    text_chunker = TextChunker(settings.chunk_size, settings.chunk_overlap)
    embedding_service = EmbeddingService(settings.embedding_model)
    
    vector_db = None
    vector_db_type = "none"
    if settings.pinecone_api_key:
        try:
            vector_db = PineconeVectorDB(
                api_key=settings.pinecone_api_key,
                environment=settings.pinecone_environment,
                index_name=settings.pinecone_index_name,
                embedding_service=embedding_service
            )
            if vector_db.index is not None:
                vector_db_type = "pinecone"
        except Exception as e:
            logger.warning(f"Could not initialize Pinecone: {str(e)}")

    # Local fallback so uploads/queries still work without cloud vector DB.
    if vector_db is None:
        vector_db = LocalVectorDB(embedding_service=embedding_service)
        vector_db_type = "local-memory"
        logger.info("Using local in-memory vector DB fallback")
    
    retriever = None
    generator = None
    agent = None
    local_llm = None

    # Initialize retriever if vector DB exists (allow retrieval even without Anthropic)
    if vector_db:
        retriever = DocumentRetriever(vector_db, top_k=settings.top_k_retrieval)

    # Initialize generator & agent only if Anthropic key is provided
    if vector_db and settings.anthropic_api_key:
        generator = ResponseGenerator(settings.anthropic_api_key, retriever)
        agent = DocumentAssistantAgent(retriever=retriever, generator=generator)

    # Attempt to initialize a local LLM fallback (if llama-cpp-python is installed
    # and the env var LOCAL_LLM_MODEL_PATH points to a model file)
    try:
        model_path = settings.local_llm_model_path or os.getenv("LOCAL_LLM_MODEL_PATH")
        if is_local_llm_available() and model_path:
            try:
                local_llm = LocalLLM(model_path=model_path)
                logger.info(f"Local LLM initialized ({local_llm.backend}) from {model_path}")
            except Exception as e:  # pragma: no cover - runtime environment issues
                logger.warning(f"Could not initialize local LLM: {e}")
        else:
            logger.info("Local LLM not available or LOCAL_LLM_MODEL_PATH not set")
    except Exception:
        local_llm = None
    
    # Store in app state
    app.state.document_loader = document_loader
    app.state.text_chunker = text_chunker
    app.state.embedding_service = embedding_service
    app.state.vector_db = vector_db
    app.state.vector_db_type = vector_db_type
    app.state.agent = agent
    app.state.retriever = retriever
    app.state.generator = generator
    app.state.local_llm = local_llm
    app.state.fallback_memory = []

    _validate_runtime_readiness(
        environment=settings.environment,
        vector_db_type=vector_db_type,
        has_local_llm=bool(local_llm),
        has_agent=bool(agent),
    )

    # Mount built frontend assets when available.
    main_file = Path(__file__).resolve()  # .../src/api/main.py
    project_root = main_file.parent.parent.parent  # .../project_root
    frontend_dist = Path(settings.frontend_dist_path)
    if not frontend_dist.is_absolute():
        frontend_dist = project_root / frontend_dist
    assets_dir = frontend_dist / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
    
    # API Routes
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "services": {
                "vector_db": "ready" if app.state.vector_db else "not configured",
                "vector_db_type": app.state.vector_db_type,
                "agent": "ready" if app.state.agent else "not configured",
                "embedding": "ready" if app.state.embedding_service else "not configured",
                "local_llm": "ready" if app.state.local_llm else "not configured",
            }
        }
    
    @app.post("/upload")
    async def upload_document(file: UploadFile = File(...), 
                             background_tasks: BackgroundTasks = None):
        """Upload and process a document"""
        max_size_bytes = settings.max_document_size_mb * 1024 * 1024
        original_filename = os.path.basename(file.filename or "uploaded_file")
        file_ext = Path(original_filename).suffix.lower().strip(".")
        if file_ext and file_ext not in settings.supported_formats_list:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format '{file_ext}'. Supported formats: {settings.supported_formats_list}"
            )

        temp_path = None
        try:
            file_bytes = await file.read(max_size_bytes + 1)
            if len(file_bytes) > max_size_bytes:
                raise HTTPException(
                    status_code=413,
                    detail=f"File exceeds max size limit of {settings.max_document_size_mb}MB"
                )

            # Infer extension when missing (common for dragged plain-text files).
            content_type = (file.content_type or "").lower()
            inferred_ext = file_ext
            if not inferred_ext:
                content_type_map = {
                    "text/plain": "txt",
                    "application/pdf": "pdf",
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation": "pptx",
                }
                inferred_ext = content_type_map.get(content_type, "")
                if inferred_ext:
                    logger.info(f"Inferred upload extension '{inferred_ext}' from content-type '{content_type}'")

            # Save uploaded file to a unique temp file.
            suffix = f".{inferred_ext}" if inferred_ext else Path(original_filename).suffix
            with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
                tmp_file.write(file_bytes)
                temp_path = tmp_file.name
            
            # Load document
            doc = app.state.document_loader.load(temp_path)
            if doc is None:
                # Fallback: treat unknown or parser-failed files as UTF-8 text when possible.
                try:
                    text_content = file_bytes.decode("utf-8", errors="ignore")
                    if text_content.strip():
                        doc = Document(
                            content=text_content,
                            filename=original_filename,
                            format="txt",
                            metadata={"file_size": len(file_bytes), "content_type": content_type},
                        )
                    else:
                        doc = None
                except Exception:
                    doc = None

            if doc is None:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"Failed to load document '{original_filename}'. "
                        f"Supported formats: {settings.supported_formats_list}. "
                        f"Received content-type: '{content_type or 'unknown'}'."
                    ),
                )

            # Keep the original upload name for metadata/citations.
            doc.filename = original_filename
            
            # Process in background
            document_id = str(uuid.uuid4())
            if background_tasks:
                background_tasks.add_task(
                    _process_document,
                    doc,
                    document_id,
                    app.state.text_chunker,
                    app.state.vector_db
                )
            else:
                _process_document(doc, document_id, app.state.text_chunker, app.state.vector_db)
            
            return DocumentResponse(
                status="success",
                message=f"Document '{original_filename}' uploaded successfully",
                file_id=document_id,
                document_id=document_id
            )
        
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error uploading document: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            try:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception as cleanup_error:
                logger.warning(f"Could not remove temporary upload file: {cleanup_error}")
    
    @app.post("/query")
    async def query_documents(request: QueryRequest):
        """Query documents with AI analysis and optional local-LLM / extractive fallback."""
        # If no vector DB, no agent, and no local model -> cannot serve queries
        if app.state.vector_db is None and app.state.agent is None and app.state.local_llm is None:
            raise HTTPException(status_code=503, detail="No backend available for answering queries")

        try:
            # Preferred path: use configured agent (Anthropic-based)
            if app.state.agent is not None:
                if request.stream:
                    def generate():
                        for chunk in app.state.agent.process(request.query, use_streaming=True):
                            yield chunk

                    return StreamingResponse(generate(), media_type="text/plain")
                else:
                    answer = app.state.agent.process(request.query)
                    sources = None
                    if app.state.retriever:
                        docs = app.state.retriever.retrieve(request.query)
                        sources = [doc.get('metadata', {}) for doc in docs]

                    return AnswerResponse(
                        query=request.query,
                        response=answer,
                        answer=answer,
                        sources=sources
                    )

            # Fallback path: use local LLM if available
            docs = []
            sources = None
            if app.state.retriever:
                docs = app.state.retriever.retrieve(request.query)
                sources = [doc.get('metadata', {}) for doc in docs]

            # Build context from retrieved docs (text is stored in metadata by our indexers).
            context = "\n\n".join(
                [
                    f"Source: {d.get('metadata', {}).get('source_doc', '')}\n"
                    f"{d.get('text') or d.get('metadata', {}).get('text', '')}"
                    for d in docs
                ]
            ) if docs else ""

            if app.state.local_llm is not None:
                prompt = (
                    "Use the following document excerpts to answer the question. Provide a concise answer and cite sources when available:\n\n"
                    f"{context}\n\nQuestion: {request.query}\nAnswer:"
                )
                try:
                    resp_text = app.state.local_llm.generate(prompt, max_tokens=512, temperature=0.2)
                    _append_memory(app, request.query, resp_text)
                    return AnswerResponse(
                        query=request.query,
                        response=resp_text,
                        answer=resp_text,
                        sources=sources
                    )
                except Exception as e:
                    logger.warning(f"Local LLM generation failed: {e}")

            # Final fallback: heuristic non-LLM answer from retrieved snippets.
            if docs:
                extractive = _generate_fallback_answer(request.query, docs)
                _append_memory(app, request.query, extractive)
                return AnswerResponse(
                    query=request.query,
                    response=extractive,
                    answer=extractive,
                    sources=sources
                )

            # If we reach here, no data to answer
            no_info = "I don't have enough information to answer that. Please upload relevant documents."
            _append_memory(app, request.query, no_info)
            return AnswerResponse(
                query=request.query,
                response=no_info,
                answer="",
                sources=[]
            )

        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/memory")
    async def get_agent_memory():
        """Get agent conversation memory"""
        if app.state.agent is None:
            history = app.state.fallback_memory[-100:]
            return {
                "history": history,
                "conversation_history": history,
                "query_count": len(history),
                "documents_retrieved": 0
            }
        
        memory = app.state.agent.get_memory()
        
        # Format history for frontend
        history = []
        if hasattr(memory, 'query_history') and hasattr(memory, 'conversation_history'):
            for i, query in enumerate(memory.query_history):
                response = memory.conversation_history[i] if i < len(memory.conversation_history) else ""
                history.append({
                    "query": query,
                    "response": response
                })
        
        return {
            "history": history,
            "conversation_history": memory.conversation_history if hasattr(memory, 'conversation_history') else [],
            "query_count": len(memory.query_history) if hasattr(memory, 'query_history') else 0,
            "documents_retrieved": len(memory.retrieved_documents) if hasattr(memory, 'retrieved_documents') else 0
        }
    
    @app.post("/reset")
    async def reset_memory():
        """Reset agent memory"""
        if app.state.agent is not None:
            app.state.agent.reset_memory()
        app.state.fallback_memory = []
        return {"status": "success", "message": "Agent memory reset"}
    
    @app.get("/")
    async def root():
        """Root endpoint - serve frontend or API info"""
        candidates = [
            frontend_dist / "index.html",
            project_root / "index.html",
        ]
        for candidate in candidates:
            if candidate.exists():
                logger.info(f"Serving frontend from: {candidate}")
                return FileResponse(str(candidate), media_type="text/html")
        
        # Fallback: return API info
        return {
            "name": "Intelligent Document Assistant",
            "version": "1.0.0",
            "endpoints": {
                "health": "/health",
                "upload": "/upload",
                "query": "/query",
                "memory": "/memory",
                "reset": "/reset"
            }
        }

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon():
        """Serve favicon when present; avoid noisy 404s in local logs."""
        candidates = [
            frontend_dist / "favicon.ico",
            project_root / "favicon.ico",
        ]
        for candidate in candidates:
            if candidate.exists():
                return FileResponse(str(candidate), media_type="image/x-icon")
        return Response(status_code=204)
    
    return app


def _process_document(doc, document_id: str, text_chunker: TextChunker, vector_db):
    """Process document in background"""
    try:
        logger.info(f"Processing document: {doc.filename}")
        
        # Chunk the document
        chunks = text_chunker.chunk(doc.content, doc.filename)
        
        # Create vectors for storage
        documents_to_store = []
        for chunk in chunks:
            documents_to_store.append({
                'id': f"{document_id}_{chunk.chunk_id}",
                'text': chunk.text,
                'metadata': {
                    'source_doc': doc.filename,
                    'document_id': document_id,
                    'chunk_id': chunk.chunk_id,
                    'text': chunk.text,  # Store text in metadata too
                    **chunk.metadata
                }
            })
        
        # Store in vector database
        vector_db.upsert_documents(documents_to_store)
        logger.info(f"Document {document_id} processed and stored successfully")
    
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}")


def _append_memory(app: FastAPI, query: str, response: str) -> None:
    """Append to fallback memory with bounded size."""
    app.state.fallback_memory.append({"query": query, "response": response})
    max_items = max(1, settings.max_fallback_memory_items)
    if len(app.state.fallback_memory) > max_items:
        app.state.fallback_memory = app.state.fallback_memory[-max_items:]


def _validate_runtime_readiness(
    environment: str,
    vector_db_type: str,
    has_local_llm: bool,
    has_agent: bool,
) -> None:
    """Fail fast in production for misconfigured critical dependencies."""
    if environment.lower() != "production":
        return

    if settings.require_pinecone_in_production and vector_db_type != "pinecone":
        raise RuntimeError(
            "Production startup blocked: Pinecone is required but not configured. "
            "Set PINECONE_API_KEY/PINECONE_ENVIRONMENT/PINECONE_INDEX_NAME."
        )

    if settings.require_llm_in_production and not (has_agent or has_local_llm):
        raise RuntimeError(
            "Production startup blocked: no LLM available. "
            "Configure ANTHROPIC_API_KEY or LOCAL_LLM_MODEL_PATH."
        )


def _doc_text(match: dict) -> str:
    """Get chunk text regardless of backend-specific shape."""
    return match.get("text") or match.get("metadata", {}).get("text", "")


def _is_requirements_like(text: str) -> bool:
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    dep_lines = 0
    for ln in lines:
        if ln.startswith("#"):
            continue
        if re.match(r"^[A-Za-z0-9_.-]+(\[[A-Za-z0-9_,.-]+\])?\s*(==|>=|<=|~=|>|<)", ln):
            dep_lines += 1
    return dep_lines >= 5


def _summarize_requirements(text: str) -> str:
    categories = []
    packages = []
    for ln in text.splitlines():
        raw = ln.strip()
        if not raw:
            continue
        if raw.startswith("#"):
            label = raw.lstrip("#").strip()
            if label:
                categories.append(label)
            continue
        m = re.match(r"^([A-Za-z0-9_.-]+)", raw)
        if m:
            packages.append(m.group(1))

    unique_categories = list(dict.fromkeys(categories))
    unique_packages = list(dict.fromkeys(packages))
    top_categories = ", ".join(unique_categories[:8]) if unique_categories else "dependencies"
    sample_packages = ", ".join(unique_packages[:10]) if unique_packages else "project packages"

    return (
        "This document is a Python dependency manifest (`requirements.txt`) for the project. "
        f"It lists {len(unique_packages)} packages grouped by sections such as: {top_categories}. "
        f"Example packages: {sample_packages}."
    )


def _generate_fallback_answer(query: str, docs: List[dict]) -> str:
    """Generate a useful response when no LLM is available."""
    query_l = query.lower()
    chunk_texts = [_doc_text(d) for d in docs if _doc_text(d).strip()]
    if not chunk_texts:
        return "I found related chunks, but they were empty."

    combined = "\n".join(chunk_texts)
    intent_is_summary = any(
        k in query_l for k in ["about", "summary", "summarize", "what is this", "overview"]
    )

    if intent_is_summary and _is_requirements_like(combined):
        return _summarize_requirements(combined)

    # Keyword-based extractive fallback for non-summary queries.
    tokens = [t for t in re.findall(r"[a-zA-Z0-9_.-]+", query_l) if len(t) > 3]
    if tokens:
        ranked = []
        for line in combined.splitlines():
            line_l = line.lower()
            score = sum(1 for t in tokens if t in line_l)
            if score > 0:
                ranked.append((score, line.strip()))
        if ranked:
            ranked.sort(key=lambda x: x[0], reverse=True)
            top = [line for _, line in ranked[:8]]
            return "\n".join(top)

    # Last resort: return a clipped extract instead of the full raw chunk dump.
    return combined[:1200]


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
