"""
FastAPI Application - Main API endpoints for Document Assistant
"""
import logging
from fastapi import FastAPI, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import List, Optional
import os
import uuid
import tempfile

from config.settings import settings
from src.document_processing import DocumentLoader, TextChunker
from src.vector_db import EmbeddingService, PineconeVectorDB
from src.rag_pipeline import DocumentRetriever, ResponseGenerator
from src.agent_orchestration import DocumentAssistantAgent

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
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*", "null"],  # Allow all origins including file:// protocol
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Initialize services
    logger.info("Initializing Document Assistant services...")
    
    document_loader = DocumentLoader(settings.supported_formats_list)
    text_chunker = TextChunker(settings.chunk_size, settings.chunk_overlap)
    embedding_service = EmbeddingService(settings.embedding_model)
    
    vector_db = None
    if settings.pinecone_api_key:
        try:
            vector_db = PineconeVectorDB(
                api_key=settings.pinecone_api_key,
                environment=settings.pinecone_environment,
                index_name=settings.pinecone_index_name,
                embedding_service=embedding_service
            )
        except Exception as e:
            logger.warning(f"Could not initialize Pinecone: {str(e)}")
    
    retriever = None
    generator = None
    agent = None
    
    if vector_db and settings.anthropic_api_key:
        retriever = DocumentRetriever(vector_db, top_k=settings.top_k_retrieval)
        generator = ResponseGenerator(settings.anthropic_api_key, retriever)
        agent = DocumentAssistantAgent(retriever=retriever, generator=generator)
    
    # Store in app state
    app.state.document_loader = document_loader
    app.state.text_chunker = text_chunker
    app.state.embedding_service = embedding_service
    app.state.vector_db = vector_db
    app.state.agent = agent
    app.state.retriever = retriever
    app.state.generator = generator
    
    # API Routes
    @app.get("/health")
    async def health_check():
        """Health check endpoint"""
        return {
            "status": "healthy",
            "services": {
                "vector_db": "ready" if app.state.vector_db else "not configured",
                "agent": "ready" if app.state.agent else "not configured",
                "embedding": "ready" if app.state.embedding_service else "not configured"
            }
        }
    
    @app.post("/upload")
    async def upload_document(file: UploadFile = File(...), 
                             background_tasks: BackgroundTasks = None):
        """Upload and process a document"""
        if app.state.vector_db is None:
            raise HTTPException(status_code=503, detail="Vector database not configured")
        
        try:
            # Save uploaded file to temp directory (cross-platform)
            temp_dir = tempfile.gettempdir()
            file_path = os.path.join(temp_dir, file.filename)
            with open(file_path, 'wb') as f:
                f.write(await file.read())
            
            # Load document
            doc = app.state.document_loader.load(file_path)
            if doc is None:
                raise HTTPException(status_code=400, detail="Failed to load document")
            
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
                message=f"Document '{file.filename}' uploaded successfully",
                file_id=document_id,
                document_id=document_id
            )
        
        except Exception as e:
            logger.error(f"Error uploading document: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.post("/query")
    async def query_documents(request: QueryRequest):
        """Query documents with AI analysis"""
        if app.state.agent is None:
            raise HTTPException(status_code=503, detail="Agent not configured")
        
        try:
            if request.stream:
                def generate():
                    for chunk in app.state.agent.process(request.query, use_streaming=True):
                        yield chunk
                
                return StreamingResponse(generate(), media_type="text/plain")
            else:
                answer = app.state.agent.process(request.query)
                
                # Get retrieved documents for sources
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
        
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    @app.get("/memory")
    async def get_agent_memory():
        """Get agent conversation memory"""
        if app.state.agent is None:
            raise HTTPException(status_code=503, detail="Agent not configured")
        
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
        if app.state.agent is None:
            raise HTTPException(status_code=503, detail="Agent not configured")
        
        app.state.agent.reset_memory()
        return {"status": "success", "message": "Agent memory reset"}
    
    @app.get("/")
    async def root():
        """Root endpoint - serve frontend or API info"""
        # Try to serve index.html from project root
        # main.py is at: project_root/src/api/main.py
        main_file = os.path.abspath(__file__)  # .../src/api/main.py
        api_dir = os.path.dirname(main_file)  # .../src/api
        src_dir = os.path.dirname(api_dir)  # .../src
        project_root = os.path.dirname(src_dir)  # .../project_root
        index_path = os.path.join(project_root, "index.html")
        
        logger.info(f"Looking for index.html at: {index_path}")
        if os.path.exists(index_path):
            logger.info("Serving index.html from project root")
            return FileResponse(index_path, media_type="text/html")
        
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
    
    return app


def _process_document(doc, document_id: str, text_chunker: TextChunker, 
                     vector_db: PineconeVectorDB):
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


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.api_host, port=settings.api_port)
