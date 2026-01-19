import { AnimatePresence, motion } from "framer-motion";
import { Activity, ChevronDown, MessageSquare, Paperclip, Send, Terminal } from "lucide-react";
import type React from "react";
import { useEffect, useRef, useState } from "react";
import { useLocale } from "../../hooks/useLocale";
import { randomInt } from "../../utils/random";

interface SupportChatProps {
  isOpen: boolean;
  onToggle: (isOpen: boolean) => void;
  onHaptic?: () => void;
  raiseOnMobile?: boolean;
}

interface Message {
  id: number;
  text: string;
  sender: "user" | "agent";
  timestamp: string;
}

const SupportChat: React.FC<SupportChatProps> = ({
  isOpen,
  onToggle,
  onHaptic,
  raiseOnMobile = false,
}) => {
  const { t } = useLocale();
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Initialize messages with translations
  useEffect(() => {
    if (messages.length === 0) {
      setMessages([
        { id: 1, text: t("support.messages.connecting"), sender: "agent", timestamp: "SYSTEM" },
        { id: 2, text: t("support.messages.connected"), sender: "agent", timestamp: "SYSTEM" },
        { id: 3, text: t("support.messages.greeting"), sender: "agent", timestamp: "10:00" },
      ]);
    }
  }, [t, messages.length]); // Only on mount/locale change if empty

  // Auto-scroll to bottom
  useEffect(() => {
    if (isOpen && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [isOpen]);

  const handleSend = () => {
    if (!inputValue.trim()) return;
    if (onHaptic) onHaptic();

    const userMsg: Message = {
      id: Date.now(),
      text: inputValue,
      sender: "user",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMsg]);
    setInputValue("");
    setIsTyping(true);

    // Simulate Agent Reply
    setTimeout(() => {
      const agentMsg: Message = {
        id: Date.now() + 1,
        text: t("support.messages.acknowledged", { id: randomInt(1000, 9999) }),
        sender: "agent",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };
      setMessages((prev) => [...prev, agentMsg]);
      setIsTyping(false);
    }, 2000);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") handleSend();
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
      <div
        className={`pointer-events-none fixed right-4 z-[100] flex flex-col items-end transition-all duration-500 ease-in-out md:right-12 md:bottom-12 ${raiseOnMobile ? "bottom-48" : "bottom-24"}`}
      >
        <AnimatePresence mode="wait">
          {/* === STATE 1: OPEN WINDOW (RESIZED) === */}
          {isOpen ? (
            <motion.div
              animate={{ opacity: 1, y: 0, scale: 1, filter: "blur(0px)" }}
              className="pointer-events-auto relative flex h-[50vh] w-[85vw] flex-col overflow-hidden rounded-sm border border-pandora-cyan/30 bg-[#050505]/95 shadow-[0_0_50px_rgba(0,255,255,0.15)] backdrop-blur-xl md:h-[480px] md:w-[350px]"
              exit={{ opacity: 0, y: 40, scale: 0.8, filter: "blur(10px)" }}
              initial={{ opacity: 0, y: 40, scale: 0.8, filter: "blur(10px)" }}
              key="window"
              transition={{ type: "spring", stiffness: 350, damping: 30 }}
            >
              {/* CRT Screen Effects */}
              <div className="pointer-events-none absolute inset-0 z-20 bg-[length:100%_4px,3px_100%] bg-[linear-gradient(rgba(18,16,16,0)_50%,rgba(0,0,0,0.25)_50%),linear-gradient(90deg,rgba(255,0,0,0.06),rgba(0,255,0,0.02),rgba(0,0,255,0.06))]" />
              <div className="absolute top-0 right-0 left-0 z-20 h-px bg-white/20 shadow-[0_0_10px_white]" />

              {/* Header */}
              <div className="relative z-30 flex h-12 shrink-0 items-center justify-between border-white/10 border-b bg-pandora-cyan/10 px-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-6 w-6 items-center justify-center rounded-sm border border-pandora-cyan/30 bg-black/50">
                    <Terminal className="text-pandora-cyan" size={12} />
                  </div>
                  <div>
                    <div className="font-bold font-mono text-[10px] text-white tracking-widest">
                      {t("support.title")}
                    </div>
                    <div className="flex items-center gap-1 font-mono text-[8px] text-pandora-cyan">
                      <span className="h-1 w-1 animate-pulse rounded-full bg-green-500" />
                      {t("support.channelOpen")}
                    </div>
                  </div>
                </div>
                <button
                  className="flex h-6 w-6 items-center justify-center rounded-sm text-gray-400 transition-all hover:bg-white/10 hover:text-white"
                  onClick={() => onToggle(false)}
                  type="button"
                >
                  <ChevronDown size={14} />
                </button>
              </div>

              {/* Chat Body */}
              <div
                className="scrollbar-thin scrollbar-thumb-pandora-cyan/20 scrollbar-track-transparent relative z-30 flex-1 space-y-4 overflow-y-auto p-3 font-mono text-xs"
                ref={scrollRef}
              >
                {messages.map((msg) => (
                  <div
                    className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"}`}
                    key={msg.id}
                  >
                    <div
                      className={`group relative max-w-[90%] ${msg.sender === "user" ? "flex flex-col items-end" : ""}`}
                    >
                      {/* Metadata */}
                      <div
                        className={`mb-1 flex items-center gap-2 text-[8px] text-gray-600 ${msg.sender === "user" ? "flex-row-reverse" : ""}`}
                      >
                        <span className="font-bold uppercase tracking-wider">
                          {msg.sender === "agent"
                            ? t("support.sender.agent")
                            : t("support.sender.user")}
                        </span>
                        <span>{msg.timestamp}</span>
                      </div>

                      {/* Bubble */}
                      <div
                        className={`relative border p-2.5 text-[11px] leading-relaxed backdrop-blur-sm ${
                          msg.sender === "user"
                            ? "rounded-sm rounded-tr-none border-white/20 bg-white/10 text-gray-100"
                            : "rounded-sm rounded-tl-none border-pandora-cyan/30 bg-pandora-cyan/5 text-pandora-cyan shadow-[0_0_15px_rgba(0,255,255,0.05)]"
                        }
                                        `}
                      >
                        <p className="whitespace-pre-wrap">{msg.text}</p>

                        {/* Decorative corners */}
                        {msg.sender === "agent" && (
                          <div className="absolute top-0 left-0 h-1.5 w-1.5 border-pandora-cyan border-t border-l opacity-50" />
                        )}
                      </div>
                    </div>
                  </div>
                ))}

                {isTyping && (
                  <div className="flex justify-start">
                    <div className="flex items-center gap-2 rounded-sm rounded-tl-none border border-pandora-cyan/20 bg-pandora-cyan/5 p-2 text-[10px] text-pandora-cyan">
                      <Activity className="animate-pulse" size={10} />
                      <span>{t("support.typing")}</span>
                    </div>
                  </div>
                )}
              </div>

              {/* Input Area */}
              <div className="relative z-30 shrink-0 border-white/10 border-t bg-black/90 p-3">
                <div className="relative flex items-end gap-2 rounded-sm border border-white/10 bg-[#0a0a0a] p-1.5 transition-colors focus-within:border-pandora-cyan/50">
                  <button
                    className="flex h-8 items-center justify-center p-1.5 text-gray-500 transition-colors hover:text-white"
                    type="button"
                  >
                    <Paperclip size={14} />
                  </button>
                  <textarea
                    className="h-8 flex-1 resize-none border-none bg-transparent py-2 font-mono text-[11px] text-white leading-relaxed outline-none placeholder:text-gray-700"
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder={t("support.inputPlaceholder")}
                    value={inputValue}
                  />
                  <button
                    className={`flex h-8 w-8 items-center justify-center rounded-sm transition-all ${inputValue.trim() ? "bg-pandora-cyan text-black hover:bg-white" : "bg-white/5 text-gray-600"}`}
                    onClick={handleSend}
                    type="button"
                  >
                    <Send size={14} />
                  </button>
                </div>
                <div className="mt-1.5 flex items-center justify-center gap-2 text-center font-mono text-[8px] text-gray-600">
                  <div className="h-1 w-1 rounded-full bg-green-500" />
                  {t("support.encryption")}
                </div>
              </div>
            </motion.div>
          ) : (
            /* === STATE 2: THE CYBERPUNK WIDGET (HUD STYLE) === */
            <motion.div
              animate={{ scale: 1, opacity: 1 }}
              className="group pointer-events-auto relative cursor-pointer"
              exit={{ scale: 0, opacity: 0 }}
              initial={{ scale: 0, opacity: 0 }}
              key="widget"
              onClick={toggleChat}
            >
              {/* 1. Status Label (Floating Next to Widget) - Hidden on Mobile */}
              <motion.div
                animate={{ x: 0, opacity: 1 }}
                className="pointer-events-none absolute top-1/2 right-full mr-6 hidden -translate-y-1/2 items-center gap-3 md:flex"
                initial={{ x: 20, opacity: 0 }}
                transition={{ delay: 0.5 }}
              >
                <div className="rounded-sm border border-white/10 bg-black/80 px-3 py-1.5 shadow-xl backdrop-blur-md">
                  <div className="flex items-center gap-2 whitespace-nowrap font-bold font-mono text-[10px] text-pandora-cyan tracking-widest">
                    <Activity className="animate-pulse" size={10} />
                    {t("support.systemOnline")}
                  </div>
                </div>
                {/* Connecting Line */}
                <div className="h-px w-6 bg-gradient-to-r from-white/20 to-pandora-cyan/50" />
              </motion.div>

              {/* 2. The Core Widget Container */}
              <div className="relative flex h-16 w-16 items-center justify-center md:h-20 md:w-20">
                {/* Rotating Outer Ring (Dashed) */}
                <div className="hud-spin absolute inset-0 rounded-full border border-white/20 border-dashed" />

                {/* Counter-Rotating Inner Ring */}
                <div className="hud-spin-rev absolute inset-1 rounded-full border border-pandora-cyan/30 border-t-transparent border-l-transparent" />

                {/* Pulsing Glow Background */}
                <div className="absolute inset-2 animate-pulse rounded-full bg-pandora-cyan/5 blur-md" />

                {/* The Solid Hexagon Core (Now with proper clip-path) */}
                <div className="clip-hexagon relative z-10 flex h-10 w-10 items-center justify-center bg-[#0a0a0a] shadow-[0_0_20px_rgba(0,0,0,0.5)] transition-colors duration-300 group-hover:bg-pandora-cyan md:h-12 md:w-12">
                  <MessageSquare
                    className="relative z-20 text-pandora-cyan transition-colors duration-300 group-hover:text-black"
                    size={20}
                  />
                </div>

                {/* Notification Dot */}
                <div className="absolute top-2 right-2 z-20 h-3 w-3 animate-bounce rounded-full border-2 border-black bg-red-500 shadow-[0_0_10px_red]">
                  <span className="absolute inset-0 animate-ping rounded-full bg-red-500 opacity-75" />
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
            animate={{ opacity: 1 }}
            className="fixed inset-0 z-[90] bg-black/60 backdrop-blur-sm md:hidden"
            exit={{ opacity: 0 }}
            initial={{ opacity: 0 }}
            onClick={() => onToggle(false)}
          />
        )}
      </AnimatePresence>
    </>
  );
};

export default SupportChat;
