"""
Response Generator - Generate answers using Claude API
Combines retrieved documents with LLM for contextual responses
"""
import logging
from typing import List, Dict, Optional
from src.rag_pipeline.retriever import DocumentRetriever

logger = logging.getLogger(__name__)


class ResponseGenerator:
    """Generate contextual responses using Claude API and retrieved documents"""
    
    def __init__(self, api_key: str, retriever: DocumentRetriever, 
                 model: str = "claude-3-sonnet-20240229"):
        """
        Initialize ResponseGenerator
        
        Args:
            api_key: Anthropic API key
            retriever: DocumentRetriever instance
            model: Claude model version to use
        """
        self.api_key = api_key
        self.retriever = retriever
        self.model = model
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Anthropic client"""
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
        if self.client is None:
            logger.error("Client not initialized")
            return "Error: Claude client not initialized"
        
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
