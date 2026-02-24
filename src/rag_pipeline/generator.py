"""
Response Generator - Generate answers using Claude API or Local LLM
Combines retrieved documents with LLM for contextual responses
"""
import logging
import os
from typing import List, Dict, Optional
from src.rag_pipeline.retriever import DocumentRetriever
from src.llm.local_model import LocalLLM

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Generate contextual responses using Claude API, Local LLM, or retrieved documents"""
    
    def __init__(self, api_key: str = "", retriever: DocumentRetriever = None, 
                 model: str = "claude-3-sonnet-20240229",
                 local_model_path: str = ""):
        """
        Initialize ResponseGenerator
        
        Args:
            api_key: Anthropic API key (if using Claude)
            retriever: DocumentRetriever instance
            model: Claude model version to use
            local_model_path: Path to local GGML model (if using GPT4All)
        """
        self.api_key = api_key
        self.retriever = retriever
        self.model = model
        self.local_model_path = local_model_path or os.getenv("LOCAL_LLM_MODEL_PATH")
        self.client = None
        self.local_llm = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Anthropic client or Local LLM"""
        # Check if local model is available
        if self.local_model_path and os.path.exists(self.local_model_path):
            try:
                self.local_llm = LocalLLM(model_path=self.local_model_path)
                logger.info(f"Initialized local LLM from: {self.local_model_path}")
                return
            except Exception as e:
                logger.warning(f"Failed to load local model: {e}. Trying API...")
        
        # Fall back to Anthropic API
        if self.api_key:
            try:
                from anthropic import Anthropic
                self.client = Anthropic(api_key=self.api_key)
                logger.info(f"Initialized Anthropic client with model: {self.model}")
            except ImportError:
                logger.error("anthropic library not installed")
            except Exception as e:
                logger.error(f"Error initializing Anthropic client: {str(e)}")
    
    def generate_response(self, query: str, context_documents: List[Dict] = None,
                         include_citations: bool = True) -> str:
        """
        Generate response to user query using retrieved documents
        
        Args:
            query: User question/query
            context_documents: Pre-retrieved documents (retrieves if not provided)
            include_citations: Include citations from source documents
            
        Returns:
            Generated response text
        """
        # Use local LLM if available
        if self.local_llm is not None:
            return self._generate_local_response(query, context_documents, include_citations)
        
        if self.client is None:
            logger.error("Client not initialized")
            return "Error: No LLM available. Please set either API key or local model path."
        
        # Retrieve relevant documents if not provided
        if context_documents is None:
            context_documents = self.retriever.retrieve(query)
        
        if not context_documents:
            logger.warning("No relevant documents found")
            return self._generate_no_context_response(query)
        
        # Build context from retrieved documents
        context = self._build_context(context_documents, include_citations)
        
        # Create prompt with context
        prompt = self._create_prompt(query, context, include_citations)
        
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=2048,
                messages=[
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            )
            
            answer = response.content[0].text
            logger.info("Response generated successfully")
            return answer
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return f"Error generating response: {str(e)}"
    
    def _build_context(self, documents: List[Dict], include_citations: bool) -> str:
        """Build context string from retrieved documents"""
        context_parts = []
        
        for i, doc in enumerate(documents):
            metadata = doc.get('metadata', {})
            text = metadata.get('text', '')
            
            if text:
                if include_citations:
                    source = metadata.get('source_doc', 'Unknown')
                    context_parts.append(f"[Source: {source}]\n{text}")
                else:
                    context_parts.append(text)
        
        return "\n\n".join(context_parts)
    
    def _create_prompt(self, query: str, context: str, 
                      include_citations: bool) -> str:
        """Create prompt for Claude"""
        if include_citations:
            prompt = f"""Based on the following document excerpts, answer the user's question. 
If the answer cannot be found in the documents, say so explicitly.
Include references to the source documents when citing information.

Document Context:
{context}

User Question: {query}

Please provide a clear, concise answer with citations where applicable."""
        else:
            prompt = f"""Based on the following information, answer the user's question:

{context}

User Question: {query}

Please provide a clear, concise answer."""
        
        return prompt
    
    def _generate_local_response(self, query: str, context_documents: List[Dict] = None,
                               include_citations: bool = True) -> str:
        """Generate response using local LLM (GPT4All)"""
        # Retrieve relevant documents if not provided
        if context_documents is None and self.retriever:
            context_documents = self.retriever.retrieve(query)
        
        context = ""
        if context_documents:
            context = self._build_context(context_documents, include_citations)
        
        # Create prompt with context
        prompt = self._create_prompt(query, context, include_citations)
        
        try:
            answer = self.local_llm.generate(
                prompt=prompt,
                max_tokens=1024,
                temperature=0.1
            )
            logger.info("Local LLM response generated successfully")
            return answer
        except Exception as e:
            logger.error(f"Error generating local response: {str(e)}")
            return f"Error generating response from local model: {str(e)}"
    
    def _generate_no_context_response(self, query: str) -> str:
        """Generate response when no relevant documents found"""
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {
                        "role": "user",
                        "content": f"No specific documents were available to answer this question. " \
                                  f"Based on general knowledge, {query}"
                    }
                ]
            )
            return response.content[0].text
        except Exception as e:
            return f"No relevant documents found and error generating response: {str(e)}"
    
    def stream_response(self, query: str, context_documents: List[Dict] = None):
        """
        Stream response token by token
        
        Args:
            query: User question
            context_documents: Pre-retrieved documents
            
        Yields:
            Response tokens
        """
        if self.client is None:
            logger.error("Client not initialized")
            yield "Error: Claude client not initialized"
            return
        
        if context_documents is None:
            context_documents = self.retriever.retrieve(query)
        
        context = self._build_context(context_documents, include_citations=True)
        prompt = self._create_prompt(query, context, include_citations=True)
        
        try:
            with self.client.messages.stream(
                model=self.model,
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}]
            ) as stream:
                for text in stream.text_stream:
                    yield text
        except Exception as e:
            logger.error(f"Error streaming response: {str(e)}")
            yield f"Error: {str(e)}"
