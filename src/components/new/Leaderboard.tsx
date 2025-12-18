
import React, { useState, useRef } from 'react';
import { motion } from 'framer-motion';
import { Trophy, ChevronUp, ChevronDown, User, Crown, ArrowRight, TrendingUp, ShieldCheck, Activity, Zap, Terminal, BarChart3, Lock, ArrowLeft } from 'lucide-react';
import { formatPrice, getCurrencySymbol } from '../../utils/currency';
import { useLocale } from '../../hooks/useLocale';

// Type matching LeaderboardUser from types/component
interface LeaderboardUserData {
  rank: number;
  name: string;
  handle: string;
  marketSpend: number;
  actualSpend: number;
  saved: number;
  modules: number;
  trend: 'up' | 'down' | 'same';
  status: 'ONLINE' | 'AWAY' | 'BUSY' | 'OFFLINE';
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
  onFilterChange?: (filter: 'weekly' | 'all_time') => void;
  activeFilter?: 'weekly' | 'all_time';
}

// MOCK DATA removed - use real API data only

const Leaderboard: React.FC<LeaderboardProps> = ({ 
  leaderboardData: propData, 
  currency = 'USD',
  onBack, 
  onLoadMore,
  hasMore = false,
  isLoadingMore = false,
  onFilterChange,
  activeFilter = 'all_time',
}) => {
  const { t } = useLocale();
  // Use controlled filter from parent or internal state
  const [internalFilter, setInternalFilter] = useState<'weekly' | 'all_time'>('all_time');
  const filter = onFilterChange ? activeFilter : internalFilter;
  
  const handleFilterChange = (newFilter: 'weekly' | 'all_time') => {
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
  
  // Determine currency: use from first user if available, or from props, or default to USD
  const displayCurrency = data.find(u => u.currency)?.currency || currency || 'USD';
  
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
  }, [onLoadMore, restList.length]); // Re-attach when list changes
  
  // Find current user for the sticky footer
  const currentUser = data.find(u => u.isMe);
  
  // Check if we have enough data for podium
  const hasRank1 = topThree.length >= 1;
  const hasRank2 = topThree.length >= 2;
  const hasRank3 = topThree.length >= 3;

  // Calculate efficiency percentage
  const calculateEfficiency = (market: number, saved: number) => {
      if (!market || market <= 0) return 0;
      return Math.round((saved / market) * 100);
  };

  // Aggregate totals for header stats (replace hardcoded mock)
  const totalSavedAggregate = data.reduce((acc, u) => acc + (u.saved || 0), 0);
  const totalMarketAggregate = data.reduce((acc, u) => acc + (u.marketSpend || 0), 0);
  const totalEfficiency = calculateEfficiency(totalMarketAggregate, totalSavedAggregate);

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
          <button onClick={onBack} className="flex items-center gap-2 text-[10px] font-mono text-gray-500 hover:text-pandora-cyan mb-4 transition-colors">
            <ArrowLeft size={12} /> {t('empty.returnToBase').toUpperCase()}
          </button>
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <Trophy size={64} className="text-gray-700 mb-6" />
            <h2 className="text-2xl font-bold text-white mb-2">{t('leaderboard.empty').toUpperCase()}</h2>
            <p className="text-gray-500 font-mono text-sm max-w-md">
              {t('leaderboard.emptyHint')}
            </p>
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
                    <button onClick={onBack} className="flex items-center gap-2 text-[10px] font-mono text-gray-500 hover:text-pandora-cyan mb-4 transition-colors">
                        <ArrowLeft size={12} /> {t('empty.returnToBase').toUpperCase()}
                    </button>
                    <h1 className="text-3xl sm:text-4xl md:text-6xl font-display font-black text-white uppercase tracking-tighter leading-[0.9] mb-4">
                        {t('leaderboard.titlePrefix')} <br/> <span className="text-transparent bg-clip-text bg-gradient-to-r from-pandora-cyan to-white/50">{t('leaderboard.title')}</span>
                    </h1>
                    <div className="text-sm font-mono text-gray-500 uppercase tracking-widest mb-4">{t('leaderboard.subtitle')}</div>
                    <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-pandora-cyan/70">
                        <span className="flex items-center gap-1 bg-pandora-cyan/10 px-2 py-1 rounded-sm"><Activity size={12} /> {t('leaderboard.networkActivity').toUpperCase()}: HIGH</span>
                        <span className="hidden sm:inline">|</span>
                        <span className="hidden sm:inline">CYCLE_HASH: #A92-B</span>
                    </div>
                </div>

                {/* Global Stats Card */}
                <div className="w-full md:w-auto bg-[#0a0a0a] border border-white/10 p-4 rounded-sm relative overflow-hidden group">
                    <div className="absolute inset-0 bg-pandora-cyan/5 translate-y-full group-hover:translate-y-0 transition-transform duration-500" />
                    <div className="relative z-10">
                        <div className="text-[9px] font-mono text-gray-500 uppercase tracking-widest mb-1 flex items-center gap-2">
                            <ShieldCheck size={10} className="text-pandora-cyan" /> {t('leaderboard.corporateLoss')}
                        </div>
                        <div className="text-xl sm:text-2xl md:text-3xl font-mono font-bold text-white tracking-tight tabular-nums break-all sm:break-normal">
                            {formatPrice(totalSavedAggregate, displayCurrency)}<span className="text-gray-600">{totalEfficiency ? ` // ${totalEfficiency}%` : ''}</span>
                        </div>
                    </div>
                    {/* Decorative Corner */}
                    <div className="absolute top-0 right-0 w-3 h-3 border-t border-r border-pandora-cyan opacity-50" />
                </div>
            </div>

            {/* === TOP 3 OPERATIVES (PODIUM) === */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6 items-end mb-12 md:mb-20 relative">
                
                {/* Rank 2 */}
                {hasRank2 ? (
                <div className="order-2 md:order-1 relative group">
                    <div className="absolute inset-0 bg-gradient-to-b from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                    <div className="bg-[#0e0e0e] border border-white/10 p-6 relative overflow-hidden hover:border-pandora-cyan/30 transition-colors">
                        <div className="absolute top-0 left-0 bg-white/10 px-2 py-1 text-[10px] font-bold font-mono text-gray-300">RANK_02</div>
                        <div className="flex flex-col items-center text-center mt-4">
                            <div className="w-16 h-16 rounded-full border border-white/20 p-1 mb-3 overflow-hidden bg-gray-900 flex items-center justify-center">
                                {topThree[1].avatarUrl ? (
                                    <img 
                                        src={topThree[1].avatarUrl} 
                                        alt={topThree[1].name} 
                                        className="w-full h-full object-cover rounded-full"
                                        onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                                    />
                                ) : null}
                                <User size={24} className={`text-gray-500 absolute ${topThree[1].avatarUrl ? 'hidden' : ''}`} />
                            </div>
                            <h3 className="font-bold text-white text-lg">{topThree[1].name}</h3>
                            <div className="text-xs font-mono text-pandora-cyan mb-4">{topThree[1].handle}</div>
                            
                            <div className="w-full bg-white/5 p-2 rounded-sm border border-white/5">
                                <div className="text-[9px] text-gray-500 uppercase">{t('leaderboard.totalSaved')}</div>
                                <div className="text-lg font-bold text-white">{formatPrice(topThree[1].saved, topThree[1].currency || displayCurrency)}</div>
                            </div>
                        </div>
                    </div>
                </div>
                ) : (
                <div className="order-2 md:order-1 relative">
                    <div className="bg-[#0e0e0e] border border-white/5 p-6 opacity-30">
                        <div className="absolute top-0 left-0 bg-white/5 px-2 py-1 text-[10px] font-bold font-mono text-gray-600">RANK_02</div>
                        <div className="flex flex-col items-center text-center mt-4">
                            <div className="w-16 h-16 rounded-full border border-white/10 mb-3 flex items-center justify-center">
                                <span className="text-gray-600 text-2xl">?</span>
                            </div>
                            <h3 className="font-bold text-gray-600 text-lg">{t('leaderboard.vacant').toUpperCase()}</h3>
                        </div>
                    </div>
                </div>
                )}

                {/* Rank 1 (Center) */}
                {hasRank1 && (
                <div className="order-1 md:order-2 relative z-10 mt-0 md:-mt-12 mb-4 md:mb-0">
                     {/* Glow Effect */}
                    <div className="absolute inset-0 bg-pandora-cyan/20 blur-3xl -z-10" />
                    
                    <div className="bg-[#050505] border border-pandora-cyan p-1 relative rounded-sm">
                        <div className="bg-[#0a0a0a] p-4 sm:p-8 relative">
                             {/* Crown Icon */}
                             <div className="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-pandora-cyan text-black p-2 rounded-full shadow-[0_0_20px_#00FFFF] z-20">
                                <Crown size={20} fill="currentColor" />
                             </div>
                             
                             <div className="flex flex-col items-center text-center mt-4">
                                <div className="w-24 h-24 rounded-full border-2 border-pandora-cyan p-1 mb-4 relative">
                                    <div className="absolute inset-0 rounded-full border border-pandora-cyan animate-ping opacity-20" />
                                    <div className="w-full h-full bg-gray-900 rounded-full flex items-center justify-center overflow-hidden relative">
                                        <div className="absolute inset-0 bg-gradient-to-tr from-pandora-cyan/20 to-transparent" />
                                        {topThree[0].avatarUrl ? (
                                            <img 
                                                src={topThree[0].avatarUrl} 
                                                alt={topThree[0].name} 
                                                className="w-full h-full object-cover rounded-full relative z-10"
                                                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                                            />
                                        ) : null}
                                        <Crown size={32} className={`text-pandora-cyan/50 relative z-10 ${topThree[0].avatarUrl ? 'hidden' : ''}`} />
                                    </div>
                                    <div className="absolute -bottom-1 -right-1 w-6 h-6 bg-pandora-cyan rounded-full flex items-center justify-center text-black font-bold text-xs shadow-[0_0_10px_#00FFFF] z-20">1</div>
                                </div>

                                <h3 className="font-display font-bold text-xl sm:text-2xl text-white tracking-wide">{topThree[0].name}</h3>
                                <div className="text-sm font-mono text-pandora-cyan mb-6">{topThree[0].handle}</div>

                                <div className="w-full grid grid-cols-2 gap-2">
                                    <div className="bg-pandora-cyan/10 border border-pandora-cyan/30 p-2 rounded-sm overflow-hidden">
                                        <div className="text-[9px] text-pandora-cyan uppercase font-bold truncate">Saved</div>
                                        <div className="text-base sm:text-xl font-bold text-white whitespace-normal break-all sm:break-normal leading-tight">{formatPrice(topThree[0].saved, topThree[0].currency || displayCurrency)}</div>
                                    </div>
                                    <div className="bg-white/5 border border-white/10 p-2 rounded-sm overflow-hidden">
                                        <div className="text-[9px] text-gray-500 uppercase font-bold truncate">Efficiency</div>
                                        <div className="text-base sm:text-xl font-bold text-white">{calculateEfficiency(topThree[0].marketSpend, topThree[0].saved)}%</div>
                                    </div>
                                </div>
                             </div>
                        </div>
                    </div>
                </div>
                )}

                {/* Rank 3 */}
                {hasRank3 ? (
                <div className="order-3 md:order-3 relative group">
                    <div className="absolute inset-0 bg-gradient-to-b from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                    <div className="bg-[#0e0e0e] border border-white/10 p-6 relative overflow-hidden hover:border-pandora-cyan/30 transition-colors">
                        <div className="absolute top-0 left-0 bg-white/10 px-2 py-1 text-[10px] font-bold font-mono text-gray-300">RANK_03</div>
                        <div className="flex flex-col items-center text-center mt-4">
                            <div className="w-16 h-16 rounded-full border border-white/20 p-1 mb-3 overflow-hidden bg-gray-900 flex items-center justify-center">
                                {topThree[2].avatarUrl ? (
                                    <img 
                                        src={topThree[2].avatarUrl} 
                                        alt={topThree[2].name} 
                                        className="w-full h-full object-cover rounded-full"
                                        onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                                    />
                                ) : null}
                                <User size={24} className={`text-gray-500 absolute ${topThree[2].avatarUrl ? 'hidden' : ''}`} />
                            </div>
                            <h3 className="font-bold text-white text-lg">{topThree[2].name}</h3>
                            <div className="text-xs font-mono text-pandora-cyan mb-4">{topThree[2].handle}</div>
                            
                            <div className="w-full bg-white/5 p-2 rounded-sm border border-white/5">
                                <div className="text-[9px] text-gray-500 uppercase">{t('leaderboard.totalSaved')}</div>
                                <div className="text-lg font-bold text-white">{formatPrice(topThree[2].saved, topThree[2].currency || displayCurrency)}</div>
                            </div>
                        </div>
                    </div>
                </div>
                ) : (
                <div className="order-3 md:order-3 relative">
                    <div className="bg-[#0e0e0e] border border-white/5 p-6 opacity-30">
                        <div className="absolute top-0 left-0 bg-white/5 px-2 py-1 text-[10px] font-bold font-mono text-gray-600">RANK_03</div>
                        <div className="flex flex-col items-center text-center mt-4">
                            <div className="w-16 h-16 rounded-full border border-white/10 mb-3 flex items-center justify-center">
                                <span className="text-gray-600 text-2xl">?</span>
                            </div>
                            <h3 className="font-bold text-gray-600 text-lg">{t('leaderboard.vacant').toUpperCase()}</h3>
                        </div>
                    </div>
                </div>
                )}
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
                            onClick={() => handleFilterChange('weekly')}
                            className={`px-3 py-1.5 text-[9px] font-mono font-bold uppercase transition-colors ${filter === 'weekly' ? 'bg-white/10 text-white' : 'text-gray-600 hover:text-gray-400'}`}
                        >
                            Weekly
                        </button>
                        <button 
                            onClick={() => handleFilterChange('all_time')}
                            className={`px-3 py-1.5 text-[9px] font-mono font-bold uppercase transition-colors ${filter === 'all_time' ? 'bg-white/10 text-white' : 'text-gray-600 hover:text-gray-400'}`}
                        >
                            All Time
                        </button>
                    </div>
                </div>

                {/* List Header */}
                <div className="hidden md:grid grid-cols-12 gap-4 px-6 py-2 text-[10px] font-mono text-gray-500 uppercase tracking-wider">
                    <div className="col-span-1 text-center">#</div>
                    <div className="col-span-4">Operative</div>
                    <div className="col-span-5">Savings Efficiency (Market vs Actual)</div>
                    <div className="col-span-2 text-right">Net Profit</div>
                </div>

                {/* Rows (Native) */}
                <div className="space-y-2">
                    {restList.map((user) => {
                        const efficiency = calculateEfficiency(user.marketSpend, user.saved);
                        return (
                            <div key={user.rank} className="group relative bg-[#0a0a0a] border border-white/5 hover:border-pandora-cyan/50 transition-all duration-300">
                                <div className="absolute left-0 top-0 bottom-0 w-0.5 bg-pandora-cyan opacity-0 group-hover:opacity-100 transition-opacity" />
                                
                                <div className="grid grid-cols-12 gap-4 items-center p-4">
                                    {/* Rank */}
                                    <div className="col-span-2 md:col-span-1 text-center font-display font-bold text-gray-600 group-hover:text-white transition-colors">
                                        {user.rank.toString().padStart(2, '0')}
                                    </div>

                                    {/* Identity */}
                                    <div className="col-span-10 md:col-span-4 flex items-center gap-4">
                                        <div className="w-8 h-8 bg-white/5 rounded-sm flex items-center justify-center border border-white/10 shrink-0 overflow-hidden">
                                            {user.avatarUrl ? (
                                                <img 
                                                    src={user.avatarUrl} 
                                                    alt={user.name} 
                                                    className="w-full h-full object-cover"
                                                    onError={(e) => {
                                                        (e.target as HTMLImageElement).style.display = 'none';
                                                        (e.target as HTMLImageElement).nextElementSibling?.classList.remove('hidden');
                                                    }}
                                                />
                                            ) : null}
                                            <User size={14} className={`text-gray-500 group-hover:text-pandora-cyan ${user.avatarUrl ? 'hidden' : ''}`} />
                                        </div>
                                        <div className="min-w-0">
                                            <div className="text-sm font-bold text-white group-hover:text-pandora-cyan transition-colors flex items-center gap-2 truncate">
                                                {user.name}
                                                {user.status === 'ONLINE' && <div className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse shrink-0" />}
                                            </div>
                                            <div className="text-[10px] font-mono text-gray-600 truncate">{user.modules} modules installed</div>
                                        </div>
                                    </div>

                                    {/* Visual Bar (Savings Visualization) */}
                                    <div className="col-span-12 md:col-span-5 mt-2 md:mt-0">
                                        <div className="flex justify-between text-[9px] font-mono text-gray-500 mb-1">
                                            <span>MARKET: <span className="line-through decoration-red-500/50">{user.marketSpend.toLocaleString()}</span></span>
                                            <span className="text-pandora-cyan">SAVED: {efficiency}%</span>
                                        </div>
                                        <div className="h-2 w-full bg-white/5 rounded-sm overflow-hidden flex relative">
                                            <div className="absolute inset-0 bg-white/5" />
                                            <div 
                                                className="h-full bg-gray-600" 
                                                style={{ width: `${100 - efficiency}%` }} 
                                            />
                                            <div 
                                                className="h-full bg-pandora-cyan shadow-[0_0_10px_#00FFFF]" 
                                                style={{ width: `${efficiency}%` }} 
                                            />
                                        </div>
                                    </div>

                                    {/* Net Savings */}
                                    <div className="col-span-12 md:col-span-2 text-right mt-2 md:mt-0 flex justify-between md:block items-center">
                                        <span className="md:hidden text-[10px] text-gray-500 font-mono uppercase">Net Profit:</span>
                                        <div className="font-display font-bold text-white text-lg group-hover:text-pandora-cyan transition-colors">
                                            {formatPrice(user.saved, user.currency || displayCurrency)}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                    
                    {/* Infinite scroll trigger - placed at end of list */}
                    {onLoadMore && hasMore && (
                        <div 
                            ref={loadMoreTriggerRef} 
                            className="py-8 flex justify-center"
                        >
                            {isLoadingMore ? (
                                <div className="flex items-center gap-3 text-pandora-cyan">
                                    <div className="w-5 h-5 border-2 border-pandora-cyan border-t-transparent rounded-full animate-spin" />
                                    <span className="font-mono text-xs uppercase">Loading more agents...</span>
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
                                        {currentUser.name} <span className="text-pandora-cyan font-mono text-xs opacity-80">&lt;YOU&gt;</span>
                                    </div>
                                </div>
                            </div>

                            <div className="text-right relative z-10">
                                <div className="text-[9px] font-mono text-gray-500 uppercase tracking-wider mb-0.5">Net Profit</div>
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
