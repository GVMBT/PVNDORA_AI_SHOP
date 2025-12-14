"""
RAG Module - Semantic Product Search via Supabase REST API

Uses pgvector through Supabase PostgREST - no direct DB connection needed.
Works with Supabase Connection Pooler (Transaction mode).
"""

import os
from typing import Optional, List

from core.logging import get_logger
from core.services.database import get_database

logger = get_logger(__name__)


# Environment
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")

# Embedding settings
EMBEDDING_DIMENSION = 768  # Gemini text-embedding-004
EMBEDDING_MODEL = "text-embedding-004"

# Singletons
_embedding_client = None


async def get_embedding(text: str) -> List[float]:
    """
    Generate embedding for text using Gemini.
    
    Returns 768-dimensional vector.
    """
    global _embedding_client
    
    if not GEMINI_API_KEY:
        return []
    
    try:
        from google import genai
        
        if _embedding_client is None:
            _embedding_client = genai.Client(api_key=GEMINI_API_KEY)
        
        # Note: model name without "models/" prefix
        response = _embedding_client.models.embed_content(
            model=EMBEDDING_MODEL,
            contents=text  # 'contents' not 'content'
        )
        
        # Response structure: response.embeddings[0].values
        if response.embeddings and len(response.embeddings) > 0:
            return list(response.embeddings[0].values)
        
        return []
        
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}", exc_info=True)
        return []


class ProductSearch:
    """
    Semantic product search using pgvector via Supabase REST API.
    
    Features:
    - Natural language queries ("I need to make presentations")
    - Automatic embedding generation
    - Similarity scoring
    
    Uses Supabase RPC function search_products_semantic() for vector search.
    """
    
    def __init__(self):
        self._db = None
        self._initialized = False
    
    @property
    def db(self):
        """Lazy database initialization."""
        if self._db is None:
            self._db = get_database()
        return self._db
    
    @property
    def is_available(self) -> bool:
        """Check if RAG search is available."""
        return bool(GEMINI_API_KEY)
    
    async def index_product(
        self,
        product_id: str,
        name: str,
        description: str,
        product_type: str,
        instructions: Optional[str] = None
    ) -> bool:
        """
        Index a product for semantic search.
        
        Creates/updates embedding in product_embeddings table.
        """
        if not self.is_available:
            logger.warning("RAG not available: missing GEMINI_API_KEY")
            return False
        
        # Build text for embedding
        text_parts = [name]
        if description:
            text_parts.append(description)
        if instructions:
            text_parts.append(instructions)
        
        content = " | ".join(text_parts)
        
        # Generate embedding
        embedding = await get_embedding(content)
        
        if not embedding:
            logger.warning(f"Failed to generate embedding for {name}")
            return False
        
        try:
            # Format embedding as PostgreSQL vector string
            embedding_str = f"[{','.join(map(str, embedding))}]"
            
            # Upsert embedding (sync client, no await)
            self.db.client.table("product_embeddings").upsert({
                "product_id": product_id,
                "content": content,
                "embedding": embedding_str
            }, on_conflict="product_id").execute()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to index product {product_id}: {e}", exc_info=True)
            return False
    
    async def search(
        self,
        query: str,
        limit: int = 5,
        similarity_threshold: float = 0.3
    ) -> List[dict]:
        """
        Search products by semantic similarity.
        
        Args:
            query: Natural language search query
            limit: Maximum results
            similarity_threshold: Minimum similarity score (0-1)
        
        Returns:
            List of matching products with similarity scores
        """
        if not self.is_available:
            return []
        
        # Generate query embedding
        query_embedding = await get_embedding(query)
        
        if not query_embedding:
            return []
        
        try:
            # Format as PostgreSQL vector
            embedding_str = f"[{','.join(map(str, query_embedding))}]"
            
            # Call RPC function for vector search (sync client)
            result = self.db.client.rpc(
                "search_products_semantic",
                {
                    "query_embedding": embedding_str,
                    "match_count": limit,
                    "similarity_threshold": similarity_threshold
                }
            ).execute()
            
            if not result.data:
                return []
            
            # Format results
            products = []
            for row in result.data:
                products.append({
                    "product_id": row["product_id"],
                    "name": row["product_name"],
                    "price": row["product_price"],
                    "type": row["product_type"],
                    "score": row["similarity"]
                })
            
            return products
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}", exc_info=True)
            return []
    
    async def index_all_products(self) -> int:
        """
        Index all active products.
        
        Returns number of products indexed.
        """
        try:
            # Sync client, no await
            result = self.db.client.table("products").select(
                "id, name, description, type, instructions"
            ).eq("status", "active").execute()
            
            if not result.data:
                logger.info("No active products found")
                return 0
            
            logger.info(f"Found {len(result.data)} products to index")
            
            indexed = 0
            for product in result.data:
                success = await self.index_product(
                    product_id=product["id"],
                    name=product["name"],
                    description=product.get("description", ""),
                    product_type=product["type"],
                    instructions=product.get("instructions", "")
                )
                if success:
                    indexed += 1
            
            return indexed
            
        except Exception as e:
            logger.error(f"Failed to index products: {e}", exc_info=True)
            return 0
    
    async def delete_product(self, product_id: str) -> bool:
        """Remove product from search index."""
        try:
            # Sync client
            self.db.client.table("product_embeddings").delete().eq(
                "product_id", product_id
            ).execute()
            return True
        except Exception:
            return False


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
        score_pct = int(p['score'] * 100)
        lines.append(f"- {p['name']} (ID: {p['product_id']}, {p['price']}₽, {score_pct}% match)")
    
    return "\n".join(lines)
