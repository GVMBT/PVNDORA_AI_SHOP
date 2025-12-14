
import React, { useState, useEffect, useRef } from 'react';
import { Send, Terminal, Paperclip, MessageSquare, ChevronDown, Activity } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { randomInt } from '../../utils/random';

interface SupportChatProps {
  isOpen: boolean;
  onToggle: (isOpen: boolean) => void;
  onHaptic?: () => void;
  raiseOnMobile?: boolean;
}

interface Message {
  id: number;
  text: string;
  sender: 'user' | 'agent';
  timestamp: string;
}

const INITIAL_MESSAGES: Message[] = [
    { id: 1, text: "Connecting to secure support channel...", sender: 'agent', timestamp: 'SYSTEM' },
    { id: 2, text: "Connection established. Agent [NEO_7] assigned.", sender: 'agent', timestamp: 'SYSTEM' },
    { id: 3, text: "Greetings. Describe your issue or request access to high-tier nodes.", sender: 'agent', timestamp: '10:00' },
];

const SupportChat: React.FC<SupportChatProps> = ({ isOpen, onToggle, onHaptic, raiseOnMobile = false }) => {
  const [messages, setMessages] = useState<Message[]>(INITIAL_MESSAGES);
  const [inputValue, setInputValue] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    if (isOpen && scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isTyping, isOpen]);

  const handleSend = () => {
      if (!inputValue.trim()) return;
      if (onHaptic) onHaptic();

      const userMsg: Message = {
          id: Date.now(),
          text: inputValue,
          sender: 'user',
          timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages(prev => [...prev, userMsg]);
      setInputValue('');
      setIsTyping(true);

      // Simulate Agent Reply
      setTimeout(() => {
          const agentMsg: Message = {
              id: Date.now() + 1,
              text: "Request acknowledged. Processing ticket ID #" + randomInt(1000, 9999) + ". Please wait...",
              sender: 'agent',
              timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
          };
          setMessages(prev => [...prev, agentMsg]);
          setIsTyping(false);
      }, 2000);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
      if (e.key === 'Enter') handleSend();
  };

  const toggleChat = () => {
      if (onHaptic) onHaptic();
      onToggle(!isOpen);
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
            
            /* CRITICAL FIXES FOR SHAPES */
            .clip-hexagon {
                clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
                -webkit-clip-path: polygon(50% 0%, 100% 25%, 100% 75%, 50% 100%, 0% 75%, 0% 25%);
            }
        `}</style>

        {/* === WIDGET CONTAINER === */}
        {/* Dynamic bottom position: moves up if raiseOnMobile is true to clear HUD/Footers */}
        <div className={`fixed right-4 md:bottom-12 md:right-12 z-[100] flex flex-col items-end pointer-events-none transition-all duration-500 ease-in-out ${raiseOnMobile ? 'bottom-48' : 'bottom-24'}`}>
            
            <AnimatePresence mode="wait">
                
                {/* === STATE 1: OPEN WINDOW (RESIZED) === */}
                {isOpen ? (
                    <motion.div
                        key="window"
                        initial={{ opacity: 0, y: 40, scale: 0.8, filter: "blur(10px)" }}
                        animate={{ opacity: 1, y: 0, scale: 1, filter: "blur(0px)" }}
                        exit={{ opacity: 0, y: 40, scale: 0.8, filter: "blur(10px)" }}
                        transition={{ type: "spring", stiffness: 350, damping: 30 }}
                        className="pointer-events-auto w-[85vw] h-[50vh] md:w-[350px] md:h-[480px] bg-[#050505]/95 backdrop-blur-xl border border-pandora-cyan/30 shadow-[0_0_50px_rgba(0,255,255,0.15)] flex flex-col overflow-hidden relative rounded-sm"
                    >
                        {/* CRT Screen Effects */}
                        <div className="absolute inset-0 bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))] z-20 pointer-events-none bg-[length:100%_4px,3px_100%]" />
                        <div className="absolute top-0 left-0 right-0 h-px bg-white/20 z-20 shadow-[0_0_10px_white]" />

                        {/* Header */}
                        <div className="h-12 bg-pandora-cyan/10 border-b border-white/10 flex items-center justify-between px-3 shrink-0 relative z-30">
                            <div className="flex items-center gap-3">
                                <div className="w-6 h-6 bg-black/50 border border-pandora-cyan/30 flex items-center justify-center rounded-sm">
                                    <Terminal size={12} className="text-pandora-cyan" />
                                </div>
                                <div>
                                    <div className="font-mono font-bold text-[10px] tracking-widest text-white">UPLINK_SECURE</div>
                                    <div className="font-mono text-[8px] text-pandora-cyan flex items-center gap-1">
                                        <span className="w-1 h-1 bg-green-500 rounded-full animate-pulse" />
                                        CHANNEL_OPEN
                                    </div>
                                </div>
                            </div>
                            <button onClick={() => onToggle(false)} className="w-6 h-6 flex items-center justify-center text-gray-400 hover:text-white hover:bg-white/10 transition-all rounded-sm">
                                <ChevronDown size={14} />
                            </button>
                        </div>

                        {/* Chat Body */}
                        <div ref={scrollRef} className="flex-1 overflow-y-auto p-3 space-y-4 font-mono text-xs relative z-30 scrollbar-thin scrollbar-thumb-pandora-cyan/20 scrollbar-track-transparent">
                            {messages.map((msg) => (
                                <div key={msg.id} className={`flex ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
                                    <div className={`max-w-[90%] relative group ${msg.sender === 'user' ? 'items-end flex flex-col' : ''}`}>
                                        
                                        {/* Metadata */}
                                        <div className={`text-[8px] text-gray-600 mb-1 flex items-center gap-2 ${msg.sender === 'user' ? 'flex-row-reverse' : ''}`}>
                                            <span className="font-bold uppercase tracking-wider">{msg.sender === 'agent' ? 'Sys_Admin' : 'Operative'}</span>
                                            <span>{msg.timestamp}</span>
                                        </div>

                                        {/* Bubble */}
                                        <div className={`
                                            p-2.5 border backdrop-blur-sm relative text-[11px] leading-relaxed
                                            ${msg.sender === 'user' 
                                                ? 'bg-white/10 border-white/20 text-gray-100 rounded-sm rounded-tr-none' 
                                                : 'bg-pandora-cyan/5 border-pandora-cyan/30 text-pandora-cyan rounded-sm rounded-tl-none shadow-[0_0_15px_rgba(0,255,255,0.05)]'}
                                        `}>
                                            <p className="whitespace-pre-wrap">{msg.text}</p>
                                            
                                            {/* Decorative corners */}
                                            {msg.sender === 'agent' && (
                                                <div className="absolute top-0 left-0 w-1.5 h-1.5 border-t border-l border-pandora-cyan opacity-50" />
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))}
                            
                            {isTyping && (
                                <div className="flex justify-start">
                                    <div className="bg-pandora-cyan/5 border border-pandora-cyan/20 p-2 text-pandora-cyan text-[10px] flex items-center gap-2 rounded-sm rounded-tl-none">
                                        <Activity size={10} className="animate-pulse" />
                                        <span>ENCRYPTING_PACKET...</span>
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Input Area */}
                        <div className="p-3 bg-black/90 border-t border-white/10 shrink-0 relative z-30">
                            <div className="relative flex items-end gap-2 bg-[#0a0a0a] border border-white/10 p-1.5 rounded-sm focus-within:border-pandora-cyan/50 transition-colors">
                                <button className="p-1.5 text-gray-500 hover:text-white transition-colors h-8 flex items-center justify-center">
                                    <Paperclip size={14} />
                                </button>
                                <textarea 
                                    value={inputValue}
                                    onChange={(e) => setInputValue(e.target.value)}
                                    onKeyDown={handleKeyDown}
                                    placeholder="Enter system command..."
                                    className="flex-1 bg-transparent border-none outline-none text-white font-mono text-[11px] placeholder:text-gray-700 h-8 py-2 resize-none leading-relaxed"
                                    autoFocus
                                />
                                <button 
                                    onClick={handleSend}
                                    className={`h-8 w-8 flex items-center justify-center rounded-sm transition-all ${inputValue.trim() ? 'bg-pandora-cyan text-black hover:bg-white' : 'bg-white/5 text-gray-600'}`}
                                >
                                    <Send size={14} />
                                </button>
                            </div>
                            <div className="text-[8px] text-gray-600 font-mono mt-1.5 text-center flex items-center justify-center gap-2">
                                <div className="w-1 h-1 bg-green-500 rounded-full" />
                                E2E_ENCRYPTION_ACTIVE
                            </div>
                        </div>
                    </motion.div>
                ) : (
                    
                    /* === STATE 2: THE CYBERPUNK WIDGET (HUD STYLE) === */
                    <motion.div
                        key="widget"
                        initial={{ scale: 0, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        exit={{ scale: 0, opacity: 0 }}
                        className="pointer-events-auto relative group cursor-pointer"
                        onClick={toggleChat}
                    >
                        {/* 1. Status Label (Floating Next to Widget) - Hidden on Mobile */}
                        <motion.div 
                            initial={{ x: 20, opacity: 0 }}
                            animate={{ x: 0, opacity: 1 }}
                            transition={{ delay: 0.5 }}
                            className="absolute right-full mr-6 top-1/2 -translate-y-1/2 hidden md:flex items-center gap-3 pointer-events-none"
                        >
                            <div className="bg-black/80 backdrop-blur-md border border-white/10 px-3 py-1.5 rounded-sm shadow-xl">
                                <div className="text-[10px] font-bold text-pandora-cyan font-mono tracking-widest whitespace-nowrap flex items-center gap-2">
                                    <Activity size={10} className="animate-pulse" />
                                    SYSTEM_ONLINE
                                </div>
                            </div>
                            {/* Connecting Line */}
                            <div className="w-6 h-px bg-gradient-to-r from-white/20 to-pandora-cyan/50" />
                        </motion.div>

                        {/* 2. The Core Widget Container */}
                        <div className="relative w-16 h-16 md:w-20 md:h-20 flex items-center justify-center">
                            
                            {/* Rotating Outer Ring (Dashed) */}
                            <div className="absolute inset-0 rounded-full border border-dashed border-white/20 hud-spin" />
                            
                            {/* Counter-Rotating Inner Ring */}
                            <div className="absolute inset-1 rounded-full border border-t-transparent border-l-transparent border-pandora-cyan/30 hud-spin-rev" />
                            
                            {/* Pulsing Glow Background */}
                            <div className="absolute inset-2 bg-pandora-cyan/5 rounded-full blur-md animate-pulse" />
                            
                            {/* The Solid Hexagon Core (Now with proper clip-path) */}
                            <div className="relative z-10 w-10 h-10 md:w-12 md:h-12 bg-[#0a0a0a] flex items-center justify-center clip-hexagon group-hover:bg-pandora-cyan transition-colors duration-300 shadow-[0_0_20px_rgba(0,0,0,0.5)]">
                                <MessageSquare 
                                    size={20} 
                                    className="text-pandora-cyan group-hover:text-black transition-colors duration-300 relative z-20" 
                                />
                            </div>

                            {/* Notification Dot */}
                            <div className="absolute top-2 right-2 w-3 h-3 bg-red-500 rounded-full border-2 border-black z-20 shadow-[0_0_10px_red] animate-bounce">
                                <span className="absolute inset-0 rounded-full bg-red-500 animate-ping opacity-75" />
                            </div>

                        </div>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>

        {/* Mobile Backdrop (Only when open) */}
        <AnimatePresence>
            {isOpen && (
                <motion.div 
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                    onClick={() => onToggle(false)}
                    className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[90] md:hidden"
                />
            )}
        </AnimatePresence>
    </>
  );
};

export default SupportChat;
