/**
 * Studio Zustand Store
 * 
 * Manages all Studio state including sessions, generations, and UI state.
 */

import { create } from "zustand";
import { devtools, subscribeWithSelector } from "zustand/middleware";
import {
  generationsApi,
  modelsApi,
  sessionsApi,
  type GenerateRequest,
  type StudioGeneration,
  type StudioModel,
  type StudioSession,
} from "../api/studio";

// ============================================================
// Types
// ============================================================

export type ViewMode = "feed" | "canvas";
export type GenerationStatus = "idle" | "loading" | "generating" | "error";

interface StudioState {
  // Sessions
  sessions: StudioSession[];
  activeSessionId: string | null;
  sessionsLoading: boolean;
  
  // Generations
  generations: StudioGeneration[];
  generationsLoading: boolean;
  activeGenerationId: string | null;
  
  // Models
  models: StudioModel[];
  modelsLoading: boolean;
  activeModelId: string;
  
  // Generation in progress
  generationStatus: GenerationStatus;
  generationError: string | null;
  
  // UI State
  viewMode: ViewMode;
  sidebarOpen: boolean;
  
  // Prompt
  prompt: string;
  config: Record<string, unknown>;
}

interface StudioActions {
  // Sessions
  fetchSessions: () => Promise<void>;
  createSession: (name?: string) => Promise<StudioSession | null>;
  renameSession: (sessionId: string, name: string) => Promise<void>;
  deleteSession: (sessionId: string) => Promise<void>;
  setActiveSession: (sessionId: string) => void;
  
  // Generations
  fetchGenerations: (sessionId?: string) => Promise<void>;
  startGeneration: (request?: Partial<GenerateRequest>) => Promise<string | null>;
  setActiveGeneration: (generationId: string | null) => void;
  updateGeneration: (generationId: string, updates: Partial<StudioGeneration>) => void;
  
  // Models
  fetchModels: () => Promise<void>;
  setActiveModel: (modelId: string) => void;
  calculatePrice: () => Promise<number>;
  
  // UI
  setViewMode: (mode: ViewMode) => void;
  toggleSidebar: () => void;
  setPrompt: (prompt: string) => void;
  setConfig: (key: string, value: unknown) => void;
  resetConfig: () => void;
  
  // Reset
  reset: () => void;
}

type StudioStore = StudioState & StudioActions;

// ============================================================
// Initial State
// ============================================================

const initialState: StudioState = {
  sessions: [],
  activeSessionId: null,
  sessionsLoading: false,
  
  generations: [],
  generationsLoading: false,
  activeGenerationId: null,
  
  models: [],
  modelsLoading: false,
  activeModelId: "veo-3.1",
  
  generationStatus: "idle",
  generationError: null,
  
  viewMode: "feed",
  sidebarOpen: false,
  
  prompt: "",
  config: {
    resolution: "720p",
    aspect_ratio: "16:9",
  },
};

// ============================================================
// Store
// ============================================================

export const useStudioStore = create<StudioStore>()(
  devtools(
    subscribeWithSelector((set, get) => ({
      ...initialState,

      // --------------------------------------------------------
      // Sessions
      // --------------------------------------------------------
      
      fetchSessions: async () => {
        set({ sessionsLoading: true });
        try {
          const { sessions, default_session_id } = await sessionsApi.getSessions();
          set({
            sessions,
            activeSessionId: get().activeSessionId || default_session_id || sessions[0]?.id || null,
            sessionsLoading: false,
          });
        } catch (error) {
          console.error("Failed to fetch sessions:", error);
          set({ sessionsLoading: false });
        }
      },

      createSession: async (name = "Новый проект") => {
        try {
          const { session } = await sessionsApi.createSession(name);
          set((state) => ({
            sessions: [session, ...state.sessions],
            activeSessionId: session.id,
          }));
          return session;
        } catch (error) {
          console.error("Failed to create session:", error);
          return null;
        }
      },

      renameSession: async (sessionId, name) => {
        try {
          await sessionsApi.updateSession(sessionId, { name });
          set((state) => ({
            sessions: state.sessions.map((s) =>
              s.id === sessionId ? { ...s, name } : s
            ),
          }));
        } catch (error) {
          console.error("Failed to rename session:", error);
        }
      },

      deleteSession: async (sessionId) => {
        try {
          await sessionsApi.deleteSession(sessionId);
          set((state) => {
            const filtered = state.sessions.filter((s) => s.id !== sessionId);
            return {
              sessions: filtered,
              activeSessionId:
                state.activeSessionId === sessionId
                  ? filtered[0]?.id || null
                  : state.activeSessionId,
            };
          });
        } catch (error) {
          console.error("Failed to delete session:", error);
        }
      },

      setActiveSession: (sessionId) => {
        set({ activeSessionId: sessionId, activeGenerationId: null });
        get().fetchGenerations(sessionId);
      },

      // --------------------------------------------------------
      // Generations
      // --------------------------------------------------------

      fetchGenerations: async (sessionId) => {
        const targetSession = sessionId || get().activeSessionId;
        if (!targetSession) return;

        set({ generationsLoading: true });
        try {
          const { generations } = await generationsApi.getGenerations(targetSession);
          set({ generations, generationsLoading: false });
        } catch (error) {
          console.error("Failed to fetch generations:", error);
          set({ generationsLoading: false });
        }
      },

      startGeneration: async (requestOverrides = {}) => {
        const state = get();
        
        if (!state.prompt.trim() && !requestOverrides.prompt) {
          set({ generationError: "Введите промпт" });
          return null;
        }

        set({ generationStatus: "generating", generationError: null });

        const request: GenerateRequest = {
          model_id: requestOverrides.model_id || state.activeModelId,
          prompt: requestOverrides.prompt || state.prompt,
          session_id: requestOverrides.session_id || state.activeSessionId || undefined,
          config: {
            ...state.config,
            ...requestOverrides.config,
          },
        };

        try {
          const response = await generationsApi.generate(request);
          
          if (response.success) {
            // Add placeholder generation to list
            const newGeneration: StudioGeneration = {
              id: response.generation_id,
              user_id: "",
              session_id: state.activeSessionId || "",
              type: state.models.find((m) => m.id === request.model_id)?.type || "video",
              model: request.model_id,
              prompt: request.prompt,
              config: request.config || {},
              status: "processing",
              progress: 0,
              error_message: null,
              result_url: null,
              thumbnail_url: null,
              duration_seconds: null,
              file_size_bytes: null,
              has_audio: false,
              position_x: null,
              position_y: null,
              cost_amount: response.cost,
              created_at: new Date().toISOString(),
              updated_at: new Date().toISOString(),
              expires_at: new Date(Date.now() + 30 * 24 * 60 * 60 * 1000).toISOString(),
            };

            set((s) => ({
              generations: [newGeneration, ...s.generations],
              activeGenerationId: response.generation_id,
              generationStatus: "idle",
              prompt: "", // Clear prompt after successful generation
            }));

            return response.generation_id;
          }
          
          set({ generationStatus: "error", generationError: "Generation failed" });
          return null;
        } catch (error) {
          console.error("Generation failed:", error);
          const message = error instanceof Error ? error.message : "Неизвестная ошибка";
          set({ generationStatus: "error", generationError: message });
          return null;
        }
      },

      setActiveGeneration: (generationId) => {
        set({ activeGenerationId: generationId });
      },

      updateGeneration: (generationId, updates) => {
        set((state) => ({
          generations: state.generations.map((g) =>
            g.id === generationId ? { ...g, ...updates } : g
          ),
        }));
      },

      // --------------------------------------------------------
      // Models
      // --------------------------------------------------------

      fetchModels: async () => {
        set({ modelsLoading: true });
        try {
          const { models } = await modelsApi.getModels();
          set({ models, modelsLoading: false });
        } catch (error) {
          console.error("Failed to fetch models:", error);
          set({ modelsLoading: false });
        }
      },

      setActiveModel: (modelId) => {
        set({ activeModelId: modelId });
      },

      calculatePrice: async () => {
        const state = get();
        try {
          const { price } = await modelsApi.calculatePrice(
            state.activeModelId,
            state.config
          );
          return price;
        } catch {
          // Fallback to local calculation
          const model = state.models.find((m) => m.id === state.activeModelId);
          return model?.base_price || 0;
        }
      },

      // --------------------------------------------------------
      // UI
      // --------------------------------------------------------

      setViewMode: (mode) => set({ viewMode: mode }),
      
      toggleSidebar: () => set((s) => ({ sidebarOpen: !s.sidebarOpen })),
      
      setPrompt: (prompt) => set({ prompt }),
      
      setConfig: (key, value) =>
        set((state) => ({
          config: { ...state.config, [key]: value },
        })),
      
      resetConfig: () =>
        set({
          config: { resolution: "720p", aspect_ratio: "16:9" },
        }),

      // --------------------------------------------------------
      // Reset
      // --------------------------------------------------------

      reset: () => set(initialState),
    })),
    { name: "studio-store" }
  )
);

// ============================================================
// Selectors
// ============================================================

export const selectActiveSession = (state: StudioStore) =>
  state.sessions.find((s) => s.id === state.activeSessionId) || null;

export const selectActiveGeneration = (state: StudioStore) =>
  state.generations.find((g) => g.id === state.activeGenerationId) || null;

export const selectActiveModel = (state: StudioStore) =>
  state.models.find((m) => m.id === state.activeModelId) || null;

export const selectProcessingGenerations = (state: StudioStore) =>
  state.generations.filter((g) => g.status === "processing" || g.status === "queued");

export const selectCompletedGenerations = (state: StudioStore) =>
  state.generations.filter((g) => g.status === "completed");

// ============================================================
// Hooks for common patterns
// ============================================================

export const useActiveSession = () => useStudioStore(selectActiveSession);
export const useActiveGeneration = () => useStudioStore(selectActiveGeneration);
export const useActiveModel = () => useStudioStore(selectActiveModel);
