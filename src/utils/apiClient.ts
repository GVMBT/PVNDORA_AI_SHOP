/**
 * API Client Utility
 * 
 * Standalone fetch wrapper for use outside React components.
 * For React components, use useApi() hook instead.
 */

import { API } from '../config';
import { getApiHeaders } from './apiHeaders';
import { logger } from './logger';

interface ApiClientOptions extends RequestInit {
  headers?: Record<string, string>;
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
  const url = endpoint.startsWith('http') ? endpoint : `${API.BASE_URL}${endpoint}`;

  try {
    const response = await fetch(url, {
      ...options,
      headers: {
        ...getApiHeaders(),
        ...options.headers,
      },
    });

    if (!response.ok) {
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

      // Handle specific status codes
      if (response.status === 429) {
        errorMessage = errorMessage.replace(/^(1Plat|Rukassa) API error:\s*/i, '');
        if (!errorMessage || errorMessage === `HTTP ${response.status}`) {
          errorMessage = 'Слишком много запросов. Подождите минуту и попробуйте снова.';
        }
      } else if (response.status === 502 || response.status === 503) {
        errorMessage = 'Платёжная система временно недоступна. Попробуйте позже.';
      }

      logger.error('API request failed', { endpoint, status: response.status, errorMessage });
      throw new Error(errorMessage);
    }

    let data: T;
    try {
      data = await response.json();
    } catch {
      logger.warn('API returned non-JSON response', { endpoint });
      data = {} as T;
    }

    return data;
  } catch (err) {
    const errorMessage = err instanceof Error ? err.message : 'Unknown error';
    logger.error('API request error', { endpoint, error: err });
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
  return apiRequest<T>(endpoint, { method: 'GET' });
}

/**
 * POST request
 */
export async function apiPost<T = unknown>(endpoint: string, body: unknown): Promise<T> {
  return apiRequest<T>(endpoint, {
    method: 'POST',
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
    method: 'PUT',
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
    method: 'PATCH',
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
  return apiRequest<T>(endpoint, { method: 'DELETE' });
}








