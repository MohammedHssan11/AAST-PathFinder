import logging
from typing import Any, Dict, List, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from qdrant_client import QdrantClient
from qdrant_client.http import models as qdrant_models
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# --- Data Models ---
class AskRequest(BaseModel):
    question: str
    user_type: Optional[str] = None

class AskResponse(BaseModel):
    results: List[Dict[str, Any]]

# --- Service Layer ---
class CAIRetriever:
    """Service layer class for interacting with Qdrant Vector DB and BGE-M3."""
    
    def __init__(self, model_name: str = "BAAI/bge-m3", 
                 host: str = "localhost", 
                 port: int = 6333, 
                 collection_name: str = "aast_cai_knowledge"):
        self.collection_name = collection_name
        
        logger.info("Initializing CAIRetriever...")
        
        # Load the identical model as ingestion for strict vector space consistency
        logger.info(f"Loading embedding space model: {model_name}")
        self.model = SentenceTransformer(model_name, device="cpu")
        
        logger.info(f"Connecting to Qdrant at {host}:{port}")
        self.client = QdrantClient(host=host, port=port)
        
    def get_embedding(self, text: str) -> List[float]:
        """
        Generates dense vector using strictly the same pipeline parameters as ingestion.
        """
        # normalize_embeddings=True was used natively in our ingestion phase 
        # so we maintain exact semantic space alignment.
        return self.model.encode(text, normalize_embeddings=True).tolist()

    def search(self, query: str, category_filter: Optional[str] = None, top_k: int = 3) -> List[Dict[str, Any]]:
        """
        Embeds the query, uses Qdrant's Filter logic to narrow the search space
        to the specified category, and retrieves nearest neighbors.
        """
        logger.info(f"Executing search for query: '{query}' | Target Category: {category_filter if category_filter else 'GLOBAL FALLBACK'}")
        query_vector = self.get_embedding(query)
        
        # Implement Smart Filtering via Keyword matching on indexed payload
        q_filter = None
        if category_filter:
            q_filter = qdrant_models.Filter(
                must=[
                    qdrant_models.FieldCondition(
                        key="category",
                        match=qdrant_models.MatchValue(value=category_filter)
                    )
                ]
            )
        
        # Execute cosine similarity search
        response = self.client.query_points(
            collection_name=self.collection_name,
            query=query_vector,
            query_filter=q_filter,
            limit=top_k
        )
        results = response.points
        
        # Format Results cleanly
        formatted_results = []
        for res in results:
            formatted_results.append({
                "score": res.score,
                "title": res.payload.get("title", "Unknown Title"),
                "content": res.payload.get("content", ""),
            })
            
        return formatted_results


# --- FastAPI Application Setup ---
app = FastAPI(
    title="CAI API - Intent Aware Retriever",
    description="A service layer handling retrieval queries safely powered by BGE-M3 and Qdrant DB.",
    version="1.0.0"
)

# Global Instance memory init
# Note: For strict production environments, lifespan events handle this better, but this works globally well for now.
retriever = CAIRetriever()

# Categorical Intent Map
# Expanding this based on actual knowledge domain labels helps us natively map intent to payload indices.
USER_TYPE_MAP = {
    "msc": "Postgraduate Programs",
    "undergrad": "Undergraduate Programs",
    "financial": "Financial Information",
    "admissions": "Admissions",
    "compliance": "Compliance and Quality",
    "academic": "Academic Policies"
}

@app.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest):
    """
    Core route matching Question > Intent Context > Qdrant Results.
    Uses 'user_type' to enforce a strict category filter if matches in the USER_TYPE_MAP.
    Falls back to a global search context universally if not categorizable.
    """
    try:
        category_filter = None
        
        # 1. Apply Intent Context Filtering
        if request.user_type:
            user_intent = request.user_type.lower()
            if user_intent in USER_TYPE_MAP:
                category_filter = USER_TYPE_MAP[user_intent]
                logger.info(f"Mapped user_type '{user_intent}' -> Indexing Category '{category_filter}'")
            else:
                logger.warning(f"Unknown user_type '{request.user_type}', initiating fallback to global context.")
                
        # 2. Execute RAG Retrieval
        results = retriever.search(
            query=request.question,
            category_filter=category_filter,
            top_k=3
        )
        
        return {"results": results}
    
    except Exception as e:
        logger.error(f"Failed handling request: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Search failed at the vector service layer.")

if __name__ == "__main__":
    import uvicorn
    # Ready to be initialized individually
    uvicorn.run("retriever:app", host="0.0.0.0", port=8000, reload=True)
