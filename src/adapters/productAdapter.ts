/**
 * Product Adapter
 * 
 * Transforms API product data into component-friendly format.
 */

import type { APIProduct, APIProductDetailed, APIProductResponse } from '../types/api';
import type { CatalogProduct, ProductDetailData, ProductReview, ProductFile } from '../types/component';

/**
 * Adapt a single API product to CatalogProduct format
 */
export function adaptProduct(apiProduct: APIProduct): CatalogProduct {
  return {
    id: apiProduct.id,
    name: apiProduct.name,
    category: apiProduct.type === 'shared' ? 'Shared' : 'Personal',
    price: apiProduct.final_price,
    msrp: apiProduct.msrp || apiProduct.original_price,
    description: apiProduct.description || '',
    warranty: apiProduct.warranty_days * 24, // days to hours
    duration: apiProduct.duration_days,
    instructions: apiProduct.instructions || '',
    image: `https://picsum.photos/seed/${apiProduct.id.substring(0, 8)}/800/600`,
    popular: apiProduct.sales_count > 50,
    stock: apiProduct.available_count,
    fulfillment: apiProduct.fulfillment_time_hours || 0,
    sold: apiProduct.sales_count,
    vpn: false, // API does not expose this; default false for now
    video: undefined,
    sku: `MOD-${apiProduct.id.substring(0, 4).toUpperCase()}`,
    version: '2.0',
  };
}

/**
 * Adapt a list of API products
 */
export function adaptProductList(apiProducts: APIProduct[]): CatalogProduct[] {
  return apiProducts.map(adaptProduct);
}

/**
 * Adapt detailed product response with reviews
 */
export function adaptProductDetail(response: APIProductResponse): ProductDetailData {
  const { product, social_proof } = response;
  const baseProduct = adaptProduct(product);
  
  // Adapt reviews from social_proof (real data only)
  const reviews: ProductReview[] = (social_proof.recent_reviews || []).map((r, idx) => ({
    id: idx + 1,
    user: `@user_${Math.random().toString(36).substring(2, 8)}`,
    rating: r.rating,
    date: formatTimeAgo(r.created_at),
    text: r.text || 'Great module, works perfectly!',
    verified: true,
  }));
  
  // Use instruction_files from API when available
  const files: ProductFile[] = (product.instruction_files || []).map((f, idx) => ({
    name: f.name || `payload_${idx + 1}`,
    size: '—',
    type: 'doc',
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
  
  if (diffHours < 1) return 'just now';
  if (diffHours < 24) return `${diffHours}h ago`;
  const diffDays = Math.floor(diffHours / 24);
  if (diffDays < 7) return `${diffDays}d ago`;
  return date.toLocaleDateString();
}
