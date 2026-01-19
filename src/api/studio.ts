/**
 * Studio API Client
 *
 * Handles all communication with Studio backend endpoints.
 */

import { apiClient } from "../utils/apiClient";

// ============================================================
// Types
// ============================================================

export interface StudioSession {
  id: string;
  user_id: string;
  name: string;
  total_generations: number;
  total_spent: number;
  is_archived: boolean;
  is_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface StudioGeneration {
  id: string;
  user_id: string;
  session_id: string;
  type: "video" | "image" | "audio";
  model: string;
  prompt: string | null;
  config: Record<string, unknown>;
  status: "queued" | "processing" | "completed" | "failed" | "expired";
  progress: number;
  error_message: string | null;
  result_url: string | null;
  thumbnail_url: string | null;
  duration_seconds: number | null;
  file_size_bytes: number | null;
  has_audio: boolean;
  position_x: number | null;
  position_y: number | null;
  cost_amount: number;
  created_at: string;
  updated_at: string;
  expires_at: string;
}

export interface StudioModel {
  id: string;
  name: string;
  type: "video" | "image" | "audio";
  base_price: number;
  price_multipliers: Record<string, Record<string, number>>;
  max_duration_seconds: number | null;
  supported_resolutions: string[] | null;
  capabilities: {
    supports_audio?: boolean;
    supports_extend?: boolean;
    supports_image_to_video?: boolean;
    custom_options?: CustomOption[];
  };
  is_active: boolean;
}

export interface CustomOption {
  id: string;
  type: "boolean" | "select" | "text" | "number";
  label: string;
  options?: string[];
  default?: unknown;
}

export interface GenerateRequest {
  model_id: string;
  prompt: string;
  session_id?: string;
  config?: {
    resolution?: string;
    duration_seconds?: number;
    aspect_ratio?: string;
    custom_params?: Record<string, unknown>;
  };
}

export interface GenerateResponse {
  success: boolean;
  generation_id: string;
  status: string;
  cost: number;
}

// ============================================================
// API Functions
// ============================================================

const BASE_PATH = "/api/webapp/studio";

/**
 * Sessions API
 */
export const sessionsApi = {
  /**
   * Get all user sessions
   */
  async getSessions(includeArchived = false): Promise<{
    sessions: StudioSession[];
    default_session_id: string | null;
  }> {
    const params = includeArchived ? "?include_archived=true" : "";
    const response = await apiClient.get(`${BASE_PATH}/sessions${params}`);
    return response.data;
  },

  /**
   * Create new session
   */
  async createSession(name = "Новый проект"): Promise<{
    success: boolean;
    session: StudioSession;
  }> {
    const response = await apiClient.post(`${BASE_PATH}/sessions`, { name });
    return response.data;
  },

  /**
   * Update session (rename, archive)
   */
  async updateSession(
    sessionId: string,
    updates: { name?: string; is_archived?: boolean }
  ): Promise<{ success: boolean; session: StudioSession }> {
    const response = await apiClient.patch(`${BASE_PATH}/sessions/${sessionId}`, updates);
    return response.data;
  },

  /**
   * Delete session
   */
  async deleteSession(sessionId: string, hardDelete = false): Promise<{ success: boolean }> {
    const params = hardDelete ? "?hard_delete=true" : "";
    const response = await apiClient.delete(`${BASE_PATH}/sessions/${sessionId}${params}`);
    return response.data;
  },
};

/**
 * Generations API
 */
export const generationsApi = {
  /**
   * Get generations (optionally filtered by session)
   */
  async getGenerations(
    sessionId?: string,
    limit = 50,
    offset = 0
  ): Promise<{ generations: StudioGeneration[] }> {
    const params = new URLSearchParams();
    if (sessionId) {
      params.set("session_id", sessionId);
    }
    params.set("limit", String(limit));
    params.set("offset", String(offset));

    const response = await apiClient.get(`${BASE_PATH}/generations?${params.toString()}`);
    return response.data;
  },

  /**
   * Get single generation
   */
  async getGeneration(generationId: string): Promise<{ generation: StudioGeneration }> {
    const response = await apiClient.get(`${BASE_PATH}/generations/${generationId}`);
    return response.data;
  },

  /**
   * Start new generation
   */
  async generate(request: GenerateRequest): Promise<GenerateResponse> {
    const response = await apiClient.post(`${BASE_PATH}/generate`, request);
    return response.data;
  },

  /**
   * Move generation to another session
   */
  async moveGeneration(
    generationId: string,
    targetSessionId: string,
    copy = false
  ): Promise<{ success: boolean; generation_id: string; new_session_id: string }> {
    const response = await apiClient.post(`${BASE_PATH}/generations/${generationId}/move`, {
      target_session_id: targetSessionId,
      copy,
    });
    return response.data;
  },
};

/**
 * Models API
 */
export const modelsApi = {
  /**
   * Get available models with pricing
   */
  async getModels(): Promise<{ models: StudioModel[] }> {
    const response = await apiClient.get(`${BASE_PATH}/models`);
    return response.data;
  },

  /**
   * Get capabilities for specific model
   */
  async getCapabilities(modelId: string): Promise<{
    capabilities: StudioModel["capabilities"];
  }> {
    const response = await apiClient.get(`${BASE_PATH}/models/${modelId}/capabilities`);
    return response.data;
  },

  /**
   * Calculate price for generation config
   */
  async calculatePrice(
    modelId: string,
    config: Record<string, unknown>
  ): Promise<{ price: number; currency: string }> {
    const response = await apiClient.post(`${BASE_PATH}/models/${modelId}/calculate-price`, config);
    return response.data;
  },
};

/**
 * Combined Studio API
 */
export const studioApi = {
  sessions: sessionsApi,
  generations: generationsApi,
  models: modelsApi,
};

export default studioApi;
