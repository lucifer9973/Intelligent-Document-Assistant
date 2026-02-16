"""
Pinecone Vector Database - Store and retrieve document embeddings
Handles semantic search and retrieval
"""
import logging
from typing import List, Dict, Optional, Tuple
from src.vector_db.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class PineconeVectorDB:
    """Interface to Pinecone vector database"""
    
    def __init__(self, api_key: str, environment: str, index_name: str, 
                 embedding_service: EmbeddingService = None):
        """
        Initialize Pinecone Vector DB
        
        Args:
            api_key: Pinecone API key
            environment: Pinecone environment (e.g., 'us-east1-aws')
            index_name: Name of the Pinecone index
            embedding_service: EmbeddingService instance for generating embeddings
        """
        self.api_key = api_key
        self.environment = environment
        self.index_name = index_name
        self.embedding_service = embedding_service or EmbeddingService()
        self.index = None
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Initialize connection to Pinecone"""
        try:
            from pinecone import Pinecone
            
            logger.info(f"Connecting to Pinecone index: {self.index_name}")
            # Initialize Pinecone client with new API
            pc = Pinecone(api_key=self.api_key)
            self.index = pc.Index(self.index_name)
            logger.info("Pinecone connection established")
        except ImportError:
            logger.error("pinecone not installed. Install with: pip install pinecone")
        except Exception as e:
            logger.error(f"Error initializing Pinecone connection: {str(e)}")
    
    def upsert_documents(self, documents: List[Dict]) -> bool:
        """
        Store document chunks in Pinecone
        
        Args:
            documents: List of dicts with 'id', 'text', 'metadata'
            
        Returns:
            Success status
        """
        if self.index is None:
            logger.error("Pinecone index not initialized")
            return False
        
        try:
            vectors = []
            for doc in documents:
                embedding = self.embedding_service.embed_text(doc['text'])
                if len(embedding) > 0:
                    vectors.append({
                        'id': doc['id'],
                        'values': embedding.tolist(),
                        'metadata': doc.get('metadata', {})
                    })
            
            if vectors:
                self.index.upsert(vectors=vectors)
                logger.info(f"Upserted {len(vectors)} document chunks to Pinecone")
                return True
            return False
        except Exception as e:
            logger.error(f"Error upserting documents: {str(e)}")
            return False
    
    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Search for relevant documents
        
        Args:
            query: Search query text
            top_k: Number of results to return
            
        Returns:
            List of matching documents with scores
        """
        if self.index is None:
            logger.error("Pinecone index not initialized")
            return []
        
        try:
            query_embedding = self.embedding_service.embed_text(query)
            if len(query_embedding) == 0:
                return []
            
            results = self.index.query(
                vector=query_embedding.tolist(),
                top_k=top_k,
                include_metadata=True
            )
            
            documents = []
            for match in results['matches']:
                documents.append({
                    'id': match['id'],
                    'score': match['score'],
                    'metadata': match.get('metadata', {})
                })
            
            return documents
        except Exception as e:
            logger.error(f"Error searching documents: {str(e)}")
            return []
    
    def delete_documents(self, doc_ids: List[str]) -> bool:
        """
        Delete documents from vector database
        
        Args:
            doc_ids: List of document IDs to delete
            
        Returns:
            Success status
        """
        if self.index is None:
            logger.error("Pinecone index not initialized")
            return False
        
        try:
            self.index.delete(ids=doc_ids)
            logger.info(f"Deleted {len(doc_ids)} documents from Pinecone")
            return True
        except Exception as e:
            logger.error(f"Error deleting documents: {str(e)}")
            return False
    
    def get_document_info(self, doc_id: str) -> Optional[Dict]:
        """
        Get metadata for a specific document
        
        Args:
            doc_id: Document ID
            
        Returns:
            Document metadata or None
        """
        if self.index is None:
            return None
        
        try:
            result = self.index.fetch(ids=[doc_id])
            if result['vectors']:
                return result['vectors'][0].get('metadata', {})
            return None
        except Exception as e:
            logger.error(f"Error fetching document info: {str(e)}")
            return None
