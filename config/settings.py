"""
Configuration settings for Intelligent Document Assistant
"""
from pydantic_settings import BaseSettings
from pydantic import ConfigDict
from typing import List
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    model_config = ConfigDict(env_file=".env", case_sensitive=False, extra="ignore")
    
    # API Configuration
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    environment: str = "development"
    
    # Anthropic Claude API
    anthropic_api_key: str = ""
    
    # Pinecone Vector Database
    pinecone_api_key: str = ""
    pinecone_environment: str = ""
    pinecone_index_name: str = "intelligent-document-index"
    pinecone_project_name: str = ""
    pinecone_project_id: str = ""
    
    # Embedding Model
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    
    # AWS Configuration
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "us-east-1"
    
    # Document Processing
    max_document_size_mb: int = 50
    supported_formats: str = "pdf,docx,txt,pptx"
    
    # RAG Configuration
    chunk_size: int = 1000
    chunk_overlap: int = 200
    top_k_retrieval: int = 5
    
    # Logging
    log_level: str = "INFO"
    
    @property
    def supported_formats_list(self) -> List[str]:
        """Convert supported formats string to list"""
        return [fmt.strip() for fmt in self.supported_formats.split(",")]


# Create global settings instance
settings = Settings()
