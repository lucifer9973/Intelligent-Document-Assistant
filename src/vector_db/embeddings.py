"""
Embedding Service - Convert text to vector embeddings
Uses simple hash-based embeddings (no heavy dependencies)
"""
import logging
from typing import List
import numpy as np
import hashlib

logger = logging.getLogger(__name__)


class EmbeddingService:
    """Generate embeddings for text using simple hash-based method"""
    
    def __init__(self, model_name: str = "simple-hash", embedding_dim: int = 1536):
        """
        Initialize Embedding Service
        
        Args:
            model_name: Model name (kept for compatibility)
            embedding_dim: Dimension of embedding vectors (default 1536 for OpenAI compatibility)
        """
        self.model_name = model_name
        self.embedding_dim = embedding_dim
        logger.info(f"Initialized simple embedding service (dim={embedding_dim})")
    
    def _generate_deterministic_embedding(self, text: str) -> np.ndarray:
        """Generate deterministic embedding using text hash"""
        # Create a deterministic but pseudo-random vector from text hash
        hash_val = hashlib.sha256(text.encode()).digest()
        # Convert hash to seed in valid range (0 to 2**32 - 1)
        seed_value = int.from_bytes(hash_val[:4], 'big') % (2**31)  # Use modulo to keep in range
        np.random.seed(seed_value)
        embedding = np.random.randn(self.embedding_dim).astype(np.float32)
        # Normalize to unit length
        embedding = embedding / (np.linalg.norm(embedding) + 1e-8)
        return embedding
    
    def embed_text(self, text: str) -> np.ndarray:
        """
        Generate embedding for single text
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as numpy array
        """
        try:
            embedding = self._generate_deterministic_embedding(text)
            return embedding
        except Exception as e:
            logger.error(f"Error embedding text: {str(e)}")
            return np.array([])
    
    def embed_texts(self, texts: List[str]) -> List[np.ndarray]:
        """
        Generate embeddings for multiple texts
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        try:
            embeddings = [self._generate_deterministic_embedding(text) for text in texts]
            logger.debug(f"Generated embeddings for {len(texts)} texts")
            return embeddings
        except Exception as e:
            logger.error(f"Error embedding texts: {str(e)}")
            return []
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings produced by this model"""
        return self.embedding_dim
