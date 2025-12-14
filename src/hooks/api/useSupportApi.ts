/**
 * Support API Hooks
 * 
 * Hooks for reviews, support tickets, and AI chat.
 */

import { useState, useCallback } from 'react';
import { useApi } from '../useApi';
import { logger } from '../../utils/logger';

// Reviews Hook
export function useReviewsTyped() {
  const { post, loading, error } = useApi();

  const submitReview = useCallback(async (
    orderId: string,
    rating: number,
    text?: string
  ): Promise<{ success: boolean; review_id?: string }> => {
    try {
      return await post('/reviews', { order_id: orderId, rating, text });
    } catch (err) {
      logger.error('Failed to submit review', err);
      throw err;
    }
  }, [post]);

  return { submitReview, loading, error };
}

// Support Tickets
interface SupportTicket {
  id: string;
  status: 'open' | 'approved' | 'rejected' | 'closed';
  issue_type: string;
  message: string;
  admin_reply?: string;
  order_id?: string;
  created_at: string;
}

export function useSupportTyped() {
  const { get, post, loading, error } = useApi();
  const [tickets, setTickets] = useState<SupportTicket[]>([]);

  const getTickets = useCallback(async (): Promise<SupportTicket[]> => {
    try {
      const response = await get<{ tickets: SupportTicket[] }>('/support/tickets');
      const data = response.tickets || [];
      setTickets(data);
      return data;
    } catch (err) {
      logger.error('Failed to fetch tickets', err);
      return [];
    }
  }, [get]);

  const createTicket = useCallback(async (
    message: string,
    issueType: string = 'general',
    orderId?: string
  ): Promise<{ success: boolean; ticket_id?: string; message?: string }> => {
    try {
      return await post('/support/tickets', {
        message,
        issue_type: issueType,
        order_id: orderId,
      });
    } catch (err) {
      logger.error('Failed to create ticket', err);
      throw err;
    }
  }, [post]);

  const getTicket = useCallback(async (ticketId: string): Promise<SupportTicket | null> => {
    try {
      const response = await get<{ ticket: SupportTicket }>(`/support/tickets/${ticketId}`);
      return response.ticket || null;
    } catch (err) {
      logger.error(`Failed to fetch ticket ${ticketId}`, err);
      return null;
    }
  }, [get]);

  return { tickets, getTickets, createTicket, getTicket, loading, error };
}

// AI Chat
interface AIChatResponse {
  reply_text: string;
  action: string;
  thought?: string;
  ticket_id?: string;
  product_id?: string;
  total_amount?: number;
}

interface ChatHistoryItem {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

export function useAIChatTyped() {
  const { get, post, del, loading, error } = useApi();
  const [history, setHistory] = useState<ChatHistoryItem[]>([]);

  const sendMessage = useCallback(async (message: string): Promise<AIChatResponse | null> => {
    try {
      const response: AIChatResponse = await post('/ai/chat', { message });
      return response;
    } catch (err) {
      logger.error('Failed to send AI message', err);
      return null;
    }
  }, [post]);

  const getHistory = useCallback(async (limit: number = 20): Promise<ChatHistoryItem[]> => {
    try {
      const response = await get<{ messages: ChatHistoryItem[] }>(`/ai/history?limit=${limit}`);
      const messages = response.messages || [];
      setHistory(messages);
      return messages;
    } catch (err) {
      logger.error('Failed to get chat history', err);
      return [];
    }
  }, [get]);

  const clearHistory = useCallback(async (): Promise<boolean> => {
    try {
      await del('/ai/history');
      setHistory([]);
      return true;
    } catch (err) {
      logger.error('Failed to clear chat history', err);
      return false;
    }
  }, [del]);

  return { history, sendMessage, getHistory, clearHistory, loading, error };
}

// Promo Code Hook
interface PromoResult {
  is_valid: boolean;
  discount_percent?: number;
  discount_amount?: number;
  error?: string;
}

export function usePromoTyped() {
  const { post, loading, error } = useApi();

  const checkPromo = useCallback(async (code: string): Promise<PromoResult> => {
    try {
      return await post<PromoResult>('/promo/check', { code });
    } catch (err) {
      logger.error('Failed to check promo code', err);
      return { is_valid: false, error: err instanceof Error ? err.message : 'Unknown error' };
    }
  }, [post]);

  return { checkPromo, loading, error };
}
