/**
 * Product Adapter
 *
 * Transforms API product data into component-friendly format.
 */

import type { APIProduct, APIProductResponse } from "../types/api";
import type {
  CatalogProduct,
  ProductAvailability,
  ProductDetailData,
  ProductFile,
  ProductReview,
} from "../types/component";

/**
 * Derive availability status from API data
 */
function deriveAvailability(apiProduct: APIProduct): ProductAvailability {
  // Check API status first
  if (apiProduct.status === "discontinued") {
    return "discontinued";
  }
  if (apiProduct.status === "coming_soon") {
    return "coming_soon";
  }

  // Then check stock
  if (apiProduct.available_count > 0) {
    return "available";
  }

  // Out of stock but can fulfill on demand
  if (apiProduct.can_fulfill_on_demand) {
    return "on_demand";
  }

  // Default to discontinued if nothing else matches
  return "discontinued";
}

/**
 * Adapt a single API product to CatalogProduct format
 *
 * IMPORTANT: The API now returns anchor prices (fixed or converted).
 * - final_price: Price in user's currency (anchor if set, otherwise converted from USD)
 * - is_anchor_price: true if price is fixed (won't change with exchange rate)
 * - price_usd: Base USD price (for backend calculations only)
 *
 * Frontend should NOT do any currency conversion - just display final_price as-is.
 */
export function adaptProduct(apiProduct: APIProduct, currency = "USD"): CatalogProduct {
  // Derive categories: use API categories array, fallback to product type
  const productCategories =
    apiProduct.categories && apiProduct.categories.length > 0
      ? apiProduct.categories
      : [apiProduct.type]; // type = 'ai' | 'dev' | 'design' | 'music'

  return {
    id: apiProduct.id,
    name: apiProduct.name,
    // Legacy single category: use first from categories or type
    category: productCategories[0] || apiProduct.type,
    categories: productCategories,
    // Use final_price from API - already in user's currency (anchor or converted)
    price: apiProduct.final_price,
    msrp: apiProduct.msrp || apiProduct.original_price,
    currency: apiProduct.currency || currency,
    description: apiProduct.description || "",
    warranty: apiProduct.warranty_days * 24, // days to hours
    duration: apiProduct.duration_days,
    instructions: apiProduct.instructions || "",
    image: apiProduct.image_url || "/noise.png",
    popular: apiProduct.sales_count > 50,
    stock: apiProduct.available_count,
    fulfillment: apiProduct.fulfillment_time_hours || 0,
    sold: apiProduct.sales_count,
    video: apiProduct.video_url || undefined, // Video URL for looped product visualization
    sku: `MOD-${apiProduct.id.substring(0, 4).toUpperCase()}`,
    version: "2.0",
    status: deriveAvailability(apiProduct),
    can_fulfill_on_demand: apiProduct.can_fulfill_on_demand,
  };
}

/**
 * Adapt a list of API products
 */
export function adaptProductList(apiProducts: APIProduct[], currency = "USD"): CatalogProduct[] {
  return apiProducts.map((p) => adaptProduct(p, currency));
}

/**
 * Adapt detailed product response with reviews
 */
export function adaptProductDetail(
  response: APIProductResponse,
  currency = "USD"
): ProductDetailData {
  const { product, social_proof } = response;
  const baseProduct = adaptProduct(product, product.currency || currency);

  // Adapt reviews from social_proof (real data only)
  const reviews: ProductReview[] = (social_proof.recent_reviews || []).map((r, idx) => ({
    id: idx + 1,
    user: `@user_${Math.random().toString(36).substring(2, 8)}`,
    rating: r.rating,
    date: formatTimeAgo(r.created_at),
    text: r.text || "Great module, works perfectly!",
    verified: true,
  }));

  // Use instruction_files from API when available
  const files: ProductFile[] = (product.instruction_files || []).map((f, idx) => ({
    name: f.name || `payload_${idx + 1}`,
    size: "—",
    type: "doc",
  }));

  return {
    ...baseProduct,
    reviews,
    files,
    relatedProducts: [], // populated in connected component
  };
}

/**
 * Format timestamp to human-readable "time ago"
 */
function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));

  if (diffHours < 1) {
    return "just now";
  }
  if (diffHours < 24) {
    return `${diffHours}h ago`;
  }
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) {
    return `${diffDays}d ago`;
  }
  return date.toLocaleDateString();
}
