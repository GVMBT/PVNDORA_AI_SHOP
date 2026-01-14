/**
 * SupportChatConnected
 *
 * AI-powered support chat using Gemini consultant.
 * The AI can answer questions, help with purchases, and create support tickets.
 */

import { AnimatePresence, motion } from "framer-motion";
import {
  Activity,
  ChevronDown,
  MessageSquare,
  RefreshCw,
  Send,
  Sparkles,
  Terminal,
  Trash2,
} from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useRef, useState } from "react";
import { useAIChatTyped } from "../../hooks/useApiTyped";
import { useLocale } from "../../hooks/useLocale";

// Helper for message styling (avoid nested ternary)
const getMessageClasses = (sender: string): string => {
  if (sender === "user")
    return "bg-pandora-cyan/20 border border-pandora-cyan/30 text-pandora-cyan";
  if (sender === "system") return "bg-white/5 border border-white/10 text-gray-500 italic";
  return "bg-white/5 border border-white/10 text-gray-300";
};

type SupportChatInitialContext = {
  orderId?: string;
  itemId?: string; // Specific order item ID for replacements
  orderTotal?: number;
  productNames?: string[];
  reason?: string;
} | null;

interface SupportChatConnectedProps {
  isOpen: boolean;
  onToggle: (isOpen: boolean) => void;
  onHaptic?: () => void;
  raiseOnMobile?: boolean;
  initialContext?: SupportChatInitialContext;
}

interface DisplayMessage {
  id: string;
  text: string;
  sender: "user" | "agent" | "system";
  timestamp: string;
  action?: string;
  ticketId?: string;
}

const INITIAL_MESSAGES: DisplayMessage[] = [
  {
    id: "sys-1",
    text: "Connecting to AI support channel...",
    sender: "system",
    timestamp: "SYSTEM",
  },
  {
    id: "sys-2",
    text: "AI Agent online. Ask me anything about products, orders, or get support.",
    sender: "system",
    timestamp: "SYSTEM",
  },
];

const SupportChatConnected: React.FC<SupportChatConnectedProps> = ({
  isOpen,
  onToggle,
  onHaptic,
  raiseOnMobile = false,
  initialContext = null,
}) => {
  const { sendMessage, getHistory, clearHistory, loading } = useAIChatTyped();
  const { t } = useLocale();
  const [messages, setMessages] = useState<DisplayMessage[]>(INITIAL_MESSAGES);
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const hasLoadedHistory = useRef(false);
  const processedContextRef = useRef<string | null>(null);
  const contextAppliedRef = useRef(false);

  // Handle initial context (e.g., refund request from orders page)
  // This should run AFTER history is loaded to avoid overwriting
  useEffect(() => {
    if (isOpen && initialContext && initialContext.orderId && !contextAppliedRef.current) {
      // Only process each unique context once
      const contextKey = `${initialContext.orderId}-${initialContext.reason}`;
      if (processedContextRef.current !== contextKey) {
        processedContextRef.current = contextKey;
        contextAppliedRef.current = true;

        // Set pre-filled message for issue report (not refund by default!)
        const products = initialContext.productNames?.join(", ") || "N/A";
        const itemInfo = initialContext.itemId ? `\n• Item ID: ${initialContext.itemId}` : "";
        const reason = initialContext.reason || "Проблема с аккаунтом";
        const prefillMessage = `Проблема с аккаунтом:\n\n• Order ID: ${initialContext.orderId}${itemInfo}\n• Товар: ${products}\n• Описание: ${reason}\n\nПрошу помочь с заменой аккаунта.`;

        // Apply after a small delay to ensure input is ready
        setTimeout(() => {
          setInputValue(prefillMessage);
        }, 100);
      }
    } else if (!initialContext) {
      // Reset when context is cleared
      contextAppliedRef.current = false;
      processedContextRef.current = null;
    }
  }, [isOpen, initialContext]);

  // Load chat history on first open
  useEffect(() => {
    if (isOpen && !hasLoadedHistory.current) {
      hasLoadedHistory.current = true;
      loadHistory().then(() => {
        // After history loads, apply context if needed (check current initialContext)
        const currentContext = initialContext;
        if (currentContext?.orderId && !contextAppliedRef.current) {
          const products = currentContext.productNames?.join(", ") || "N/A";
          const itemInfo = currentContext.itemId ? `\n• Item ID: ${currentContext.itemId}` : "";
          const reason = currentContext.reason || "Проблема с аккаунтом";
          const prefillMessage = `Проблема с аккаунтом:\n\n• Order ID: ${currentContext.orderId}${itemInfo}\n• Товар: ${products}\n• Описание: ${reason}\n\nПрошу помочь с заменой аккаунта.`;
          setInputValue(prefillMessage);
          contextAppliedRef.current = true;
          processedContextRef.current = `${currentContext.orderId}-${currentContext.reason}`;
        }
      });
    }
  }, [isOpen, initialContext, loadHistory]); // Don't include initialContext to avoid re-loading history

  const loadHistory = useCallback(async () => {
    const history = await getHistory(20);
    if (history.length > 0) {
      // Convert history to display messages
      const historyMessages: DisplayMessage[] = history.map((msg, idx) => ({
        id: `history-${idx}`,
        text: msg.content,
        sender: msg.role === "user" ? "user" : "agent",
        timestamp: msg.timestamp || (msg.role === "user" ? "YOU" : "AI"),
      }));

      setMessages([...INITIAL_MESSAGES, ...historyMessages]);
    }
  }, [getHistory]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (isOpen && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [isOpen]);

  const handleSend = async () => {
    if (!inputValue.trim() || loading || isTyping) return;
    if (onHaptic) onHaptic();

    const userMsg: DisplayMessage = {
      id: `user-${Date.now()}`,
      text: inputValue,
      sender: "user",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    const messageText = inputValue;
    setInputValue("");

    // Clear context after sending (so it doesn't re-apply on next open)
    contextAppliedRef.current = false;
    processedContextRef.current = null;

    setIsTyping(true);

    try {
      const response = await sendMessage(messageText);

      if (response) {
        const agentMsg: DisplayMessage = {
          id: `agent-${Date.now()}`,
          text: response.reply_text,
          sender: "agent",
          timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          action: response.action,
          ticketId: response.ticket_id,
        };
        setMessages((prev) => [...prev, agentMsg]);

        // If ticket was created, show system message
        if (response.ticket_id) {
          const ticketMsg: DisplayMessage = {
            id: `ticket-${Date.now()}`,
            text: `Support ticket created: #${response.ticket_id.substring(0, 8)}`,
            sender: "system",
            timestamp: "TICKET",
          };
          setMessages((prev) => [...prev, ticketMsg]);
        }

        // If action requires payment, show system message
        if (response.action === "offer_payment" && response.total_amount) {
          const paymentMsg: DisplayMessage = {
            id: `payment-${Date.now()}`,
            text: `Ready for checkout: ${response.total_amount}₽`,
            sender: "system",
            timestamp: "CHECKOUT",
          };
          setMessages((prev) => [...prev, paymentMsg]);
        }
      } else {
        // Error response
        const errorMsg: DisplayMessage = {
          id: `error-${Date.now()}`,
          text: "Connection error. Please try again.",
          sender: "system",
          timestamp: "ERROR",
        };
        setMessages((prev) => [...prev, errorMsg]);
      }
    } catch {
      const errorMsg: DisplayMessage = {
        id: `error-${Date.now()}`,
        text: "Failed to reach AI. Check your connection.",
        sender: "system",
        timestamp: "ERROR",
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const toggleChat = () => {
    if (onHaptic) onHaptic();
    const willClose = isOpen;
    onToggle(!isOpen);

    // Reset context refs when closing chat
    if (willClose) {
      contextAppliedRef.current = false;
      processedContextRef.current = null;
    }
  };

  const handleRefresh = () => {
    if (onHaptic) onHaptic();
    loadHistory();
  };

  const handleClear = async () => {
    if (onHaptic) onHaptic();
    const success = await clearHistory();
    if (success) {
      setMessages(INITIAL_MESSAGES);
    }
  };

  return (
    <>
      <style>{`
        @keyframes spin-slow {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
        @keyframes spin-reverse {
          from { transform: rotate(360deg); }
          to { transform: rotate(0deg); }
        }
        .hud-spin { animation: spin-slow 10s linear infinite; }
        .hud-spin-fast { animation: spin-slow 3s linear infinite; }
        .hud-spin-rev { animation: spin-reverse 8s linear infinite; }
        
        .clip-hexagon {
          clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
          -webkit-clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
        }
      `}</style>

      <div
        className={`fixed right-4 md:bottom-12 md:right-12 z-[100] flex flex-col items-end pointer-events-none transition-all duration-500 ease-in-out ${raiseOnMobile ? "bottom-48" : "bottom-24"}`}
      >
        {/* Chat Window */}
        <AnimatePresence>
          {isOpen && (
            <motion.div
              initial={{ opacity: 0, y: 20, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 20, scale: 0.9 }}
              transition={{ type: "spring", stiffness: 300, damping: 25 }}
              className="pointer-events-auto w-[360px] max-w-[calc(100vw-2rem)] h-[450px] bg-[#050505] border border-pandora-cyan/30 flex flex-col shadow-[0_0_40px_rgba(0,255,255,0.15)] mb-4 relative overflow-hidden"
            >
              {/* Header */}
              <div className="p-3 border-b border-pandora-cyan/20 bg-gradient-to-r from-pandora-cyan/10 to-transparent flex items-center justify-between shrink-0">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-black/50 border border-pandora-cyan/30 flex items-center justify-center rounded-sm">
                    <Terminal size={14} className="text-pandora-cyan" />
                  </div>
                  <div>
                    <div className="font-mono font-bold text-[10px] tracking-widest text-white">
                      UPLINK_SECURE
                    </div>
                    <div className="font-mono text-[9px] text-pandora-cyan flex items-center gap-1">
                      <span className="w-1 h-1 bg-green-500 rounded-full animate-pulse" />
                      <span>CHANNEL_OPEN</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleClear}
                    className="p-1 hover:bg-white/10 rounded transition-colors"
                    title="Clear history"
                  >
                    <Trash2 size={14} className="text-gray-400 hover:text-red-400" />
                  </button>
                  <button
                    onClick={handleRefresh}
                    className="p-1 hover:bg-white/10 rounded transition-colors"
                    title="Refresh history"
                  >
                    <RefreshCw
                      size={14}
                      className={`text-gray-400 hover:text-pandora-cyan ${loading ? "animate-spin" : ""}`}
                    />
                  </button>
                  <button
                    onClick={toggleChat}
                    className="p-1 hover:bg-white/10 rounded transition-colors"
                  >
                    <ChevronDown size={18} className="text-gray-400 hover:text-white" />
                  </button>
                </div>
              </div>

              {/* Messages */}
              <div
                ref={scrollRef}
                className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-thin scrollbar-thumb-white/10"
              >
                {messages.map((msg) => (
                  <motion.div
                    key={msg.id}
                    initial={{ opacity: 0, x: msg.sender === "user" ? 10 : -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
                  >
                    <div
                      className={`max-w-[85%] p-2.5 text-xs font-mono ${getMessageClasses(msg.sender)}`}
                    >
                      {/* Render HTML safely for agent messages */}
                      {msg.sender === "agent" ? (
                        <p
                          className="leading-relaxed whitespace-pre-wrap"
                          dangerouslySetInnerHTML={{ __html: msg.text }}
                        />
                      ) : (
                        <p className="leading-relaxed whitespace-pre-wrap">{msg.text}</p>
                      )}
                      <span
                        className={`block text-[9px] mt-1 ${
                          msg.sender === "user"
                            ? "text-pandora-cyan/50 text-right"
                            : "text-gray-600"
                        }`}
                      >
                        {msg.timestamp}
                        {msg.action && msg.action !== "none" && (
                          <span className="ml-2 text-yellow-500">[{msg.action}]</span>
                        )}
                      </span>
                    </div>
                  </motion.div>
                ))}

                {isTyping && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex justify-start"
                  >
                    <div className="bg-white/5 border border-white/10 p-2.5 text-xs font-mono text-gray-500">
                      <span className="flex items-center gap-2">
                        <Sparkles size={12} className="animate-pulse text-pandora-cyan" />
                        AI is thinking...
                      </span>
                    </div>
                  </motion.div>
                )}
              </div>

              {/* Input */}
              <div className="p-3 border-t border-white/10 bg-black/50 shrink-0">
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask anything..."
                    disabled={loading || isTyping}
                    className="flex-1 bg-white/5 border border-white/10 text-white text-xs font-mono p-2.5 focus:outline-none focus:border-pandora-cyan/50 placeholder:text-gray-600 disabled:opacity-50"
                  />
                  <button
                    onClick={handleSend}
                    disabled={!inputValue.trim() || loading || isTyping}
                    className="p-2.5 bg-pandora-cyan/20 border border-pandora-cyan/50 text-pandora-cyan hover:bg-pandora-cyan hover:text-black transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Send size={16} />
                  </button>
                </div>
                <p className="text-[9px] text-gray-600 mt-2 font-mono">
                  AI powered by Gemini. Can help with products, orders & support.
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Toggle Button (HUD widget style) */}
        <button
          onClick={toggleChat}
          className="pointer-events-auto relative w-16 h-16 md:w-20 md:h-20 flex items-center justify-center group"
        >
          {/* Status label (desktop) */}
          <motion.div
            initial={{ x: 20, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="absolute right-full mr-6 top-1/2 -translate-y-1/2 hidden md:flex items-center gap-3 pointer-events-none"
          >
            <div className="bg-black/80 backdrop-blur-md border border-white/10 px-3 py-1.5 rounded-sm shadow-xl">
              <div className="text-[10px] font-bold text-pandora-cyan font-mono tracking-widest whitespace-nowrap flex items-center gap-2">
                <Activity size={10} className="animate-pulse" />
                {t("support.systemOnline")}
              </div>
            </div>
            <div className="w-6 h-px bg-gradient-to-r from-white/20 to-pandora-cyan/50" />
          </motion.div>

          {/* Rings */}
          <div className="absolute inset-0 rounded-full border border-dashed border-white/20 hud-spin" />
          <div className="absolute inset-1 rounded-full border border-t-transparent border-l-transparent border-pandora-cyan/30 hud-spin-rev" />
          <div className="absolute inset-2 bg-pandora-cyan/5 rounded-full blur-md animate-pulse" />

          {/* Hexagon core with chat icon */}
          <div className="relative z-10 w-10 h-10 md:w-12 md:h-12 bg-[#0a0a0a] flex items-center justify-center clip-hexagon group-hover:bg-pandora-cyan transition-colors duration-300 shadow-[0_0_20px_rgba(0,0,0,0.5)]">
            <MessageSquare
              size={20}
              className="text-pandora-cyan group-hover:text-black transition-colors duration-300 relative z-20"
            />
          </div>

          {/* Notification Dot (always on to match original) */}
          <div className="absolute top-2 right-2 w-3 h-3 bg-red-500 rounded-full border-2 border-black z-20 shadow-[0_0_10px_red] animate-bounce">
            <span className="absolute inset-0 rounded-full bg-red-500 animate-ping opacity-75" />
          </div>
        </button>
      </div>
    </>
  );
};

export default SupportChatConnected;
