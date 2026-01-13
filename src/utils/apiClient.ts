/**
 * API Client Utility
 *
 * Standalone fetch wrapper for use outside React components.
 * For React components, use useApi() hook instead.
 */

import { API } from "../config";
import { getApiHeaders } from "./apiHeaders";
import { logger } from "./logger";

interface ApiClientOptions extends RequestInit {
  headers?: Record<string, string>;
}

// Helper to extract error message from response (reduces cognitive complexity)
async function extractErrorMessage(response: Response): Promise<string> {
  let errorMessage = `HTTP ${response.status}`;

  try {
    const errorData = await response.json();
    errorMessage = errorData.detail || errorData.error || errorData.message || errorMessage;
  } catch {
    try {
      const textError = await response.text();
      if (textError && textError.length < 200) {
        errorMessage = textError;
      }
    } catch {
      // Ignore
    }
  }

  return errorMessage;
}

// Helper to handle specific HTTP status codes (reduces cognitive complexity)
function handleSpecificStatusCodes(status: number, errorMessage: string): string {
  if (status === 429) {
    const cleaned = errorMessage.replace(/^CrystalPay API error:\s*/i, "");
    if (!cleaned || cleaned === `HTTP ${status}`) {
      return "Слишком много запросов. Подождите минуту и попробуйте снова.";
    }
    return cleaned;
  }
  if (status === 502 || status === 503) {
    return "Платёжная система временно недоступна. Попробуйте позже.";
  }
  return errorMessage;
}

// Helper to parse response data (reduces cognitive complexity)
async function parseResponseData<T>(response: Response, endpoint: string): Promise<T> {
  try {
    return await response.json();
  } catch {
    logger.warn("API returned non-JSON response", { endpoint });
    return {} as T;
  }
}

// Helper to build request URL (reduces cognitive complexity)
function buildRequestUrl(endpoint: string): string {
  if (endpoint.startsWith("http") || endpoint.startsWith("/api/")) {
    return endpoint;
  }
  return `${API.BASE_URL}${endpoint}`;
}

/**
 * Make API request (for use outside React components)
 *
 * @param endpoint - API endpoint path (relative to BASE_URL) or full URL
 * @param options - Fetch options (method, body, headers, etc.)
 * @returns Promise resolving to response data
 * @throws Error with user-friendly message on failure
 *
 * @example
 * ```ts
 * const data = await apiRequest<User>('/profile');
 * const result = await apiPost<Order>('/orders', orderData);
 * ```
 */
export async function apiRequest<T = unknown>(
  endpoint: string,
  options: ApiClientOptions = {}
): Promise<T> {
  const url = buildRequestUrl(endpoint);

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...getApiHeaders(),
        ...options.headers,
      },
    });

    if (!response.ok) {
      const errorMessage = await extractErrorMessage(response);
      const finalErrorMessage = handleSpecificStatusCodes(response.status, errorMessage);
      logger.error("API request failed", { endpoint, status: response.status, errorMessage: finalErrorMessage });
      throw new Error(finalErrorMessage);
    }

    return await parseResponseData<T>(response, endpoint);
  } catch (err) {
    logger.error("API request error", { endpoint, error: err });
    throw err;
  }
}

/**
 * GET request
 *
 * @param endpoint - API endpoint path
 * @returns Promise resolving to response data
 */
export async function apiGet<T = unknown>(endpoint: string): Promise<T> {
  return apiRequest<T>(endpoint, { method: "GET" });
}

/**
 * POST request
 */
export async function apiPost<T = unknown>(endpoint: string, body: unknown): Promise<T> {
  return apiRequest<T>(endpoint, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/**
 * PUT request
 *
 * @param endpoint - API endpoint path
 * @param body - Request body (will be JSON stringified)
 * @returns Promise resolving to response data
 */
export async function apiPut<T = unknown>(endpoint: string, body: unknown): Promise<T> {
  return apiRequest<T>(endpoint, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

/**
 * PATCH request
 *
 * @param endpoint - API endpoint path
 * @param body - Request body (will be JSON stringified)
 * @returns Promise resolving to response data
 */
export async function apiPatch<T = unknown>(endpoint: string, body: unknown): Promise<T> {
  return apiRequest<T>(endpoint, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

/**
 * DELETE request
 *
 * @param endpoint - API endpoint path
 * @returns Promise resolving to response data
 */
export async function apiDelete<T = unknown>(endpoint: string): Promise<T> {
  return apiRequest<T>(endpoint, { method: "DELETE" });
}
