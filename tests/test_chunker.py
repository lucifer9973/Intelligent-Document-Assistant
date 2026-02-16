"""Tests for text chunker"""
import pytest
from src.document_processing.chunker import TextChunker


def test_chunk_creation():
    """Test basic chunk creation"""
    chunker = TextChunker(chunk_size=100, overlap=20)
    text = "This is a sample document. " * 20  # Create a longer text
    
    chunks = chunker.chunk(text)
    
    assert len(chunks) > 0
    assert all(chunk.text for chunk in chunks)


def test_chunk_overlap():
    """Test overlap between chunks"""
    chunker = TextChunker(chunk_size=100, overlap=20)
    text = "A" * 250  # Create known-size text
    
    chunks = chunker.chunk(text)
    
    # Verify overlap exists
    if len(chunks) > 1:
        chunk1_end = chunks[0].metadata['end_index']
        chunk2_start = chunks[1].metadata['start_index']
        overlap = chunk1_end - chunk2_start
        assert overlap > 0


def test_empty_text():
    """Test handling empty text"""
    chunker = TextChunker()
    chunks = chunker.chunk("")
    
    assert chunks == []


if __name__ == "__main__":
    pytest.main([__file__])
