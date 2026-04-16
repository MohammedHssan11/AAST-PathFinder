import json
import logging
from pathlib import Path
from typing import Any, Dict, List

from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer
from tqdm import tqdm

# Configure logging to console, adhering to FastAPI-ready practices (no raw prints)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


class DataLoader:
    """Handles loading and cleaning data from JSON files."""
    
    @staticmethod
    def load_and_clean_data(file_paths: List[str]) -> List[Dict[str, Any]]:
        """
        Reads multiple JSON files, cleans the data, and applies contextual enrichment.
        Args:
            file_paths: List of paths to JSON files.
        Returns:
            A list of dictionary objects containing 'text_to_embed' and 'payload'.
        """
        all_data = []
        for file_path in file_paths:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"File not found: {file_path}. Skipping.")
                continue

            try:
                with open(path, "r", encoding="utf-8") as file:
                    data = json.load(file)
                    
                    if not isinstance(data, list):
                        logger.warning(f"Expected a list of JSON objects in {file_path}, got {type(data)}. Skipping.")
                        continue
                        
                    for item in data:
                        # Cleaning: safe retrieval and trimming
                        title = item.get("title", "").strip()
                        category = item.get("category", "Uncategorized").strip()
                        content = item.get("content", "").strip()
                        tags = item.get("tags", [])
                        
                        if not content:
                            logger.debug(f"Skipping an entry due to missing content in {file_path}")
                            continue
                        
                        # Contextual Enrichment for better retrieval density
                        enriched_text = f"{title} [Category: {category}] {content}"
                        
                        processed_item = {
                            "text_to_embed": enriched_text,
                            "payload": {
                                "title": title,
                                "category": category,
                                "content": content,
                                "tags": tags
                            }
                        }
                        all_data.append(processed_item)
                logger.info(f"Successfully loaded and processed {file_path}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON decoding failed for {file_path}: {e}")
            except Exception as e:
                logger.error(f"Unexpected error processing {file_path}: {e}")
                
        return all_data


class Embedder:
    """Wrapper for generating embeddings using sentence-transformers."""
    
    def __init__(self, model_name: str = "BAAI/bge-m3", device: str = "cpu"):
        """
        Initializes the model.
        Args:
            model_name: The HuggingFace model hub name.
            device: Device to use for encoding ('cpu' or 'cuda').
        """
        logger.info(f"Loading embedding model: {model_name} on {device}")
        try:
            self.model = SentenceTransformer(model_name, device=device)
            logger.info("Model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load the model {model_name}: {e}")
            raise

    def batch_process(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Encodes a list of texts in batches to optimize memory and processing speed.
        Args:
            texts: List of strings to encode.
            batch_size: Number of texts per batch.
        Returns:
            List of vector embeddings as lists of floats.
        """
        logger.info(f"Encoding {len(texts)} texts in batches of {batch_size}...")
        try:
            embeddings = self.model.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=True,
                normalize_embeddings=True
            )
            # Ensure it returns native Python list of floats for Qdrant client compatibility
            return embeddings.tolist()
        except Exception as e:
            logger.error(f"Error during batch encoding: {e}")
            raise


class QdrantManager:
    """Manages Qdrant connection, collection setup, and data ingestion operations."""
    
    def __init__(self, host: str = "localhost", port: int = 6333, collection_name: str = "aast_cai_knowledge"):
        """
        Initializes the Qdrant client. Defaults to standard local docker settings.
        """
        self.collection_name = collection_name
        try:
            self.client = QdrantClient(host=host, port=port)
            logger.info(f"Connected to Qdrant at {host}:{port}")
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}")
            raise

    def setup_collection(self, vector_size: int = 1024):
        """
        Creates a collection with a strict configuration, optionally overwriting if existing.
        """
        logger.info(f"Setting up collection '{self.collection_name}' with vector size {vector_size}...")
        try:
            # Check if collection exists
            if self.client.collection_exists(self.collection_name):
                logger.info(f"Collection '{self.collection_name}' already exists. Recreating it.")
                self.client.delete_collection(collection_name=self.collection_name)
                
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=models.VectorParams(
                    size=vector_size,
                    distance=models.Distance.COSINE
                )
            )
            
            # Payload indexing for fast filtering on the category
            self.client.create_payload_index(
                collection_name=self.collection_name,
                field_name="category",
                field_schema=models.PayloadSchemaType.KEYWORD,
            )
            logger.info("Collection setup and payload indexing completed successfully.")
        except Exception as e:
            logger.error(f"Error setting up collection: {e}")
            raise

    def upsert_batches(self, embeddings: List[List[float]], payloads: List[Dict[str, Any]], batch_size: int = 50):
        """
        Uploads points to Qdrant in robust batches.
        """
        logger.info(f"Starting upsert loop for {len(embeddings)} points...")
        total_points = len(embeddings)
        
        # Use simple integer IDs starting from 1
        for i in tqdm(range(0, total_points, batch_size), desc="Upserting Vectors"):
            batch_embeddings = embeddings[i:i + batch_size]
            batch_payloads = payloads[i:i + batch_size]
            batch_ids = list(range(i + 1, i + len(batch_embeddings) + 1))
            
            try:
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=models.Batch(
                        ids=batch_ids,
                        payloads=batch_payloads,
                        vectors=batch_embeddings
                    )
                )
            except Exception as e:
                logger.error(f"Failed to upsert batch starting at index {i}: {e}")
                
        logger.info("Upsert loop completed.")

    def sanity_search(self, query_vector: List[float], top_k: int = 3):
        """
        Performs a sanity check search to ensure vectors are correctly stored
        and returning the expected payloads.
        """
        logger.info(f"Performing sanity search for top {top_k} results...")
        try:
            results = self.client.query_points(
                collection_name=self.collection_name,
                query=query_vector,
                limit=top_k
            ).points
            
            logger.info(f"Sanity search completed, found {len(results)} results.")
            for i, res in enumerate(results):
                logger.info(f"Result {i+1} | ID: {res.id} | Score: {res.score:.4f} "
                            f"| Title: {res.payload.get('title')} | Category: {res.payload.get('category')}")
            return results
        except Exception as e:
            logger.error(f"Error during sanity search: {e}")
            raise

def main():
    # =============== CONFIGURATION ===============
    # Using 'r' before the string ensures Windows backslashes are handled correctly.
    JSON_FILES = [
        r"C:\Users\mh978\Downloads\CAI_AAST\data_rag_cai\cai_msc.json",
        r"C:\Users\mh978\Downloads\CAI_AAST\data_rag_cai\CAI_rag3_cleaned.json"
    ]
    
    COLLECTION_NAME = "aast_cai_knowledge"
    VECTOR_DIMENSION = 1024       # Dimension for BAAI/bge-m3 dense vectors
    EMBEDDING_MODEL = "BAAI/bge-m3"
    UPSERT_BATCH_SIZE = 50
    ENCODE_BATCH_SIZE = 16        # Adjust to 32 or 64 if you have a GPU
    # =============================================
    
    logger.info("=== Starting Data Ingestion Pipeline for RAG ===")
    
    try:
        # Phase 1: Load and Clean Data
        logger.info("--- Phase 1: Data Loading ---")
        # The DataLoader class will use the absolute paths provided above
        processed_data = DataLoader.load_and_clean_data(JSON_FILES)
        
        if not processed_data:
            logger.error("No valid data found or processed. Pipeline exiting.")
            return
            
        texts_to_embed = [item["text_to_embed"] for item in processed_data]
        payloads = [item["payload"] for item in processed_data]
        logger.info(f"Total documents to ingest: {len(texts_to_embed)}")
        
        # Phase 2: Instantiating Models & Generating Embeddings
        logger.info("--- Phase 2: Embedding Generation ---")
        # Tip: Change device to 'cuda' if you have an NVIDIA GPU installed
        embedder = Embedder(model_name=EMBEDDING_MODEL, device="cpu") 
        embeddings = embedder.batch_process(texts_to_embed, batch_size=ENCODE_BATCH_SIZE)
        
        # Phase 3: Initializing Vector Store and Ingesting
        logger.info("--- Phase 3: Vector Store Ingestion ---")
        qdrant_manager = QdrantManager(collection_name=COLLECTION_NAME)
        
        # setup_collection will delete the old collection and create a fresh one
        qdrant_manager.setup_collection(vector_size=VECTOR_DIMENSION)
        qdrant_manager.upsert_batches(embeddings, payloads, batch_size=UPSERT_BATCH_SIZE)
        
        # Phase 4: Validating Upload (Sanity Search)
        logger.info("--- Phase 4: Validation ---")
        if payloads:
            logger.info(f"Target query check: {payloads[0].get('title')}")
            sample_query_vector = embeddings[0]
            qdrant_manager.sanity_search(query_vector=sample_query_vector, top_k=3)
        
        logger.info("=== Data Ingestion Pipeline Execution Completed Successfully ===")
        
    except Exception as e:
        logger.critical(f"Data ingestion pipeline failed: {e}", exc_info=True)


if __name__ == "__main__":
    main()