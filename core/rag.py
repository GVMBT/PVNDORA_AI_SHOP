"""
RAG Module - Vector Search Pipeline

Provides semantic search for products using pgvector/vecs:
- Product embedding generation
- Similarity search
- Context retrieval for AI
"""

import os
from typing import Optional, List
from functools import lru_cache

# Safe import - RAG is optional
try:
    import vecs
    from vecs import Collection
    VECS_AVAILABLE = True
except ImportError:
    VECS_AVAILABLE = False
    vecs = None
    Collection = None

from core.ai import get_ai_consultant


# Environment
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

# Collection settings
PRODUCTS_COLLECTION = "products"
EMBEDDING_DIMENSION = 768  # Gemini text-embedding-004

# Singleton
_vecs_client = None
_products_collection: Optional[Collection] = None


def get_vecs_client():
    """Get vecs client (singleton)."""
    global _vecs_client
    
    if not VECS_AVAILABLE:
        raise ImportError("vecs library not installed. Install with: pip install vecs")
    
    if _vecs_client is None:
        # Extract connection string from Supabase URL
        # Format: postgresql://postgres:[password]@[host]:5432/postgres
        if not SUPABASE_URL:
            raise ValueError("SUPABASE_URL must be set for vector search")
        
        # Convert Supabase URL to PostgreSQL connection string
        # SUPABASE_URL is typically https://xxx.supabase.co
        # We need to construct the DB connection string
        db_host = SUPABASE_URL.replace("https://", "").replace("http://", "")
        db_password = SUPABASE_SERVICE_ROLE_KEY
        
        # Supabase DB connection format
        connection_string = f"postgresql://postgres.{db_host.split('.')[0]}:{db_password}@aws-0-us-east-1.pooler.supabase.com:6543/postgres"
        
        # Alternative: use direct connection string from env
        db_url = os.environ.get("SUPABASE_DB_URL")
        if db_url:
            connection_string = db_url
        
        _vecs_client = vecs.create_client(connection_string)
    
    return _vecs_client


def get_products_collection() -> Collection:
    """Get or create products vector collection."""
    global _products_collection
    
    if _products_collection is None:
        client = get_vecs_client()
        _products_collection = client.get_or_create_collection(
            name=PRODUCTS_COLLECTION,
            dimension=EMBEDDING_DIMENSION
        )
    
    return _products_collection


class ProductSearch:
    """
    Semantic product search using vector embeddings.
    
    Features:
    - Natural language queries ("I need to make presentations")
    - Metadata filtering (type, status, price range)
    - Similarity scoring
    """
    
    def __init__(self):
        self.collection = get_products_collection()
        self.ai = get_ai_consultant()
    
    async def index_product(
        self,
        product_id: str,
        name: str,
        description: str,
        product_type: str,
        instructions: Optional[str] = None,
        status: str = "active"
    ) -> bool:
        """
        Index a product for semantic search.
        
        Args:
            product_id: Product UUID
            name: Product name
            description: Product description
            product_type: Type (student, trial, shared, key)
            instructions: Usage instructions
            status: Product status
        
        Returns:
            True if indexed successfully
        """
        # Build text for embedding
        text_parts = [name]
        if description:
            text_parts.append(description)
        if instructions:
            text_parts.append(instructions)
        
        text = " | ".join(text_parts)
        
        # Generate embedding
        embedding = await self.ai.generate_embedding(text)
        
        # Metadata for filtering
        metadata = {
            "product_id": product_id,
            "name": name,
            "type": product_type,
            "status": status
        }
        
        # Upsert to collection
        self.collection.upsert(
            records=[
                (product_id, embedding, metadata)
            ]
        )
        
        return True
    
    async def search(
        self,
        query: str,
        limit: int = 5,
        filters: Optional[dict] = None
    ) -> List[dict]:
        """
        Search products by semantic similarity.
        
        Args:
            query: Natural language search query
            limit: Maximum results
            filters: Metadata filters (e.g., {"status": {"$eq": "active"}})
        
        Returns:
            List of matching products with scores
        """
        # Generate query embedding
        query_embedding = await self.ai.generate_embedding(query)
        
        # Default filter: only active products
        if filters is None:
            filters = {"status": {"$eq": "active"}}
        
        # Search
        results = self.collection.query(
            data=query_embedding,
            limit=limit,
            filters=filters,
            include_metadata=True,
            include_value=True
        )
        
        # Format results
        products = []
        for result in results:
            product_id, score, metadata = result
            products.append({
                "product_id": product_id,
                "name": metadata.get("name", ""),
                "type": metadata.get("type", ""),
                "score": float(score) if score else 0.0
            })
        
        return products
    
    async def find_similar(
        self,
        product_id: str,
        limit: int = 3
    ) -> List[dict]:
        """
        Find products similar to a given product.
        
        Args:
            product_id: Reference product UUID
            limit: Maximum results
        
        Returns:
            List of similar products
        """
        # Get the product's embedding
        results = self.collection.fetch([product_id])
        
        if not results:
            return []
        
        # Use the embedding to find similar
        embedding = results[0][1]  # (id, embedding, metadata)
        
        # Search excluding the original
        similar = self.collection.query(
            data=embedding,
            limit=limit + 1,  # +1 to exclude self
            filters={"status": {"$eq": "active"}},
            include_metadata=True
        )
        
        # Filter out the original product
        products = []
        for result in similar:
            pid, score, metadata = result
            if pid != product_id:
                products.append({
                    "product_id": pid,
                    "name": metadata.get("name", ""),
                    "type": metadata.get("type", ""),
                    "score": float(score) if score else 0.0
                })
        
        return products[:limit]
    
    async def delete_product(self, product_id: str) -> bool:
        """Remove product from search index."""
        self.collection.delete([product_id])
        return True
    
    def create_index(self):
        """
        Create HNSW index for fast similarity search.
        
        Call once after initial data load.
        """
        self.collection.create_index(
            method=vecs.IndexMethod.hnsw,
            measure=vecs.IndexMeasure.cosine_distance
        )


# Singleton
_product_search: Optional[ProductSearch] = None


def get_product_search() -> ProductSearch:
    """Get ProductSearch singleton."""
    global _product_search
    if _product_search is None:
        _product_search = ProductSearch()
    return _product_search


async def search_products_for_ai(query: str, limit: int = 5) -> str:
    """
    Search products and format results for AI context.
    
    Used in AI function calling and system prompt.
    """
    search = get_product_search()
    results = await search.search(query, limit)
    
    if not results:
        return "No products found matching the query."
    
    lines = ["Found products:"]
    for p in results:
        lines.append(f"- {p['name']} (ID: {p['product_id']}, Type: {p['type']})")
    
    return "\n".join(lines)

