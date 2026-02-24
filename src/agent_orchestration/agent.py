"""
Document Assistant Agent - LangGraph-based workflow orchestration
Handles complex reasoning with multiple steps and decisions
"""
import logging
from typing import Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AgentState(Enum):
    """States in the agent workflow"""
    ANALYZING = "analyzing"
    RETRIEVING = "retrieving"
    PROCESSING = "processing"
    GENERATING = "generating"
    COMPLETED = "completed"
    ERROR = "error"


@dataclass
class AgentMemory:
    """Agent memory for conversation context"""
    conversation_history: List[Dict] = field(default_factory=list)
    retrieved_documents: List[Dict] = field(default_factory=list)
    query_history: List[str] = field(default_factory=list)
    
    def add_message(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content
        })
    
    def add_query(self, query: str):
        """Add query to history"""
        self.query_history.append(query)
    
    def get_context(self, max_messages: int = 10) -> str:
        """Get recent conversation context"""
        recent = self.conversation_history[-max_messages:]
        context = ""
        for msg in recent:
            context += f"{msg['role']}: {msg['content']}\n"
        return context


class DocumentAssistantAgent:
    """Main agent that orchestrates document analysis workflow"""
    
    def __init__(self, retriever=None, generator=None):
        """
        Initialize Document Assistant Agent
        
        Args:
            retriever: DocumentRetriever instance
            generator: ResponseGenerator instance
        """
        self.retriever = retriever
        self.generator = generator
        self.memory = AgentMemory()
        self.state = AgentState.COMPLETED
    
    def process(self, query: str, use_streaming: bool = False) -> str:
        """
        Process user query through agent workflow
        
        Args:
            query: User question
            use_streaming: Stream response token by token
            
        Returns:
            Generated response
        """
        logger.info(f"Processing query: {query[:100]}...")
        
        try:
            # Step 1: Analyze query
            self.state = AgentState.ANALYZING
            analysis = self._analyze_query(query)
            logger.info(f"Query analysis: {analysis}")
            
            # Step 2: Retrieve relevant documents
            self.state = AgentState.RETRIEVING
            documents = self._retrieve_documents(query)
            self.memory.retrieved_documents = documents
            
            # Step 3: Determine if more info needed
            if self._needs_refinement(query, documents):
                logger.info("Query refinement needed, searching again...")
                refined_query = self._refine_query(query, documents)
                documents = self._retrieve_documents(refined_query)
            
            # Step 4: Generate response
            self.state = AgentState.GENERATING
            if use_streaming:
                stream = self._generate_streaming_response(query, documents)

                def stream_with_memory():
                    chunks = []
                    for chunk in stream:
                        chunks.append(chunk)
                        yield chunk

                    response = "".join(chunks)
                    self.memory.add_query(query)
                    self.memory.add_message("user", query)
                    self.memory.add_message("assistant", response)
                    self.state = AgentState.COMPLETED

                return stream_with_memory()
            else:
                response = self._generate_response(query, documents)
            
            # Step 5: Store in memory and return
            self.memory.add_query(query)
            self.memory.add_message("user", query)
            self.memory.add_message("assistant", response)
            
            self.state = AgentState.COMPLETED
            return response
        
        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            self.state = AgentState.ERROR
            return f"Error processing query: {str(e)}"
    
    def _analyze_query(self, query: str) -> Dict:
        """Analyze user query for intent and information needs"""
        return {
            "query": query,
            "estimated_complexity": "high" if len(query) > 100 else "medium",
            "question_type": self._detect_question_type(query)
        }
    
    def _detect_question_type(self, query: str) -> str:
        """Detect type of question asked"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ["what", "which", "who"]):
            return "factual"
        elif any(word in query_lower for word in ["why", "how"]):
            return "explanatory"
        elif any(word in query_lower for word in ["summarize", "summary"]):
            return "summarization"
        else:
            return "general"
    
    def _retrieve_documents(self, query: str) -> List[Dict]:
        """Retrieve relevant documents"""
        if self.retriever is None:
            logger.warning("No retriever configured")
            return []
        
        return self.retriever.retrieve(query)
    
    def _needs_refinement(self, query: str, documents: List[Dict]) -> bool:
        """Determine if query needs refinement based on retrieved documents"""
        # If no documents found, might need refinement
        if not documents:
            return True
        
        # If average relevance score is low, needs refinement
        scores = [doc.get('score', 0) for doc in documents]
        avg_score = sum(scores) / len(scores) if scores else 0
        
        return avg_score < 0.5  # Threshold for relevance
    
    def _refine_query(self, query: str, documents: List[Dict]) -> str:
        """Refine query for better retrieval"""
        logger.info("Refining query...")
        
        # Simple refinement: remove stop words and focus on key terms
        stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'in', 'on', 'at'}
        words = query.split()
        refined = ' '.join([w for w in words if w.lower() not in stop_words])
        
        return refined if refined else query
    
    def _generate_response(self, query: str, documents: List[Dict]) -> str:
        """Generate response using generator"""
        if self.generator is None:
            logger.warning("No generator configured")
            return "Generator not configured"
        
        return self.generator.generate_response(query, documents)
    
    def _generate_streaming_response(self, query: str, documents: List[Dict]) -> str:
        """Generate streaming response"""
        if self.generator is None:
            yield "Generator not configured"
            return
        
        for chunk in self.generator.stream_response(query, documents):
            yield chunk  # Yield for streaming
    
    def get_memory(self) -> AgentMemory:
        """Get agent memory for context"""
        return self.memory
    
    def reset_memory(self):
        """Reset agent memory"""
        self.memory = AgentMemory()
        logger.info("Agent memory reset")
