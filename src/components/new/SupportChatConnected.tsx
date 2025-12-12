/**
 * SupportChatConnected
 * 
 * AI-powered support chat using Gemini consultant.
 * The AI can answer questions, help with purchases, and create support tickets.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Send, ChevronDown, Activity, RefreshCw, Trash2, Sparkles } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAIChatTyped } from '../../hooks/useApiTyped';

interface SupportChatConnectedProps {
  isOpen: boolean;
  onToggle: (isOpen: boolean) => void;
  onHaptic?: () => void;
  raiseOnMobile?: boolean;
}

interface DisplayMessage {
  id: string;
  text: string;
  sender: 'user' | 'agent' | 'system';
  timestamp: string;
  action?: string;
  ticketId?: string;
}

const INITIAL_MESSAGES: DisplayMessage[] = [
  { id: 'sys-1', text: "Connecting to AI support channel...", sender: 'system', timestamp: 'SYSTEM' },
  { id: 'sys-2', text: "AI Agent online. Ask me anything about products, orders, or get support.", sender: 'system', timestamp: 'SYSTEM' },
];

const SupportChatConnected: React.FC<SupportChatConnectedProps> = ({ 
  isOpen, 
  onToggle, 
  onHaptic, 
  raiseOnMobile = false 
}) => {
  const { sendMessage, getHistory, clearHistory, loading } = useAIChatTyped();
  const [messages, setMessages] = useState<DisplayMessage[]>(INITIAL_MESSAGES);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const hasLoadedHistory = useRef(false);

  // Load chat history on first open
  useEffect(() => {
    if (isOpen && !hasLoadedHistory.current) {
      hasLoadedHistory.current = true;
      loadHistory();
    }
  }, [isOpen]);

  const loadHistory = useCallback(async () => {
    const history = await getHistory(20);
    if (history.length > 0) {
      // Convert history to display messages
      const historyMessages: DisplayMessage[] = history.map((msg, idx) => ({
        id: `history-${idx}`,
        text: msg.content,
        sender: msg.role === 'user' ? 'user' : 'agent',
        timestamp: msg.timestamp || (msg.role === 'user' ? 'YOU' : 'AI'),
      }));
      
      setMessages([...INITIAL_MESSAGES, ...historyMessages]);
    }
  }, [getHistory]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (isOpen && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping, isOpen]);

  const handleSend = async () => {
    if (!inputValue.trim() || loading || isTyping) return;
    if (onHaptic) onHaptic();

    const userMsg: DisplayMessage = {
      id: `user-${Date.now()}`,
      text: inputValue,
      sender: 'user',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    const messageText = inputValue;
    setInputValue('');
    setIsTyping(true);

    try {
      const response = await sendMessage(messageText);
      
      if (response) {
        const agentMsg: DisplayMessage = {
          id: `agent-${Date.now()}`,
          text: response.reply_text,
          sender: 'agent',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          action: response.action,
          ticketId: response.ticket_id,
        };
        setMessages(prev => [...prev, agentMsg]);
        
        // If ticket was created, show system message
        if (response.ticket_id) {
          const ticketMsg: DisplayMessage = {
            id: `ticket-${Date.now()}`,
            text: `Support ticket created: #${response.ticket_id.substring(0, 8)}`,
            sender: 'system',
            timestamp: 'TICKET',
          };
          setMessages(prev => [...prev, ticketMsg]);
        }
        
        // If action requires payment, show system message
        if (response.action === 'offer_payment' && response.total_amount) {
          const paymentMsg: DisplayMessage = {
            id: `payment-${Date.now()}`,
            text: `Ready for checkout: ${response.total_amount}₽`,
            sender: 'system',
            timestamp: 'CHECKOUT',
          };
          setMessages(prev => [...prev, paymentMsg]);
        }
      } else {
        // Error response
        const errorMsg: DisplayMessage = {
          id: `error-${Date.now()}`,
          text: 'Connection error. Please try again.',
          sender: 'system',
          timestamp: 'ERROR'
        };
        setMessages(prev => [...prev, errorMsg]);
      }
    } catch (err) {
      const errorMsg: DisplayMessage = {
        id: `error-${Date.now()}`,
        text: 'Failed to reach AI. Check your connection.',
        sender: 'system',
        timestamp: 'ERROR'
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const toggleChat = () => {
    if (onHaptic) onHaptic();
    onToggle(!isOpen);
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

      <div className={`fixed right-4 md:bottom-12 md:right-12 z-[100] flex flex-col items-end pointer-events-none transition-all duration-500 ease-in-out ${raiseOnMobile ? 'bottom-48' : 'bottom-24'}`}>
        
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
                  <div className="w-8 h-8 bg-pandora-cyan/20 flex items-center justify-center">
                    <Sparkles size={16} className="text-pandora-cyan" />
                  </div>
                  <div>
                    <h3 className="font-display font-bold text-sm text-white tracking-wide">AI_ASSISTANT</h3>
                    <p className="text-[10px] font-mono text-pandora-cyan flex items-center gap-1">
                      <Activity size={10} className="animate-pulse" /> GEMINI_ONLINE
                    </p>
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
                    <RefreshCw size={14} className={`text-gray-400 hover:text-pandora-cyan ${loading ? 'animate-spin' : ''}`} />
                  </button>
                  <button onClick={toggleChat} className="p-1 hover:bg-white/10 rounded transition-colors">
                    <ChevronDown size={18} className="text-gray-400 hover:text-white" />
                  </button>
                </div>
              </div>
              
              {/* Messages */}
              <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-3 scrollbar-thin scrollbar-thumb-white/10">
                {messages.map((msg) => (
                  <motion.div 
                    key={msg.id}
                    initial={{ opacity: 0, x: msg.sender === 'user' ? 10 : -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
                  >
                    <div className={`max-w-[85%] p-2.5 text-xs font-mono ${
                      msg.sender === 'user' 
                        ? 'bg-pandora-cyan/20 border border-pandora-cyan/30 text-pandora-cyan' 
                        : msg.sender === 'system'
                          ? 'bg-white/5 border border-white/10 text-gray-500 italic'
                          : 'bg-white/5 border border-white/10 text-gray-300'
                    }`}>
                      {/* Render HTML safely for agent messages */}
                      {msg.sender === 'agent' ? (
                        <p 
                          className="leading-relaxed whitespace-pre-wrap"
                          dangerouslySetInnerHTML={{ __html: msg.text }}
                        />
                      ) : (
                        <p className="leading-relaxed whitespace-pre-wrap">{msg.text}</p>
                      )}
                      <span className={`block text-[9px] mt-1 ${
                        msg.sender === 'user' ? 'text-pandora-cyan/50 text-right' : 'text-gray-600'
                      }`}>
                        {msg.timestamp}
                        {msg.action && msg.action !== 'none' && (
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

        {/* Toggle Button */}
        <button 
          onClick={toggleChat}
          className="pointer-events-auto relative w-16 h-16 group"
        >
          {/* Outer HUD Ring */}
          <div className="absolute inset-0 rounded-full border-2 border-dashed border-pandora-cyan/30 hud-spin" />
          <div className="absolute inset-1 rounded-full border border-pandora-cyan/20 hud-spin-rev" />
          
          {/* Core Button */}
          <div className={`
            absolute inset-2 clip-hexagon flex items-center justify-center transition-all duration-300
            ${isOpen 
              ? 'bg-pandora-cyan text-black shadow-[0_0_20px_#00FFFF]' 
              : 'bg-[#0a0a0a] border border-pandora-cyan/50 text-pandora-cyan group-hover:bg-pandora-cyan/20 group-hover:shadow-[0_0_15px_rgba(0,255,255,0.3)]'
            }
          `}>
            <Sparkles size={20} className={isOpen ? '' : 'group-hover:scale-110 transition-transform'} />
          </div>
          
          {/* HUD Label */}
          <span className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-[8px] font-mono text-pandora-cyan whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">
            AI_ASSISTANT
          </span>
        </button>
      </div>
    </>
  );
};

export default SupportChatConnected;
