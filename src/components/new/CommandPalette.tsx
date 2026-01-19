import { AnimatePresence, motion } from "framer-motion";
import { ChevronRight, Package, Search, Shield, ShoppingCart, Terminal, User } from "lucide-react";
import type React from "react";
import { memo, useEffect, useMemo, useRef, useState } from "react";
import type { CatalogProduct, NavigationTarget } from "../../types/component";

// Navigation views available in command palette (subset of ViewType)
type NavView = "home" | "orders" | "profile" | "leaderboard";

// Command palette item types
interface CommandItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  type: "nav";
  view: NavView;
}

interface ProductItem {
  id: string;
  label: string;
  icon: React.ReactNode;
  type: "product";
  product: CatalogProduct;
}

type PaletteItem = CommandItem | ProductItem;

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onNavigate: (view: NavigationTarget) => void;
  products: CatalogProduct[];
}

const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onNavigate,
  products,
}) => {
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  // Focus input on open
  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
      setQuery("");
      setSelectedIndex(0);
    }
  }, [isOpen]);

  // Filtering Logic - memoized for performance
  const commands: CommandItem[] = useMemo(
    () => [
      {
        id: "home",
        label: "Go to Catalog",
        icon: <Package size={14} />,
        type: "nav" as const,
        view: "home" as const,
      },
      {
        id: "orders",
        label: "My Orders / Logs",
        icon: <Terminal size={14} />,
        type: "nav" as const,
        view: "orders" as const,
      },
      {
        id: "profile",
        label: "Operative Profile",
        icon: <User size={14} />,
        type: "nav" as const,
        view: "profile" as const,
      },
      {
        id: "leaderboard",
        label: "Global Leaderboard",
        icon: <Shield size={14} />,
        type: "nav" as const,
        view: "leaderboard" as const,
      },
    ],
    []
  );

  const filteredItems = useMemo((): PaletteItem[] => {
    if (!query) {
      return commands;
    }

    const queryLower = query.toLowerCase();
    const filteredCommands = commands.filter((c) => c.label.toLowerCase().includes(queryLower));
    const productResults: ProductItem[] = products
      .filter((p) => p.name.toLowerCase().includes(queryLower))
      .map((p) => ({
        id: `prod-${p.id}`,
        label: p.name,
        icon: <ShoppingCart size={14} />,
        type: "product" as const,
        product: p,
      }));

    return [...filteredCommands, ...productResults];
  }, [query, products, commands]);

  // Keyboard Navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % filteredItems.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filteredItems.length) % filteredItems.length);
    } else if (e.key === "Enter") {
      e.preventDefault();
      executeCommand(filteredItems[selectedIndex]);
    } else if (e.key === "Escape") {
      onClose();
    }
  };

  const executeCommand = (item: PaletteItem | undefined) => {
    if (!item) {
      return;
    }
    if (item.type === "nav") {
      onNavigate(item.view);
    } else if (item.type === "product") {
      onNavigate({ type: "product", product: item.product });
    }
    onClose();
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-[200] flex items-start justify-center px-4 pt-[15vh]">
          {/* Backdrop */}
          <motion.div
            animate={{ opacity: 1 }}
            className="absolute inset-0 bg-black/80 backdrop-blur-sm"
            exit={{ opacity: 0 }}
            initial={{ opacity: 0 }}
            onClick={onClose}
          />

          {/* Modal */}
          <motion.div
            animate={{ scale: 1, opacity: 1, y: 0 }}
            className="relative flex max-h-[60vh] w-full max-w-2xl flex-col overflow-hidden rounded-sm border border-white/20 bg-[#0a0a0a] shadow-[0_0_50px_rgba(0,0,0,0.8)]"
            exit={{ scale: 0.95, opacity: 0, y: -20 }}
            initial={{ scale: 0.95, opacity: 0, y: -20 }}
            transition={{ type: "spring", stiffness: 300, damping: 25 }}
          >
            {/* Header / Input */}
            <div className="relative z-10 flex items-center gap-4 border-white/10 border-b bg-white/5 p-4">
              <Search className="text-gray-500" size={20} />
              <input
                className="flex-1 border-none bg-transparent font-mono text-lg text-white outline-none placeholder:text-gray-600"
                onChange={(e) => {
                  setQuery(e.target.value);
                  setSelectedIndex(0);
                }}
                onKeyDown={handleKeyDown}
                placeholder="Type a command or search assets..."
                ref={inputRef}
                type="text"
                value={query}
              />
              <div className="hidden items-center gap-1 rounded-sm border border-white/10 px-2 py-1 font-mono text-[10px] text-gray-500 md:flex">
                <span className="text-xs">ESC</span> TO CLOSE
              </div>
            </div>

            {/* Results */}
            <div className="scrollbar-hide overflow-y-auto p-2">
              {filteredItems.length === 0 ? (
                <div className="py-12 text-center font-mono text-gray-600 text-xs">
                  NO_RESULTS_FOUND_IN_DATABASE
                </div>
              ) : (
                <div className="space-y-1">
                  {filteredItems.map((item, index) => (
                    <button
                      className={`group flex w-full items-center justify-between rounded-sm p-3 transition-all ${
                        index === selectedIndex
                          ? "bg-pandora-cyan text-black shadow-[0_0_15px_rgba(0,255,255,0.4)]"
                          : "text-gray-400 hover:bg-white/5"
                      }`}
                      key={item.id}
                      onClick={() => executeCommand(item)}
                      onMouseEnter={() => setSelectedIndex(index)}
                      type="button"
                    >
                      <div className="flex items-center gap-3">
                        <div
                          className={`rounded-sm p-1.5 ${index === selectedIndex ? "bg-black/20 text-black" : "bg-white/5 text-gray-500"}`}
                        >
                          {item.icon}
                        </div>
                        <span
                          className={`font-mono text-sm ${index === selectedIndex ? "font-bold" : ""}`}
                        >
                          {item.label}
                        </span>
                      </div>
                      {index === selectedIndex && (
                        <div className="flex animate-pulse items-center gap-2 font-bold text-[10px] uppercase tracking-wider">
                          <ChevronRight size={12} />
                          Execute
                        </div>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>

            {/* Footer */}
            <div className="flex justify-between border-white/10 border-t bg-[#050505] p-2 px-4 font-mono text-[9px] text-gray-600">
              <span>PANDORA_OS {/* V.2.4.0 */}</span>
              <div className="flex gap-4">
                <span>
                  <span className="text-pandora-cyan">↑↓</span> NAVIGATE
                </span>
                <span>
                  <span className="text-pandora-cyan">↵</span> SELECT
                </span>
              </div>
            </div>

            {/* Scanline */}
            <div
              className="pointer-events-none absolute inset-0 opacity-[0.03]"
              style={{
                backgroundImage: `url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noiseFilter'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.9' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noiseFilter)'/%3E%3C/svg%3E")`,
              }}
            />
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};

export default memo(CommandPalette);
