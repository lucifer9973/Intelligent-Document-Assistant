"""
Text Chunker - Splits documents into manageable chunks for embeddings
Uses sliding window approach with configurable overlap
"""
from dataclasses import dataclass
from typing import List
import logging

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    """Represents a text chunk"""
    text: str
    chunk_id: int
    source_doc: str
    metadata: dict


class TextChunker:
    """Split text into overlapping chunks for vector processing"""
    
    def __init__(self, chunk_size: int = 1000, overlap: int = 200):
        """
        Initialize TextChunker
        
        Args:
            chunk_size: Size of each chunk in characters
            overlap: Number of overlapping characters between chunks
        """
        self.chunk_size = chunk_size
        self.overlap = overlap
    
    def chunk(self, text: str, source_doc: str = "unknown") -> List[Chunk]:
        """
        Split text into overlapping chunks
        
        Args:
            text: Text to chunk
            source_doc: Source document name for metadata
            
        Returns:
            List of Chunk objects
        """
        if not text or len(text) == 0:
            logger.warning(f"Empty text provided for {source_doc}")
            return []
        
        chunks = []
        chunk_id = 0
        step = self.chunk_size - self.overlap
        
        for i in range(0, len(text), step):
            chunk_text = text[i:i + self.chunk_size]
            if len(chunk_text.strip()) > 0:
                chunk = Chunk(
                    text=chunk_text,
                    chunk_id=chunk_id,
                    source_doc=source_doc,
                    metadata={
                        "start_index": i,
                        "end_index": i + len(chunk_text),
                        "character_count": len(chunk_text)
                    }
                )
                chunks.append(chunk)
                chunk_id += 1
        
        logger.info(f"Created {len(chunks)} chunks from {source_doc}")
        return chunks
    
    def chunk_by_sentences(self, text: str, source_doc: str = "unknown", 
                          target_chunk_size: int = 1000) -> List[Chunk]:
        """
        Split text into chunks at sentence boundaries
        More intelligent approach than character-based splitting
        
        Args:
            text: Text to chunk
            source_doc: Source document name
            target_chunk_size: Target chunk size
            
        Returns:
            List of Chunk objects
        """
        sentences = text.split('. ')
        chunks = []
        chunk_id = 0
        current_chunk = ""
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            
            test_chunk = f"{current_chunk}. {sentence}" if current_chunk else sentence
            
            if len(test_chunk) > target_chunk_size and current_chunk:
                chunk = Chunk(
                    text=current_chunk,
                    chunk_id=chunk_id,
                    source_doc=source_doc,
                    metadata={
                        "character_count": len(current_chunk),
                        "sentence_count": len(current_chunk.split('. '))
                    }
                )
                chunks.append(chunk)
                chunk_id += 1
                current_chunk = sentence
            else:
                current_chunk = test_chunk if current_chunk else sentence
        
        if current_chunk:
            chunk = Chunk(
                text=current_chunk,
                chunk_id=chunk_id,
                source_doc=source_doc,
                metadata={
                    "character_count": len(current_chunk),
                    "sentence_count": len(current_chunk.split('. '))
                }
            )
            chunks.append(chunk)
        
        logger.info(f"Created {len(chunks)} sentence-based chunks from {source_doc}")
        return chunks
