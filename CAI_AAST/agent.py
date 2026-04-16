import asyncio
import logging
import time
from typing import Any, Dict, List, Optional

import ollama
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

# Import the pre-configured Retriever and Context Map from Phase 2
from retriever import CAIRetriever, USER_TYPE_MAP

# Configure logging for metric checks
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# --- API Models ---
class ChatRequest(BaseModel):
    question: str
    user_type: Optional[str] = None

class ChatResponse(BaseModel):
    answer: str
    sources: List[str]
    status: str

# --- Orchestrator Controller ---
class CAIAgent:
    """High-Efficiency LLM Orchestrator integrating vector retrieval and LLM generation."""
    
    def __init__(self, llm_model: str = "tinyllama"):
        """
        Initializes the agent. Uses device='cpu' internally within the retriever
        to heavily offset VRAM usage for the local LLM.
        """
        self.llm_model = llm_model
        
        # Instantiate Retriever. Because Phase 2 instantiated SentenceTransformer
        # strictly with device="cpu", this guarantees ~1.5GB to 2GB VRAM is free 
        # specifically for Ollama execution on the RTX 4050.
        logger.info("Initializing CAIRetriever optimized for memory-constrained environments...")
        self.retriever = CAIRetriever()
        
        # Core prompt constraints enforcing factual bounds
        self.system_prompt = (
            "You are the official AI Assistant for the College of Artificial Intelligence at AASTMT. "
            "Use ONLY the provided context to answer the student's question. "
            "If the answer is not in the context, politely direct them to cai@aast.edu. "
            "Mention the document titles used in your response."
        )

    def _format_context(self, retrieved_results: List[Dict[str, Any]]) -> str:
        """Formats the Qdrant result payload dictionaries into a structured text body for LLM."""
        if not retrieved_results:
            return "No relevant context found."
            
        context_blocks = []
        for res in retrieved_results:
            title = res.get("title", "Unknown")
            content = res.get("content", "")
            context_blocks.append(f"Title: {title}\nContent: {content}\n")
            
        return "\n".join(context_blocks)

    async def get_cai_response(self, question: str, user_type: Optional[str] = None) -> Dict[str, Any]:
        """
        Asynchronous Orchestration loop:
        1. Context Retrieval (Qdrant semantic search)
        2. Prompt Compilation
        3. Local LLM Generation via Ollama AsyncClient (temperature=0.1)
        """
        start_time = time.time()
        
        try:
            # 1. Map intent and Retrieve 
            category_filter = None
            if user_type:
                user_intent = user_type.lower()
                if user_intent in USER_TYPE_MAP:
                    category_filter = USER_TYPE_MAP[user_intent]
                
            logger.info(f"Retrieving context for query: '{question}'...")
            retrieved_results = self.retriever.search(
                query=question,
                category_filter=category_filter,
                top_k=3
            )
            
            # Extract Sources explicitly format mapped directly from our document schemas
            sources = [res.get("title", "Unknown Title") for res in retrieved_results]
            
            # 2. Format Context & Prompt construction
            context_text = self._format_context(retrieved_results)
            full_prompt = (
                f"Context Information:\n{context_text}\n\n"
                f"Student Question: {question}\n"
                "Answer:"
            )
            
            # 3. Call Ollama asynchronously without blocking FastAPI event loop
            logger.info(f"Generating LLM response using model '{self.llm_model}' at Temperature=0.1 ...")
            
            async_client = ollama.AsyncClient()
            response = await async_client.chat(
                model=self.llm_model,
                messages=[
                    {'role': 'system', 'content': self.system_prompt},
                    {'role': 'user', 'content': full_prompt}
                ],
                options={
                    "temperature": 0.1 # Strictly low temperature for factual synthesis ensuring rule accuracy
                }
            )
            
            llm_text = response['message']['content']
            
            # Performance logging
            end_time = time.time()
            generation_time = end_time - start_time
            logger.info(f"--- Generation successful. Elapsed time: {generation_time:.4f} seconds ---")
            
            return {
                "answer": llm_text,
                "sources": sources,
                "status": "success",
                "generation_time_sec": generation_time
            }
            
        except Exception as e:
            logger.error(f"Error occurring in get_cai_response: {e}", exc_info=True)
            return {
                "answer": "An error occurred while generating the response. Please try again later.",
                "sources": [],
                "status": "error"
            }


# --- FastAPI Application Update/Finalization ---
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="CAI Main Controller - Orchestrator API",
    description="Final controller combining vector semantic retrieval with local hardware-constrained Ollama.",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In production, replace with exact frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize single global class for reuse across endpoints
# Hardcoded to requested model swap logic
cai_agent = CAIAgent(llm_model="tinyllama")

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Final phase POST route handling the complete autonomous processing lifecycle.
    """
    logger.info(f"Received Phase 3 /chat request -> question: '{request.question}'")
    
    # Fully asynchronous orchestration handling 
    result = await cai_agent.get_cai_response(
        question=request.question,
        user_type=request.user_type
    )
    
    if result["status"] == "error":
        raise HTTPException(status_code=500, detail="LLM Generation or Retrieval failed.")
        
    return ChatResponse(
        answer=result["answer"],
        sources=result["sources"],
        status=result["status"]
    )

if __name__ == "__main__":
    import uvicorn
    # Final production execution boundary (port 8001 to avoid colliding with Phase 2 if running simultaneously)
    uvicorn.run("agent:app", host="0.0.0.0", port=8001, reload=True)
