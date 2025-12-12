/**
 * SupportChatConnected
 * 
 * Connected version of SupportChat that uses real ticket API.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Send, Terminal, MessageSquare, ChevronDown, Activity, RefreshCw } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useSupportTyped } from '../../hooks/useApiTyped';

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
  ticketId?: string;
}

const SupportChatConnected: React.FC<SupportChatConnectedProps> = ({ 
  isOpen, 
  onToggle, 
  onHaptic, 
  raiseOnMobile = false 
}) => {
  const { tickets, getTickets, createTicket, loading } = useSupportTyped();
  const [messages, setMessages] = useState<DisplayMessage[]>([
    { id: 'sys-1', text: "Connecting to secure support channel...", sender: 'system', timestamp: 'SYSTEM' },
    { id: 'sys-2', text: "Connection established. Type your message below.", sender: 'system', timestamp: 'SYSTEM' },
  ]);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const hasLoadedTickets = useRef(false);

  // Load existing tickets on first open
  useEffect(() => {
    if (isOpen && !hasLoadedTickets.current) {
      hasLoadedTickets.current = true;
      loadTickets();
    }
  }, [isOpen]);

  const loadTickets = useCallback(async () => {
    const fetchedTickets = await getTickets();
    if (fetchedTickets.length > 0) {
      // Convert tickets to messages
      const ticketMessages: DisplayMessage[] = fetchedTickets.flatMap(ticket => {
        const msgs: DisplayMessage[] = [];
        // User message
        msgs.push({
          id: `ticket-${ticket.id}-user`,
          text: ticket.message,
          sender: 'user',
          timestamp: new Date(ticket.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
          ticketId: ticket.id,
        });
        // Admin reply if exists
        if (ticket.admin_reply) {
          msgs.push({
            id: `ticket-${ticket.id}-admin`,
            text: ticket.admin_reply,
            sender: 'agent',
            timestamp: 'SUPPORT',
            ticketId: ticket.id,
          });
        } else if (ticket.status === 'open') {
          msgs.push({
            id: `ticket-${ticket.id}-pending`,
            text: `Ticket #${ticket.id.substring(0, 8)} is being processed...`,
            sender: 'system',
            timestamp: 'PENDING',
            ticketId: ticket.id,
          });
        }
        return msgs;
      });
      
      setMessages(prev => [
        ...prev.filter(m => m.sender === 'system' && !m.ticketId),
        ...ticketMessages,
      ]);
    }
  }, [getTickets]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (isOpen && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping, isOpen]);

  const handleSend = async () => {
    if (!inputValue.trim() || loading) return;
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
      const result = await createTicket(messageText, 'general');
      
      const agentMsg: DisplayMessage = {
        id: `agent-${Date.now()}`,
        text: result.success 
          ? `Ticket created successfully. ID: #${result.ticket_id?.substring(0, 8)}. Our team will respond soon.`
          : 'Failed to create ticket. Please try again.',
        sender: 'agent',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        ticketId: result.ticket_id,
      };
      setMessages(prev => [...prev, agentMsg]);
    } catch (err) {
      const errorMsg: DisplayMessage = {
        id: `error-${Date.now()}`,
        text: 'Connection error. Please check your network and try again.',
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
    loadTickets();
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
                    <Terminal size={16} className="text-pandora-cyan" />
                  </div>
                  <div>
                    <h3 className="font-display font-bold text-sm text-white tracking-wide">SUPPORT_CHANNEL</h3>
                    <p className="text-[10px] font-mono text-pandora-cyan flex items-center gap-1">
                      <Activity size={10} className="animate-pulse" /> SECURE_LINE
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button 
                    onClick={handleRefresh}
                    className="p-1 hover:bg-white/10 rounded transition-colors"
                    title="Refresh tickets"
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
                      <p className="leading-relaxed whitespace-pre-wrap">{msg.text}</p>
                      <span className={`block text-[9px] mt-1 ${
                        msg.sender === 'user' ? 'text-pandora-cyan/50 text-right' : 'text-gray-600'
                      }`}>
                        {msg.timestamp}
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
                      <span className="animate-pulse">Processing request...</span>
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
                    placeholder="Describe your issue..."
                    disabled={loading}
                    className="flex-1 bg-white/5 border border-white/10 text-white text-xs font-mono p-2.5 focus:outline-none focus:border-pandora-cyan/50 placeholder:text-gray-600 disabled:opacity-50"
                  />
                  <button 
                    onClick={handleSend}
                    disabled={!inputValue.trim() || loading}
                    className="p-2.5 bg-pandora-cyan/20 border border-pandora-cyan/50 text-pandora-cyan hover:bg-pandora-cyan hover:text-black transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Send size={16} />
                  </button>
                </div>
                <p className="text-[9px] text-gray-600 mt-2 font-mono">
                  Messages create support tickets. Response within 24h.
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
            <MessageSquare size={20} className={isOpen ? '' : 'group-hover:scale-110 transition-transform'} />
          </div>
          
          {/* Notification Dot */}
          {tickets.some(t => t.status === 'open' && t.admin_reply) && !isOpen && (
            <span className="absolute top-0 right-0 w-3 h-3 bg-red-500 rounded-full animate-pulse border-2 border-[#050505]" />
          )}
          
          {/* HUD Label */}
          <span className="absolute -bottom-5 left-1/2 -translate-x-1/2 text-[8px] font-mono text-pandora-cyan whitespace-nowrap opacity-0 group-hover:opacity-100 transition-opacity">
            SYSTEM_ONLINE
          </span>
        </button>
      </div>
    </>
  );
};

export default SupportChatConnected;

