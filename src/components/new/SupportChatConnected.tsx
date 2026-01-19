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
  if (sender === "user") {
    return "bg-pandora-cyan/20 border border-pandora-cyan/30 text-pandora-cyan";
  }
  if (sender === "system") {
    return "bg-white/5 border border-white/10 text-gray-500 italic";
  }
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
    if (isOpen && initialContext?.orderId && !contextAppliedRef.current) {
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

  // Load chat history function - must be defined BEFORE useEffect that uses it
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
  }, [isOpen, initialContext, loadHistory]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (isOpen && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [isOpen]);

  const handleSend = async () => {
    if (!inputValue.trim() || loading || isTyping) {
      return;
    }
    if (onHaptic) {
      onHaptic();
    }

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
    if (onHaptic) {
      onHaptic();
    }
    const willClose = isOpen;
    onToggle(!isOpen);

    // Reset context refs when closing chat
    if (willClose) {
      contextAppliedRef.current = false;
      processedContextRef.current = null;
    }
  };

  const handleRefresh = () => {
    if (onHaptic) {
      onHaptic();
    }
    loadHistory();
  };

  const handleClear = async () => {
    if (onHaptic) {
      onHaptic();
    }
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
        className={`pointer-events-none fixed right-4 z-[100] flex flex-col items-end transition-all duration-500 ease-in-out md:right-12 md:bottom-12 ${raiseOnMobile ? "bottom-48" : "bottom-24"}`}
      >
        {/* Chat Window */}
        <AnimatePresence>
          {isOpen && (
            <motion.div
              animate={{ opacity: 1, y: 0, scale: 1 }}
              className="pointer-events-auto relative mb-4 flex h-[450px] w-[360px] max-w-[calc(100vw-2rem)] flex-col overflow-hidden border border-pandora-cyan/30 bg-[#050505] shadow-[0_0_40px_rgba(0,255,255,0.15)]"
              exit={{ opacity: 0, y: 20, scale: 0.9 }}
              initial={{ opacity: 0, y: 20, scale: 0.9 }}
              transition={{ type: "spring", stiffness: 300, damping: 25 }}
            >
              {/* Header */}
              <div className="flex shrink-0 items-center justify-between border-pandora-cyan/20 border-b bg-gradient-to-r from-pandora-cyan/10 to-transparent p-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-8 w-8 items-center justify-center rounded-sm border border-pandora-cyan/30 bg-black/50">
                    <Terminal className="text-pandora-cyan" size={14} />
                  </div>
                  <div>
                    <div className="font-bold font-mono text-[10px] text-white tracking-widest">
                      UPLINK_SECURE
                    </div>
                    <div className="flex items-center gap-1 font-mono text-[9px] text-pandora-cyan">
                      <span className="h-1 w-1 animate-pulse rounded-full bg-green-500" />
                      <span>CHANNEL_OPEN</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    className="rounded p-1 transition-colors hover:bg-white/10"
                    onClick={handleClear}
                    title="Clear history"
                    type="button"
                  >
                    <Trash2 className="text-gray-400 hover:text-red-400" size={14} />
                  </button>
                  <button
                    className="rounded p-1 transition-colors hover:bg-white/10"
                    onClick={handleRefresh}
                    title="Refresh history"
                    type="button"
                  >
                    <RefreshCw
                      className={`text-gray-400 hover:text-pandora-cyan ${loading ? "animate-spin" : ""}`}
                      size={14}
                    />
                  </button>
                  <button
                    className="rounded p-1 transition-colors hover:bg-white/10"
                    onClick={toggleChat}
                    type="button"
                  >
                    <ChevronDown className="text-gray-400 hover:text-white" size={18} />
                  </button>
                </div>
              </div>

              {/* Messages */}
              <div
                className="scrollbar-thin scrollbar-thumb-white/10 flex-1 space-y-3 overflow-y-auto p-4"
                ref={scrollRef}
              >
                {messages.map((msg) => (
                  <motion.div
                    animate={{ opacity: 1, x: 0 }}
                    className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
                    initial={{ opacity: 0, x: msg.sender === "user" ? 10 : -10 }}
                    key={msg.id}
                  >
                    <div
                      className={`max-w-[85%] p-2.5 font-mono text-xs ${getMessageClasses(msg.sender)}`}
                    >
                      {/* Render HTML safely for agent messages */}
                      {msg.sender === "agent" ? (
                        <p
                          className="whitespace-pre-wrap leading-relaxed"
                          // biome-ignore lint/security/noDangerouslySetInnerHtml: Intentional - AI agent returns sanitized HTML
                          dangerouslySetInnerHTML={{ __html: msg.text }}
                        />
                      ) : (
                        <p className="whitespace-pre-wrap leading-relaxed">{msg.text}</p>
                      )}
                      <span
                        className={`mt-1 block text-[9px] ${
                          msg.sender === "user"
                            ? "text-right text-pandora-cyan/50"
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
                    animate={{ opacity: 1 }}
                    className="flex justify-start"
                    initial={{ opacity: 0 }}
                  >
                    <div className="border border-white/10 bg-white/5 p-2.5 font-mono text-gray-500 text-xs">
                      <span className="flex items-center gap-2">
                        <Sparkles className="animate-pulse text-pandora-cyan" size={12} />
                        AI is thinking...
                      </span>
                    </div>
                  </motion.div>
                )}
              </div>

              {/* Input */}
              <div className="shrink-0 border-white/10 border-t bg-black/50 p-3">
                <div className="flex items-center gap-2">
                  <input
                    className="flex-1 border border-white/10 bg-white/5 p-2.5 font-mono text-white text-xs placeholder:text-gray-600 focus:border-pandora-cyan/50 focus:outline-none disabled:opacity-50"
                    disabled={loading || isTyping}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask anything..."
                    type="text"
                    value={inputValue}
                  />
                  <button
                    className="border border-pandora-cyan/50 bg-pandora-cyan/20 p-2.5 text-pandora-cyan transition-all hover:bg-pandora-cyan hover:text-black disabled:cursor-not-allowed disabled:opacity-50"
                    disabled={!inputValue.trim() || loading || isTyping}
                    onClick={handleSend}
                    type="button"
                  >
                    <Send size={16} />
                  </button>
                </div>
                <p className="mt-2 font-mono text-[9px] text-gray-600">
                  AI powered by Gemini. Can help with products, orders & support.
                </p>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Toggle Button (HUD widget style) */}
        <button
          className="group pointer-events-auto relative flex h-16 w-16 items-center justify-center md:h-20 md:w-20"
          onClick={toggleChat}
          type="button"
        >
          {/* Status label (desktop) */}
          <motion.div
            animate={{ x: 0, opacity: 1 }}
            className="pointer-events-none absolute top-1/2 right-full mr-6 hidden -translate-y-1/2 items-center gap-3 md:flex"
            initial={{ x: 20, opacity: 0 }}
            transition={{ delay: 0.2 }}
          >
            <div className="rounded-sm border border-white/10 bg-black/80 px-3 py-1.5 shadow-xl backdrop-blur-md">
              <div className="flex items-center gap-2 whitespace-nowrap font-bold font-mono text-[10px] text-pandora-cyan tracking-widest">
                <Activity className="animate-pulse" size={10} />
                {t("support.systemOnline")}
              </div>
            </div>
            <div className="h-px w-6 bg-gradient-to-r from-white/20 to-pandora-cyan/50" />
          </motion.div>

          {/* Rings */}
          <div className="hud-spin absolute inset-0 rounded-full border border-white/20 border-dashed" />
          <div className="hud-spin-rev absolute inset-1 rounded-full border border-pandora-cyan/30 border-t-transparent border-l-transparent" />
          <div className="absolute inset-2 animate-pulse rounded-full bg-pandora-cyan/5 blur-md" />

          {/* Hexagon core with chat icon */}
          <div className="clip-hexagon relative z-10 flex h-10 w-10 items-center justify-center bg-[#0a0a0a] shadow-[0_0_20px_rgba(0,0,0,0.5)] transition-colors duration-300 group-hover:bg-pandora-cyan md:h-12 md:w-12">
            <MessageSquare
              className="relative z-20 text-pandora-cyan transition-colors duration-300 group-hover:text-black"
              size={20}
            />
          </div>

          {/* Notification Dot (always on to match original) */}
          <div className="absolute top-2 right-2 z-20 h-3 w-3 animate-bounce rounded-full border-2 border-black bg-red-500 shadow-[0_0_10px_red]">
            <span className="absolute inset-0 animate-ping rounded-full bg-red-500 opacity-75" />
          </div>
        </button>
      </div>
    </>
  );
};

export default SupportChatConnected;
