"""RAG Module - Semantic Product Search via Supabase REST API.

Uses pgvector through Supabase PostgREST - no direct DB connection needed.
Works with Supabase Connection Pooler (Transaction mode).
Embeddings via OpenRouter API (text-embedding-3-large).
"""

import os
from typing import TYPE_CHECKING, Any

import httpx

from core.logging import get_logger
from core.services.database import get_database

if TYPE_CHECKING:
    from core.services.database import Database

logger = get_logger(__name__)


# Environment
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY", "")

# OpenRouter Embeddings API
OPENROUTER_EMBEDDINGS_URL = "https://openrouter.ai/api/v1/embeddings"
EMBEDDING_MODEL = "text-embedding-3-large"  # OpenAI model via OpenRouter
EMBEDDING_DIMENSION = 3072  # text-embedding-3-large dimension

# Feature flag for vector search availability
VECS_AVAILABLE = bool(OPENROUTER_API_KEY)

# HTTP client singleton
_http_client: httpx.AsyncClient | None = None


def get_http_client() -> httpx.AsyncClient:
    """Get or create async HTTP client."""
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(timeout=30.0)
    return _http_client


async def get_embedding(text: str) -> list[float]:
    """Generate embedding for text using OpenRouter API.

    Uses text-embedding-3-large model (3072 dimensions).
    Reference: https://openrouter.ai/docs/api/api-reference/embeddings/create-embeddings
    """
    if not OPENROUTER_API_KEY:
        logger.warning("RAG not available: missing OPENROUTER_API_KEY")
        return []

    try:
        client = get_http_client()

        response = await client.post(
            OPENROUTER_EMBEDDINGS_URL,
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": os.environ.get("WEBAPP_URL", "https://pvndora.com"),
                "X-Title": "PVNDORA RAG Search",
            },
            json={
                "input": text,
                "model": EMBEDDING_MODEL,
            },
        )

        if response.status_code != 200:
            logger.error(
                f"OpenRouter embeddings API error: {response.status_code} - {response.text}",
            )
            return []

        data = response.json()

        # Response structure: { data: [{ embedding: [...], index: 0 }], ... }
        if data.get("data") and len(data["data"]) > 0:
            embedding_data = data["data"][0].get("embedding", [])
            if isinstance(embedding_data, list):
                return [float(x) for x in embedding_data]

        return []

    except Exception as e:
        logger.error("Embedding generation failed: %s", type(e).__name__, exc_info=True)
        return []


class ProductSearch:
    """Semantic product search using pgvector via Supabase REST API.

    Features:
    - Natural language queries ("I need to make presentations")
    - Automatic embedding generation
    - Similarity scoring

    Uses Supabase RPC function search_products_semantic() for vector search.
    """

    def __init__(self) -> None:
        self._db: Database | None = None
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
        return bool(OPENROUTER_API_KEY)

    async def index_product(
        self,
        product_id: str,
        name: str,
        description: str,
        instructions: str | None = None,
    ) -> bool:
        """Index a product for semantic search.

        Creates/updates embedding in product_embeddings table.
        """
        if not self.is_available:
            logger.warning("RAG not available: missing OPENROUTER_API_KEY")
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
            from core.logging import sanitize_string_for_logging

            logger.warning("Failed to generate embedding for %s", sanitize_string_for_logging(name))
            return False

        try:
            # Format embedding as PostgreSQL vector string
            embedding_str = f"[{','.join(map(str, embedding))}]"

            # Upsert embedding
            await (
                self.db.client.table("product_embeddings")
                .upsert(
                    {"product_id": product_id, "content": content, "embedding": embedding_str},
                    on_conflict="product_id",
                )
                .execute()
            )

            return True

        except Exception as e:
            from core.logging import sanitize_id_for_logging

            logger.error(
                "Failed to index product %s: %s",
                sanitize_id_for_logging(product_id),
                type(e).__name__,
                exc_info=True,
            )
            return False

    async def search(
        self,
        query: str,
        limit: int = 5,
        similarity_threshold: float = 0.3,
    ) -> list[dict[str, Any]]:
        """Search products by semantic similarity.

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
            result = await self.db.client.rpc(
                "search_products_semantic",
                {
                    "query_embedding": embedding_str,
                    "match_count": limit,
                    "similarity_threshold": similarity_threshold,
                },
            ).execute()

            if not result.data:
                return []

            # Format results
            products = []
            for row in result.data:
                products.append(
                    {
                        "product_id": row["product_id"],
                        "name": row["product_name"],
                        "price": row["product_price"],
                        "type": row["product_type"],
                        "score": row["similarity"],
                    },
                )

            return products

        except Exception as e:
            logger.error("Semantic search failed: %s", type(e).__name__, exc_info=True)
            return []

    async def index_all_products(self) -> int:
        """Index all active products.

        Returns number of products indexed.
        """
        try:
            # Fetch active products
            result = (
                await self.db.client.table("products")
                .select("id, name, description, type, instructions")
                .eq("status", "active")
                .execute()
            )

            if not result.data:
                logger.info("No active products found")
                return 0

            logger.info("Found %d products to index", len(result.data))

            indexed = 0
            for product in result.data:
                success = await self.index_product(
                    product_id=product["id"],
                    name=product["name"],
                    description=product.get("description", ""),
                    instructions=product.get("instructions", ""),
                )
                if success:
                    indexed += 1

            return indexed

        except Exception as e:
            logger.error("Failed to index products: %s", type(e).__name__, exc_info=True)
            return 0

    async def delete_product(self, product_id: str) -> bool:
        """Remove product from search index."""
        try:
            await (
                self.db.client.table("product_embeddings")
                .delete()
                .eq("product_id", product_id)
                .execute()
            )
            return True
        except Exception:
            return False


# Singleton
_product_search: ProductSearch | None = None


def get_product_search() -> ProductSearch:
    """Get ProductSearch singleton."""
    global _product_search
    if _product_search is None:
        _product_search = ProductSearch()
    return _product_search


async def search_products_for_ai(query: str, limit: int = 5) -> str:
    """Search products and format results for AI context.

    Used in AI function calling and system prompt.
    """
    search = get_product_search()
    results = await search.search(query, limit)

    if not results:
        return "No products found matching the query."

    lines = ["Found products:"]
    for p in results:
        score_pct = int(p["score"] * 100)
        lines.append(f"- {p['name']} (ID: {p['product_id']}, {p['price']}₽, {score_pct}% match)")

    return "\n".join(lines)
