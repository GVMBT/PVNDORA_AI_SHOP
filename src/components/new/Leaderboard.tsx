import { motion } from "framer-motion";
import {
  Activity,
  ArrowLeft,
  Crown,
  ShieldCheck,
  Terminal,
  TrendingUp,
  Trophy,
  User,
} from "lucide-react";
import React, { useState } from "react";
import { useLocaleContext } from "../../contexts/LocaleContext";
import { useLocale } from "../../hooks/useLocale";
import { formatPrice } from "../../utils/currency";

// Type matching LeaderboardUser from types/component
interface LeaderboardUserData {
  rank: number;
  name: string;
  handle: string;
  marketSpend: number;
  actualSpend: number;
  saved: number;
  modules: number;
  trend: "up" | "down" | "same";
  status: "ONLINE" | "AWAY" | "BUSY" | "OFFLINE";
  isMe?: boolean;
  avatarUrl?: string; // optional avatar if backend provides
  currency?: string; // Currency code (USD, RUB, etc.)
}

interface LeaderboardProps {
  leaderboardData?: LeaderboardUserData[];
  currency?: string; // Currency code for formatting prices
  onBack: () => void;
  onLoadMore?: () => void;
  hasMore?: boolean;
  isLoadingMore?: boolean;
  onFilterChange?: (filter: "weekly" | "all_time") => void;
  activeFilter?: "weekly" | "all_time";
}

// MOCK DATA removed - use real API data only

// Type for podium ranks
type PodiumRank = 1 | 2 | 3;

// Helper constants for podium styling (reduces cognitive complexity)
const RANK_LABELS = { 1: "RANK_01", 2: "RANK_02", 3: "RANK_03" } as const;
const ORDER_CLASSES = {
  1: "order-1 md:order-2 relative z-10 mt-0 md:-mt-12 mb-4 md:mb-0",
  2: "order-2 md:order-1 relative group",
  3: "order-3 md:order-3 relative group",
} as const;

// Helper function to get podium styles (reduces cognitive complexity)
const getPodiumStyles = (rank: PodiumRank) => {
  const isFirst = rank === 1;
  return {
    isFirst,
    containerClasses: isFirst
      ? "bg-[#050505] border border-pandora-cyan p-1 relative rounded-sm"
      : "bg-[#0e0e0e] border border-white/10 p-6 relative overflow-hidden hover:border-pandora-cyan/30 transition-colors",
    innerClasses: isFirst ? "bg-[#0a0a0a] p-4 sm:p-8 relative" : "",
    avatarSize: isFirst ? "w-24 h-24" : "w-16 h-16",
    borderClasses: isFirst ? "border-2 border-pandora-cyan" : "border border-white/20",
    nameClasses: isFirst ? "font-display text-xl sm:text-2xl tracking-wide" : "text-lg",
    handleClasses: isFirst ? "mb-6 text-sm" : "mb-4 text-xs",
    statBoxClasses: isFirst
      ? "bg-pandora-cyan/10 border border-pandora-cyan/30 p-3 overflow-hidden text-center"
      : "bg-white/5 border border-white/5 p-2",
    statLabelClasses: isFirst
      ? "text-pandora-cyan uppercase font-bold truncate"
      : "text-gray-500 uppercase",
    statValueClasses: isFirst
      ? "text-lg sm:text-2xl whitespace-normal break-all sm:break-normal leading-tight"
      : "text-lg",
  };
};

// Vacant podium slot component (reduces cognitive complexity)
const VacantPodiumSlot: React.FC<{ rank: 1 | 2 | 3; t: (key: string) => string }> = ({
  rank,
  t,
}) => (
  <div className={ORDER_CLASSES[rank]}>
    <div className="bg-[#0e0e0e] border border-white/5 p-6 opacity-30">
      <div className="absolute top-0 left-0 bg-white/5 px-2 py-1 text-[10px] font-bold font-mono text-gray-600">
        {RANK_LABELS[rank]}
      </div>
      <div className="flex flex-col items-center text-center mt-4">
        <div className="w-16 h-16 rounded-full border border-white/10 mb-3 flex items-center justify-center">
          <span className="text-gray-600 text-2xl">?</span>
        </div>
        <h3 className="font-bold text-gray-600 text-lg">{t("leaderboard.vacant").toUpperCase()}</h3>
      </div>
    </div>
  </div>
);

// Helper component for podium rank (reduces cognitive complexity)
interface PodiumRankProps {
  user: LeaderboardUserData | null;
  rank: PodiumRank;
  displayCurrency: string;
  t: (key: string) => string;
  isVacant: boolean;
}

const PodiumRank: React.FC<PodiumRankProps> = ({ user, rank, displayCurrency, t, isVacant }) => {
  if (isVacant || !user) {
    return <VacantPodiumSlot rank={rank} t={t} />;
  }

  const styles = getPodiumStyles(rank);
  const {
    isFirst,
    containerClasses,
    innerClasses,
    avatarSize,
    borderClasses,
    nameClasses,
    handleClasses,
    statBoxClasses,
    statLabelClasses,
    statValueClasses,
  } = styles;

  const content = (
    <>
      {isFirst && (
        <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-pandora-cyan text-black p-2 rounded-full shadow-[0_0_20px_#00FFFF] z-20">
          <Crown size={20} fill="currentColor" />
        </div>
      )}
      <div
        className={`absolute top-0 left-0 bg-white/10 px-2 py-1 text-[10px] font-bold font-mono ${isFirst ? "hidden" : "text-gray-300"}`}
      >
        {RANK_LABELS[rank]}
      </div>
      <div className="flex flex-col items-center text-center mt-4">
        <div
          className={`${avatarSize} rounded-full ${borderClasses} p-1 ${isFirst ? "mb-4" : "mb-3"} overflow-hidden bg-gray-900 flex items-center justify-center ${isFirst ? "relative" : ""}`}
        >
          {isFirst && (
            <div className="absolute inset-0 rounded-full border border-pandora-cyan animate-ping opacity-20" />
          )}
          {isFirst && (
            <div className="absolute inset-0 bg-gradient-to-tr from-pandora-cyan/20 to-transparent" />
          )}
          {user.avatarUrl ? (
            <img
              src={user.avatarUrl}
              alt={user.name}
              className={`w-full h-full object-cover rounded-full ${isFirst ? "relative z-10" : ""}`}
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = "none";
              }}
            />
          ) : null}
          {isFirst ? (
            <Crown
              size={32}
              className={`text-pandora-cyan/50 relative z-10 ${user.avatarUrl ? "hidden" : ""}`}
            />
          ) : (
            <User
              size={24}
              className={`text-gray-500 absolute ${user.avatarUrl ? "hidden" : ""}`}
            />
          )}
          {isFirst && (
            <div className="absolute -bottom-1 -right-1 w-6 h-6 bg-pandora-cyan rounded-full flex items-center justify-center text-black font-bold text-xs shadow-[0_0_10px_#00FFFF] z-20">
              1
            </div>
          )}
        </div>
        <h3 className={`font-bold text-white ${nameClasses}`}>{user.name}</h3>
        <div className={`font-mono text-pandora-cyan ${handleClasses}`}>{user.handle}</div>
        <div className={`w-full ${statBoxClasses} rounded-sm`}>
          <div className={`text-[9px] ${statLabelClasses}`}>{t("leaderboard.totalSaved")}</div>
          <div className={`font-bold text-white ${statValueClasses}`}>
            {formatPrice(user.saved, user.currency || displayCurrency)}
          </div>
        </div>
      </div>
    </>
  );

  return (
    <div className={ORDER_CLASSES[rank]}>
      {!isFirst && (
        <div className="absolute inset-0 bg-gradient-to-b from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
      )}
      {isFirst && <div className="absolute inset-0 bg-pandora-cyan/20 blur-3xl -z-10" />}
      <div className={containerClasses}>
        {isFirst ? <div className={innerClasses}>{content}</div> : content}
      </div>
    </div>
  );
};

// Helper component for list item (reduces cognitive complexity)
interface LeaderboardListItemProps {
  user: LeaderboardUserData;
  displayCurrency: string;
  t: (key: string) => string;
}

const LeaderboardListItem: React.FC<LeaderboardListItemProps> = ({ user, displayCurrency, t }) => {
  return (
    <div className="group relative bg-[#0a0a0a] border border-white/5 hover:border-pandora-cyan/50 transition-all duration-300">
      <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-pandora-cyan opacity-0 group-hover:opacity-100 transition-opacity" />
      <div className="grid grid-cols-12 gap-4 items-center p-4">
        <div className="col-span-2 md:col-span-1 text-center font-display font-bold text-gray-600 group-hover:text-white transition-colors">
          {user.rank.toString().padStart(2, "0")}
        </div>
        <div className="col-span-10 md:col-span-5 flex items-center gap-4">
          <div className="w-8 h-8 bg-white/5 rounded-sm flex items-center justify-center border border-white/10 shrink-0 overflow-hidden">
            {user.avatarUrl ? (
              <img
                src={user.avatarUrl}
                alt={user.name}
                className="w-full h-full object-cover"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = "none";
                  (e.target as HTMLImageElement).nextElementSibling?.classList.remove("hidden");
                }}
              />
            ) : null}
            <User
              size={14}
              className={`text-gray-500 group-hover:text-pandora-cyan ${user.avatarUrl ? "hidden" : ""}`}
            />
          </div>
          <div className="min-w-0">
            <div className="text-sm font-bold text-white group-hover:text-pandora-cyan transition-colors flex items-center gap-2 truncate">
              {user.name}
              {user.status === "ONLINE" && (
                <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse shrink-0" />
              )}
            </div>
            <div className="text-[10px] font-mono text-gray-600 truncate">{user.handle}</div>
          </div>
        </div>
        <div className="col-span-6 md:col-span-3 text-center mt-2 md:mt-0">
          <span className="md:hidden text-[10px] text-gray-500 font-mono uppercase mr-2">
            {t("leaderboard.purchases")}:
          </span>
          <span className="font-mono text-gray-400">{user.modules}</span>
        </div>
        <div className="col-span-6 md:col-span-3 text-right mt-2 md:mt-0 flex justify-end md:block items-center">
          <span className="md:hidden text-[10px] text-gray-500 font-mono uppercase mr-2">
            {t("leaderboard.totalSaved")}:
          </span>
          <div className="font-display font-bold text-white text-lg group-hover:text-pandora-cyan transition-colors">
            {formatPrice(user.saved, user.currency || displayCurrency)}
          </div>
        </div>
      </div>
    </div>
  );
};

const Leaderboard: React.FC<LeaderboardProps> = ({
  leaderboardData: propData,
  currency = "USD",
  onBack,
  onLoadMore,
  hasMore = false,
  isLoadingMore = false,
  onFilterChange,
  activeFilter = "all_time",
}) => {
  const { t } = useLocale();
  const { currency: contextCurrency } = useLocaleContext();
  // Use controlled filter from parent or internal state
  const [internalFilter, setInternalFilter] = useState<"weekly" | "all_time">("all_time");
  const filter = onFilterChange ? activeFilter : internalFilter;

  const handleFilterChange = (newFilter: "weekly" | "all_time") => {
    if (onFilterChange) {
      onFilterChange(newFilter);
    } else {
      setInternalFilter(newFilter);
    }
  };

  const loadMoreTriggerRef = React.useRef<HTMLDivElement | null>(null);

  // Track whether we can load more - use refs to avoid observer recreation
  const canLoadMoreRef = React.useRef(hasMore && !isLoadingMore);
  const onLoadMoreRef = React.useRef(onLoadMore);

  // Keep refs in sync
  React.useEffect(() => {
    canLoadMoreRef.current = hasMore && !isLoadingMore;
  }, [hasMore, isLoadingMore]);

  React.useEffect(() => {
    onLoadMoreRef.current = onLoadMore;
  }, [onLoadMore]);

  // Use provided data - NO MOCK fallback (mock data causes confusion)
  const data = propData || [];

  // Determine currency: prioritize context currency (user preference), then props, then default to USD
  const displayCurrency = contextCurrency || currency || "USD";

  // Extract top 3 for podium display (may have less than 3)
  const topThree = data.slice(0, 3);

  // Rest of the list (excluding top 3, no duplicates)
  const restList = data.slice(3);

  // Setup infinite scroll observer - watch for sentinel at end of list
  React.useEffect(() => {
    if (!onLoadMore || !loadMoreTriggerRef.current) return;

    const observer = new IntersectionObserver(
      (entries) => {
        const first = entries[0];
        if (first.isIntersecting && canLoadMoreRef.current && onLoadMoreRef.current) {
          onLoadMoreRef.current();
        }
      },
      { threshold: 0.1 }
    );

    observer.observe(loadMoreTriggerRef.current);

    return () => {
      observer.disconnect();
    };
  }, [onLoadMore]); // Re-attach when list changes

  // Find current user for the sticky footer
  const currentUser = data.find((u) => u.isMe);

  // Check if we have enough data for podium
  const hasRank1 = topThree.length >= 1;
  const hasRank2 = topThree.length >= 2;
  const hasRank3 = topThree.length >= 3;

  // Aggregate totals for header stats
  const totalSavedAggregate = data.reduce((acc, u) => acc + (u.saved || 0), 0);

  // Empty state when no data
  if (data.length === 0 && !isLoadingMore) {
    return (
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="min-h-screen text-white pt-20 md:pt-24 pb-32 px-4 md:px-8 md:pl-28 relative"
      >
        <div className="max-w-7xl mx-auto">
          <button
            type="button"
            onClick={onBack}
            className="flex items-center gap-2 text-[10px] font-mono text-gray-500 hover:text-pandora-cyan mb-4 transition-colors"
          >
            <ArrowLeft size={12} /> {t("empty.returnToBase").toUpperCase()}
          </button>
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <Trophy size={64} className="text-gray-700 mb-6" />
            <h2 className="text-2xl font-bold text-white mb-2">
              {t("leaderboard.empty").toUpperCase()}
            </h2>
            <p className="text-gray-500 font-mono text-sm max-w-md">{t("leaderboard.emptyHint")}</p>
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen text-white pt-20 md:pt-24 pb-48 md:pb-32 px-4 md:px-8 md:pl-28 relative overflow-hidden"
    >
      {/* Ambient Glows */}
      <div className="fixed top-0 left-1/2 -translate-x-1/2 w-[500px] h-[300px] bg-pandora-cyan/10 blur-[120px] pointer-events-none z-0" />

      {/* EXPANDED CONTAINER: max-w-7xl to match Catalog/Footer */}
      <div className="max-w-7xl mx-auto relative z-10">
        {/* === HEADER SECTION === */}
        <div className="flex flex-col md:flex-row justify-between items-end gap-8 mb-8 md:mb-16">
          <div className="w-full md:w-auto">
            <button
              type="button"
              onClick={onBack}
              className="flex items-center gap-2 text-[10px] font-mono text-gray-500 hover:text-pandora-cyan mb-4 transition-colors"
            >
              <ArrowLeft size={12} /> {t("empty.returnToBase").toUpperCase()}
            </button>
            <h1 className="text-3xl sm:text-4xl md:text-6xl font-display font-black text-white uppercase tracking-tighter leading-[0.9] mb-4">
              {t("leaderboard.titlePrefix")} <br />{" "}
              <span className="text-transparent bg-clip-text bg-gradient-to-r from-pandora-cyan to-white/50">
                {t("leaderboard.title")}
              </span>
            </h1>
            <div className="text-sm font-mono text-gray-500 uppercase tracking-widest mb-4">
              {t("leaderboard.subtitle")}
            </div>
            <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-pandora-cyan/70">
              <span className="flex items-center gap-1 bg-pandora-cyan/10 px-2 py-1 rounded-sm">
                <Activity size={12} /> {t("leaderboard.networkActivity").toUpperCase()}: HIGH
              </span>
              <span className="hidden sm:inline">|</span>
              <span className="hidden sm:inline">CYCLE_HASH: #A92-B</span>
            </div>
          </div>

          {/* Global Stats Card */}
          <div className="w-full md:w-auto bg-[#0a0a0a] border border-white/10 p-4 rounded-sm relative overflow-hidden group">
            <div className="absolute inset-0 bg-pandora-cyan/5 translate-y-full group-hover:translate-y-0 transition-transform duration-500" />
            <div className="relative z-10">
              <div className="text-[9px] font-mono text-gray-500 uppercase tracking-widest mb-1 flex items-center gap-2">
                <ShieldCheck size={10} className="text-pandora-cyan" />{" "}
                {t("leaderboard.corporateLoss")}
              </div>
              <div className="text-xl sm:text-2xl md:text-3xl font-mono font-bold text-white tracking-tight tabular-nums break-all sm:break-normal">
                {formatPrice(totalSavedAggregate, displayCurrency)}
              </div>
            </div>
            {/* Decorative Corner */}
            <div className="absolute top-0 right-0 w-3 h-3 border-t border-r border-pandora-cyan opacity-50" />
          </div>
        </div>

        {/* === TOP 3 OPERATIVES (PODIUM) === */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6 items-end mb-12 md:mb-20 relative">
          <PodiumRank
            user={hasRank2 ? topThree[1] : null}
            rank={2}
            displayCurrency={displayCurrency}
            t={t}
            isVacant={!hasRank2}
          />
          <PodiumRank
            user={hasRank1 ? topThree[0] : null}
            rank={1}
            displayCurrency={displayCurrency}
            t={t}
            isVacant={!hasRank1}
          />
          <PodiumRank
            user={hasRank3 ? topThree[2] : null}
            rank={3}
            displayCurrency={displayCurrency}
            t={t}
            isVacant={!hasRank3}
          />
        </div>

        {/* === MAIN LIST === */}
        <div className="space-y-4 mb-32 md:mb-24">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm md:text-lg font-bold text-white flex items-center gap-2">
              <Terminal size={16} className="text-pandora-cyan" />
              ACTIVE_AGENTS_LIST
            </h3>
            <div className="flex bg-[#0a0a0a] border border-white/10 p-0.5 rounded-sm">
              <button
                type="button"
                onClick={() => handleFilterChange("weekly")}
                className={`px-3 py-1.5 text-[9px] font-mono font-bold uppercase transition-colors ${filter === "weekly" ? "bg-white/10 text-white" : "text-gray-600 hover:text-gray-400"}`}
              >
                {t("leaderboard.weekly")}
              </button>
              <button
                type="button"
                onClick={() => handleFilterChange("all_time")}
                className={`px-3 py-1.5 text-[9px] font-mono font-bold uppercase transition-colors ${filter === "all_time" ? "bg-white/10 text-white" : "text-gray-600 hover:text-gray-400"}`}
              >
                {t("leaderboard.allTime")}
              </button>
            </div>
          </div>

          {/* List Header */}
          <div className="hidden md:grid grid-cols-12 gap-4 px-6 py-2 text-[10px] font-mono text-gray-500 uppercase tracking-wider">
            <div className="col-span-1 text-center">#</div>
            <div className="col-span-5">{t("leaderboard.participant")}</div>
            <div className="col-span-3 text-center">{t("leaderboard.purchases")}</div>
            <div className="col-span-3 text-right">{t("leaderboard.totalSaved")}</div>
          </div>

          {/* Rows */}
          <div className="space-y-2">
            {restList.map((user) => (
              <LeaderboardListItem
                key={user.rank}
                user={user}
                displayCurrency={displayCurrency}
                t={t}
              />
            ))}

            {/* Infinite scroll trigger - placed at end of list */}
            {onLoadMore && hasMore && (
              <div ref={loadMoreTriggerRef} className="py-8 flex justify-center">
                {isLoadingMore ? (
                  <div className="flex items-center gap-3 text-pandora-cyan">
                    <div className="w-5 h-5 border-2 border-pandora-cyan border-t-transparent rounded-full animate-spin" />
                    <span className="font-mono text-xs uppercase">{t("common.loadingMore")}</span>
                  </div>
                ) : (
                  <span className="text-[10px] font-mono text-gray-600">Scroll for more...</span>
                )}
              </div>
            )}
          </div>
        </div>

        {/* === USER HUD (STICKY DOCK) === */}
        {/* Docked perfectly above the 64px (h-16) mobile navbar */}
        {currentUser && (
          <div className="fixed bottom-16 md:bottom-0 left-0 md:left-20 right-0 z-40">
            <div className="max-w-7xl mx-auto">
              <div className="bg-[#050505]/95 backdrop-blur-xl border-t border-pandora-cyan/30 md:border-t-0 md:border-x shadow-[0_-10px_30px_rgba(0,0,0,0.5)] md:rounded-t-sm p-4 relative overflow-hidden flex items-center justify-between group">
                {/* Animated Scanline (Subtle) */}
                <div className="absolute top-0 left-0 w-full h-px bg-gradient-to-r from-transparent via-pandora-cyan/50 to-transparent" />
                <div className="absolute top-0 left-0 w-full h-full bg-[linear-gradient(90deg,transparent_0%,rgba(0,255,255,0.05)_50%,transparent_100%)] -translate-x-full group-hover:translate-x-full transition-transform duration-1000 pointer-events-none" />

                <div className="flex items-center gap-4 relative z-10">
                  <div className="bg-pandora-cyan text-black px-3 py-1 font-display font-bold text-lg rounded-sm shadow-[0_0_10px_rgba(0,255,255,0.4)]">
                    #{currentUser.rank}
                  </div>
                  <div>
                    <div className="text-[9px] font-mono text-gray-500 uppercase tracking-wider mb-0.5 flex items-center gap-2">
                      <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                      Current Session
                    </div>
                    <div className="text-sm font-bold text-white flex items-center gap-2">
                      {currentUser.name}{" "}
                      <span className="text-pandora-cyan font-mono text-xs opacity-80">
                        &lt;YOU&gt;
                      </span>
                    </div>
                  </div>
                </div>

                <div className="text-right relative z-10">
                  <div className="text-[9px] font-mono text-gray-500 uppercase tracking-wider mb-0.5">
                    Net Profit
                  </div>
                  <div className="text-xl font-display font-bold text-white flex items-center gap-2 justify-end">
                    {formatPrice(currentUser.saved, currentUser.currency || displayCurrency)}
                    <TrendingUp size={16} className="text-pandora-cyan" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
};

export default Leaderboard;
