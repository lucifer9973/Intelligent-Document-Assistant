"""
Document Retriever - Fetches relevant chunks from vector database
Core of RAG - Retrieval Augmented Generation
"""
import logging
from typing import List, Dict
from src.vector_db import PineconeVectorDB

logger = logging.getLogger(__name__)


class DocumentRetriever:
    """Retrieve relevant documents from vector database"""
    
    def __init__(self, vector_db: PineconeVectorDB, top_k: int = 5):
        """
        Initialize DocumentRetriever
        
        Args:
            vector_db: PineconeVectorDB instance
            top_k: Number of documents to retrieve per query
        """
        self.vector_db = vector_db
        self.top_k = top_k
    
    def retrieve(self, query: str, top_k: int = None) -> List[Dict]:
        """
        Retrieve relevant documents for a query
        
        Args:
            query: User query/question
            top_k: Number of results (uses default if not specified)
            
        Returns:
            List of relevant documents with relevance scores
        """
        k = top_k or self.top_k
        
        logger.info(f"Retrieving {k} documents for query: {query[:100]}...")
        
        try:
            results = self.vector_db.search(query, top_k=k)
            logger.info(f"Retrieved {len(results)} relevant documents")
            return results
        except Exception as e:
            logger.error(f"Error retrieving documents: {str(e)}")
            return []
    
    def retrieve_with_filter(self, query: str, filters: Dict = None, 
                           top_k: int = None) -> List[Dict]:
        """
        Retrieve documents with optional metadata filtering
        
        Args:
            query: User query/question
            filters: Metadata filters (not fully supported in basic Pinecone)
            top_k: Number of results
            
        Returns:
            Filtered relevant documents
        """
        results = self.retrieve(query, top_k=top_k)
        
        # Apply local filtering if filters provided
        if filters:
            results = self._apply_local_filters(results, filters)
        
        return results
    
    def _apply_local_filters(self, documents: List[Dict], 
                            filters: Dict) -> List[Dict]:
        """Apply metadata filters to retrieved documents"""
        filtered = []
        
        for doc in documents:
            metadata = doc.get('metadata', {})
            match = True
            
            for key, value in filters.items():
                if metadata.get(key) != value:
                    match = False
                    break
            
            if match:
                filtered.append(doc)
        
        return filtered
    
    def rerank_results(self, query: str, documents: List[Dict]) -> List[Dict]:
        """
        Rerank retrieved documents using cross-encoder
        Improves relevance of final results
        
        Args:
            query: Original query
            documents: Retrieved documents
            
        Returns:
            Reranked documents
        """
        try:
            from sentence_transformers import CrossEncoder
            
            reranker = CrossEncoder('cross-encoder/ms-marco-MiniLM-L-6-v2')
            
            passages = [doc.get('metadata', {}).get('text', '') for doc in documents]
            scores = reranker.predict([[query, passage] for passage in passages])
            
            for i, score in enumerate(scores):
                documents[i]['rerank_score'] = float(score)
            
            # Sort by rerank score
            documents.sort(key=lambda x: x.get('rerank_score', 0), reverse=True)
            
            return documents
        except ImportError:
            logger.warning("Cross-encoder not available, returning original results")
            return documents
        except Exception as e:
            logger.error(f"Error reranking results: {str(e)}")
            return documents
