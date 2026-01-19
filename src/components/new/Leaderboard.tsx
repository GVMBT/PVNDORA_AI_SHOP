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
    <div className="border border-white/5 bg-[#0e0e0e] p-6 opacity-30">
      <div className="absolute top-0 left-0 bg-white/5 px-2 py-1 font-bold font-mono text-[10px] text-gray-600">
        {RANK_LABELS[rank]}
      </div>
      <div className="mt-4 flex flex-col items-center text-center">
        <div className="mb-3 flex h-16 w-16 items-center justify-center rounded-full border border-white/10">
          <span className="text-2xl text-gray-600">?</span>
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
        <div className="absolute top-0 left-1/2 z-20 -translate-x-1/2 -translate-y-1/2 rounded-full bg-pandora-cyan p-2 text-black shadow-[0_0_20px_#00FFFF]">
          <Crown fill="currentColor" size={20} />
        </div>
      )}
      <div
        className={`absolute top-0 left-0 bg-white/10 px-2 py-1 font-bold font-mono text-[10px] ${isFirst ? "hidden" : "text-gray-300"}`}
      >
        {RANK_LABELS[rank]}
      </div>
      <div className="mt-4 flex flex-col items-center text-center">
        <div
          className={`${avatarSize} rounded-full ${borderClasses} p-1 ${isFirst ? "mb-4" : "mb-3"} flex items-center justify-center overflow-hidden bg-gray-900 ${isFirst ? "relative" : ""}`}
        >
          {isFirst && (
            <div className="absolute inset-0 animate-ping rounded-full border border-pandora-cyan opacity-20" />
          )}
          {isFirst && (
            <div className="absolute inset-0 bg-gradient-to-tr from-pandora-cyan/20 to-transparent" />
          )}
          {user.avatarUrl ? (
            <img
              alt={user.name}
              className={`h-full w-full rounded-full object-cover ${isFirst ? "relative z-10" : ""}`}
              onError={(e) => {
                (e.target as HTMLImageElement).style.display = "none";
              }}
              src={user.avatarUrl}
            />
          ) : null}
          {isFirst ? (
            <Crown
              className={`relative z-10 text-pandora-cyan/50 ${user.avatarUrl ? "hidden" : ""}`}
              size={32}
            />
          ) : (
            <User
              className={`absolute text-gray-500 ${user.avatarUrl ? "hidden" : ""}`}
              size={24}
            />
          )}
          {isFirst && (
            <div className="absolute -right-1 -bottom-1 z-20 flex h-6 w-6 items-center justify-center rounded-full bg-pandora-cyan font-bold text-black text-xs shadow-[0_0_10px_#00FFFF]">
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
        <div className="absolute inset-0 bg-gradient-to-b from-white/5 to-transparent opacity-0 transition-opacity group-hover:opacity-100" />
      )}
      {isFirst && <div className="absolute inset-0 -z-10 bg-pandora-cyan/20 blur-3xl" />}
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
    <div className="group relative border border-white/5 bg-[#0a0a0a] transition-all duration-300 hover:border-pandora-cyan/50">
      <div className="absolute top-0 bottom-0 left-0 w-0.5 bg-pandora-cyan opacity-0 transition-opacity group-hover:opacity-100" />
      <div className="grid grid-cols-12 items-center gap-4 p-4">
        <div className="col-span-2 text-center font-bold font-display text-gray-600 transition-colors group-hover:text-white md:col-span-1">
          {user.rank.toString().padStart(2, "0")}
        </div>
        <div className="col-span-10 flex items-center gap-4 md:col-span-5">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-sm border border-white/10 bg-white/5">
            {user.avatarUrl ? (
              <img
                alt={user.name}
                className="h-full w-full object-cover"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = "none";
                  (e.target as HTMLImageElement).nextElementSibling?.classList.remove("hidden");
                }}
                src={user.avatarUrl}
              />
            ) : null}
            <User
              className={`text-gray-500 group-hover:text-pandora-cyan ${user.avatarUrl ? "hidden" : ""}`}
              size={14}
            />
          </div>
          <div className="min-w-0">
            <div className="flex items-center gap-2 truncate font-bold text-sm text-white transition-colors group-hover:text-pandora-cyan">
              {user.name}
              {user.status === "ONLINE" && (
                <div className="h-1.5 w-1.5 shrink-0 animate-pulse rounded-full bg-green-500" />
              )}
            </div>
            <div className="truncate font-mono text-[10px] text-gray-600">{user.handle}</div>
          </div>
        </div>
        <div className="col-span-6 mt-2 text-center md:col-span-3 md:mt-0">
          <span className="mr-2 font-mono text-[10px] text-gray-500 uppercase md:hidden">
            {t("leaderboard.purchases")}:
          </span>
          <span className="font-mono text-gray-400">{user.modules}</span>
        </div>
        <div className="col-span-6 mt-2 flex items-center justify-end text-right md:col-span-3 md:mt-0 md:block">
          <span className="mr-2 font-mono text-[10px] text-gray-500 uppercase md:hidden">
            {t("leaderboard.totalSaved")}:
          </span>
          <div className="font-bold font-display text-lg text-white transition-colors group-hover:text-pandora-cyan">
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
  const { t, tEn } = useLocale();
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
    if (!(onLoadMore && loadMoreTriggerRef.current)) return;

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
        animate={{ opacity: 1 }}
        className="relative min-h-screen px-4 pt-20 pb-32 text-white md:px-8 md:pt-24 md:pl-28"
        exit={{ opacity: 0 }}
        initial={{ opacity: 0 }}
      >
        <div className="mx-auto max-w-7xl">
          <button
            className="mb-4 flex items-center gap-2 font-mono text-[10px] text-gray-500 transition-colors hover:text-pandora-cyan"
            onClick={onBack}
            type="button"
          >
            <ArrowLeft size={12} /> {t("empty.returnToBase").toUpperCase()}
          </button>
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <Trophy className="mb-6 text-gray-700" size={64} />
            <h2 className="mb-2 font-bold text-2xl text-white">
              {t("leaderboard.empty").toUpperCase()}
            </h2>
            <p className="max-w-md font-mono text-gray-500 text-sm">{t("leaderboard.emptyHint")}</p>
          </div>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      animate={{ opacity: 1 }}
      className="relative min-h-screen overflow-hidden px-4 pt-20 pb-48 text-white md:px-8 md:pt-24 md:pb-32 md:pl-28"
      exit={{ opacity: 0 }}
      initial={{ opacity: 0 }}
    >
      {/* Ambient Glows */}
      <div className="pointer-events-none fixed top-0 left-1/2 z-0 h-[300px] w-[500px] -translate-x-1/2 bg-pandora-cyan/10 blur-[120px]" />

      {/* EXPANDED CONTAINER: max-w-7xl to match Catalog/Footer */}
      <div className="relative z-10 mx-auto max-w-7xl">
        {/* === HEADER SECTION === */}
        <div className="mb-8 flex flex-col items-end justify-between gap-8 md:mb-16 md:flex-row">
          <div className="w-full md:w-auto">
            <button
              className="mb-4 flex items-center gap-2 font-mono text-[10px] text-gray-500 transition-colors hover:text-pandora-cyan"
              onClick={onBack}
              type="button"
            >
              <ArrowLeft size={12} /> {t("empty.returnToBase").toUpperCase()}
            </button>
            <h1 className="mb-4 font-black font-display text-3xl text-white uppercase leading-[0.9] tracking-tighter sm:text-4xl md:text-6xl">
              {tEn("leaderboard.pageTitlePrefix")} <br />{" "}
              <span className="bg-gradient-to-r from-pandora-cyan to-white/50 bg-clip-text text-transparent">
                {tEn("leaderboard.pageTitle")}
              </span>
            </h1>
            <div className="mb-4 font-mono text-gray-500 text-sm uppercase tracking-widest">
              {t("leaderboard.subtitle")}
            </div>
            <div className="flex flex-wrap items-center gap-4 font-mono text-pandora-cyan/70 text-xs">
              <span className="flex items-center gap-1 rounded-sm bg-pandora-cyan/10 px-2 py-1">
                <Activity size={12} /> {t("leaderboard.networkActivity").toUpperCase()}: HIGH
              </span>
              <span className="hidden sm:inline">|</span>
              <span className="hidden sm:inline">CYCLE_HASH: #A92-B</span>
            </div>
          </div>

          {/* Global Stats Card */}
          <div className="group relative w-full overflow-hidden rounded-sm border border-white/10 bg-[#0a0a0a] p-4 md:w-auto">
            <div className="absolute inset-0 translate-y-full bg-pandora-cyan/5 transition-transform duration-500 group-hover:translate-y-0" />
            <div className="relative z-10">
              <div className="mb-1 flex items-center gap-2 font-mono text-[9px] text-gray-500 uppercase tracking-widest">
                <ShieldCheck className="text-pandora-cyan" size={10} />{" "}
                {t("leaderboard.corporateLoss")}
              </div>
              <div className="break-all font-bold font-mono text-white text-xl tabular-nums tracking-tight sm:break-normal sm:text-2xl md:text-3xl">
                {formatPrice(totalSavedAggregate, displayCurrency)}
              </div>
            </div>
            {/* Decorative Corner */}
            <div className="absolute top-0 right-0 h-3 w-3 border-pandora-cyan border-t border-r opacity-50" />
          </div>
        </div>

        {/* === TOP 3 OPERATIVES (PODIUM) === */}
        <div className="relative mb-12 grid grid-cols-1 items-end gap-4 md:mb-20 md:grid-cols-3 md:gap-6">
          <PodiumRank
            displayCurrency={displayCurrency}
            isVacant={!hasRank2}
            rank={2}
            t={t}
            user={hasRank2 ? topThree[1] : null}
          />
          <PodiumRank
            displayCurrency={displayCurrency}
            isVacant={!hasRank1}
            rank={1}
            t={t}
            user={hasRank1 ? topThree[0] : null}
          />
          <PodiumRank
            displayCurrency={displayCurrency}
            isVacant={!hasRank3}
            rank={3}
            t={t}
            user={hasRank3 ? topThree[2] : null}
          />
        </div>

        {/* === MAIN LIST === */}
        <div className="mb-32 space-y-4 md:mb-24">
          <div className="mb-4 flex items-center justify-between">
            <h3 className="flex items-center gap-2 font-bold text-sm text-white md:text-lg">
              <Terminal className="text-pandora-cyan" size={16} />
              ACTIVE_AGENTS_LIST
            </h3>
            <div className="flex rounded-sm border border-white/10 bg-[#0a0a0a] p-0.5">
              <button
                className={`px-3 py-1.5 font-bold font-mono text-[9px] uppercase transition-colors ${filter === "weekly" ? "bg-white/10 text-white" : "text-gray-600 hover:text-gray-400"}`}
                onClick={() => handleFilterChange("weekly")}
                type="button"
              >
                {t("leaderboard.weekly")}
              </button>
              <button
                className={`px-3 py-1.5 font-bold font-mono text-[9px] uppercase transition-colors ${filter === "all_time" ? "bg-white/10 text-white" : "text-gray-600 hover:text-gray-400"}`}
                onClick={() => handleFilterChange("all_time")}
                type="button"
              >
                {t("leaderboard.allTime")}
              </button>
            </div>
          </div>

          {/* List Header */}
          <div className="hidden grid-cols-12 gap-4 px-6 py-2 font-mono text-[10px] text-gray-500 uppercase tracking-wider md:grid">
            <div className="col-span-1 text-center">#</div>
            <div className="col-span-5">{t("leaderboard.participant")}</div>
            <div className="col-span-3 text-center">{t("leaderboard.purchases")}</div>
            <div className="col-span-3 text-right">{t("leaderboard.totalSaved")}</div>
          </div>

          {/* Rows */}
          <div className="space-y-2">
            {restList.map((user) => (
              <LeaderboardListItem
                displayCurrency={displayCurrency}
                key={user.rank}
                t={t}
                user={user}
              />
            ))}

            {/* Infinite scroll trigger - placed at end of list */}
            {onLoadMore && hasMore && (
              <div className="flex justify-center py-8" ref={loadMoreTriggerRef}>
                {isLoadingMore ? (
                  <div className="flex items-center gap-3 text-pandora-cyan">
                    <div className="h-5 w-5 animate-spin rounded-full border-2 border-pandora-cyan border-t-transparent" />
                    <span className="font-mono text-xs uppercase">{t("common.loadingMore")}</span>
                  </div>
                ) : (
                  <span className="font-mono text-[10px] text-gray-600">Scroll for more...</span>
                )}
              </div>
            )}
          </div>
        </div>

        {/* === USER HUD (STICKY DOCK) === */}
        {/* Docked perfectly above the 64px (h-16) mobile navbar */}
        {currentUser && (
          <div className="fixed right-0 bottom-16 left-0 z-40 md:bottom-0 md:left-20">
            <div className="mx-auto max-w-7xl">
              <div className="group relative flex items-center justify-between overflow-hidden border-pandora-cyan/30 border-t bg-[#050505]/95 p-4 shadow-[0_-10px_30px_rgba(0,0,0,0.5)] backdrop-blur-xl md:rounded-t-sm md:border-x md:border-t-0">
                {/* Animated Scanline (Subtle) */}
                <div className="absolute top-0 left-0 h-px w-full bg-gradient-to-r from-transparent via-pandora-cyan/50 to-transparent" />
                <div className="pointer-events-none absolute top-0 left-0 h-full w-full -translate-x-full bg-[linear-gradient(90deg,transparent_0%,rgba(0,255,255,0.05)_50%,transparent_100%)] transition-transform duration-1000 group-hover:translate-x-full" />

                <div className="relative z-10 flex items-center gap-4">
                  <div className="rounded-sm bg-pandora-cyan px-3 py-1 font-bold font-display text-black text-lg shadow-[0_0_10px_rgba(0,255,255,0.4)]">
                    #{currentUser.rank}
                  </div>
                  <div>
                    <div className="mb-0.5 flex items-center gap-2 font-mono text-[9px] text-gray-500 uppercase tracking-wider">
                      <div className="h-1.5 w-1.5 animate-pulse rounded-full bg-green-500" />
                      Current Session
                    </div>
                    <div className="flex items-center gap-2 font-bold text-sm text-white">
                      {currentUser.name}{" "}
                      <span className="font-mono text-pandora-cyan text-xs opacity-80">
                        &lt;YOU&gt;
                      </span>
                    </div>
                  </div>
                </div>

                <div className="relative z-10 text-right">
                  <div className="mb-0.5 font-mono text-[9px] text-gray-500 uppercase tracking-wider">
                    Net Profit
                  </div>
                  <div className="flex items-center justify-end gap-2 font-bold font-display text-white text-xl">
                    {formatPrice(currentUser.saved, currentUser.currency || displayCurrency)}
                    <TrendingUp className="text-pandora-cyan" size={16} />
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
