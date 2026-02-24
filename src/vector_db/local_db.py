"""
In-memory vector database fallback.
Useful for local development when Pinecone is not configured.
"""
import logging
from typing import Dict, List, Optional

import numpy as np

from src.vector_db.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class LocalVectorDB:
    """A simple in-memory vector store with cosine similarity search."""

    def __init__(self, embedding_service: EmbeddingService = None):
        self.embedding_service = embedding_service or EmbeddingService()
        self._items: Dict[str, Dict] = {}

    def upsert_documents(self, documents: List[Dict]) -> bool:
        try:
            for doc in documents:
                doc_id = doc["id"]
                embedding = self.embedding_service.embed_text(doc["text"])
                if len(embedding) == 0:
                    continue
                self._items[doc_id] = {
                    "id": doc_id,
                    "vector": embedding.astype(np.float32),
                    "metadata": doc.get("metadata", {}),
                }
            logger.info(f"Stored {len(documents)} chunks in local in-memory vector store")
            return True
        except Exception as e:
            logger.error(f"Error in local upsert: {e}")
            return False

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        if not self._items:
            return []
        try:
            query_vec = self.embedding_service.embed_text(query)
            if len(query_vec) == 0:
                return []
            query_norm = np.linalg.norm(query_vec) + 1e-8

            results: List[Dict] = []
            for item in self._items.values():
                vec = item["vector"]
                score = float(np.dot(query_vec, vec) / (query_norm * (np.linalg.norm(vec) + 1e-8)))
                results.append(
                    {
                        "id": item["id"],
                        "score": score,
                        "metadata": item["metadata"],
                    }
                )

            results.sort(key=lambda x: x["score"], reverse=True)
            return results[:top_k]
        except Exception as e:
            logger.error(f"Error in local search: {e}")
            return []

    def delete_documents(self, doc_ids: List[str]) -> bool:
        try:
            for doc_id in doc_ids:
                self._items.pop(doc_id, None)
            return True
        except Exception as e:
            logger.error(f"Error in local delete: {e}")
            return False

    def get_document_info(self, doc_id: str) -> Optional[Dict]:
        item = self._items.get(doc_id)
        if not item:
            return None
        return item.get("metadata", {})
