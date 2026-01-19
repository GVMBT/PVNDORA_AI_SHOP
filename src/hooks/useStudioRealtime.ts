/**
 * Studio Realtime Hook
 * 
 * Subscribes to SSE events for generation status updates.
 */

import { useEffect, useRef } from "react";
import { useStudioStore } from "../stores/studioStore";
import { getAuthHeaders } from "../utils/apiHeaders";

interface GenerationEvent {
  type: "generation.status";
  generation_id: string;
  status: "queued" | "processing" | "completed" | "failed";
  progress: number;
  result_url?: string | null;
  error?: string | null;
  timestamp: string;
}

export function useStudioRealtime() {
  const eventSourceRef = useRef<EventSource | null>(null);
  const updateGeneration = useStudioStore((s) => s.updateGeneration);
  const fetchGenerations = useStudioStore((s) => s.fetchGenerations);
  const activeSessionId = useStudioStore((s) => s.activeSessionId);

  useEffect(() => {
    // Close existing connection
    if (eventSourceRef.current) {
      eventSourceRef.current.close();
    }

    // Build SSE URL with auth
    const headers = getAuthHeaders();
    const initData = headers["X-Telegram-Init-Data"] || "";
    
    if (!initData) {
      console.warn("No auth data for Studio SSE");
      return;
    }

    const sseUrl = `/api/webapp/realtime/stream?stream=studio&init_data=${encodeURIComponent(initData)}`;

    const eventSource = new EventSource(sseUrl);
    eventSourceRef.current = eventSource;

    eventSource.onopen = () => {
      console.log("[Studio SSE] Connected");
    };

    eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as GenerationEvent;
        
        if (data.type === "generation.status") {
          console.log("[Studio SSE] Generation update:", data);
          
          // Update store
          updateGeneration(data.generation_id, {
            status: data.status,
            progress: data.progress,
            result_url: data.result_url ?? undefined,
            error_message: data.error ?? undefined,
          });

          // If completed or failed, refresh to get full data
          if (data.status === "completed" || data.status === "failed") {
            fetchGenerations(activeSessionId || undefined);
          }
        }
      } catch (error) {
        console.error("[Studio SSE] Parse error:", error);
      }
    };

    eventSource.onerror = (error) => {
      console.error("[Studio SSE] Error:", error);
      // EventSource will automatically reconnect
    };

    return () => {
      eventSource.close();
      eventSourceRef.current = null;
    };
  }, [updateGeneration, fetchGenerations, activeSessionId]);
}

/**
 * Hook to initialize Studio data on mount
 */
export function useStudioInit() {
  const fetchSessions = useStudioStore((s) => s.fetchSessions);
  const fetchModels = useStudioStore((s) => s.fetchModels);
  const fetchGenerations = useStudioStore((s) => s.fetchGenerations);
  const activeSessionId = useStudioStore((s) => s.activeSessionId);

  useEffect(() => {
    // Fetch initial data
    Promise.all([
      fetchSessions(),
      fetchModels(),
    ]).then(() => {
      // Fetch generations after sessions are loaded
      const store = useStudioStore.getState();
      if (store.activeSessionId) {
        fetchGenerations(store.activeSessionId);
      }
    });
  }, [fetchSessions, fetchModels, fetchGenerations]);

  // Refetch generations when session changes
  useEffect(() => {
    if (activeSessionId) {
      fetchGenerations(activeSessionId);
    }
  }, [activeSessionId, fetchGenerations]);

  // Subscribe to realtime updates
  useStudioRealtime();
}
