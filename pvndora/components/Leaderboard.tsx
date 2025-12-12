
import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Trophy, ChevronUp, ChevronDown, User, Crown, ArrowRight, TrendingUp, ShieldCheck, Activity, Zap, Terminal, BarChart3, Lock, ArrowLeft } from 'lucide-react';

interface LeaderboardProps {
  onBack: () => void;
}

// Data structure: Official Price (Market), Actual Spend (Pandora), Saved = Diff
const LEADERBOARD_DATA = [
  { rank: 1, name: "Neo_Anderson", handle: "@the_one", marketSpend: 550000, actualSpend: 154200, saved: 395800, modules: 42, trend: 'up', status: 'ONLINE' },
  { rank: 2, name: "Trinity_X", handle: "@trin_hack", marketSpend: 320000, actualSpend: 98500, saved: 221500, modules: 28, trend: 'up', status: 'AWAY' },
  { rank: 3, name: "Morpheus_D", handle: "@nebuchadnezzar", marketSpend: 280000, actualSpend: 87200, saved: 192800, modules: 25, trend: 'down', status: 'ONLINE' },
  { rank: 4, name: "Cypher_L", handle: "@steak_lover", marketSpend: 150000, actualSpend: 54000, saved: 96000, modules: 14, trend: 'up', status: 'OFFLINE' },
  { rank: 5, name: "Tank_Oper", handle: "@operator_1", marketSpend: 110000, actualSpend: 42100, saved: 67900, modules: 12, trend: 'same', status: 'ONLINE' },
  { rank: 6, name: "Dozer_Mech", handle: "@core_drill", marketSpend: 95000, actualSpend: 38900, saved: 56100, modules: 10, trend: 'down', status: 'BUSY' },
  { rank: 7, name: "Switch_W", handle: "@white_rabbit", marketSpend: 75000, actualSpend: 31000, saved: 44000, modules: 8, trend: 'up', status: 'ONLINE' },
  { rank: 8, name: "Apoc_Dev", handle: "@bug_fixer", marketSpend: 68000, actualSpend: 28500, saved: 39500, modules: 6, trend: 'same', status: 'ONLINE' },
  { rank: 9, name: "Mouse_Kid", handle: "@digital_pimp", marketSpend: 40000, actualSpend: 15000, saved: 25000, modules: 4, trend: 'up', status: 'AWAY' },
  { rank: 158, name: "Nikita", handle: "@gvmbt158", marketSpend: 5000, actualSpend: 1250, saved: 3750, modules: 1, trend: 'same', status: 'ONLINE', isMe: true }, // Current User
];

const Leaderboard: React.FC<LeaderboardProps> = ({ onBack }) => {
  const [filter, setFilter] = useState<'weekly' | 'all_time'>('weekly');

  const topThree = LEADERBOARD_DATA.slice(0, 3);
  const restList = LEADERBOARD_DATA.slice(3, 9);
  const currentUser = LEADERBOARD_DATA.find(u => u.isMe);

  // Calculate efficiency percentage
  const calculateEfficiency = (market: number, saved: number) => {
      return Math.round((saved / market) * 100);
  };

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen text-white pt-24 pb-48 md:pb-32 px-4 md:px-8 md:pl-28 relative overflow-hidden"
    >
        {/* Ambient Glows */}
        <div className="fixed top-0 left-1/2 -translate-x-1/2 w-[500px] h-[300px] bg-pandora-cyan/10 blur-[120px] pointer-events-none z-0" />

        {/* EXPANDED CONTAINER: max-w-7xl to match Catalog/Footer */}
        <div className="max-w-7xl mx-auto relative z-10">
            
            {/* === HEADER SECTION === */}
            <div className="flex flex-col md:flex-row justify-between items-end gap-8 mb-8 md:mb-16">
                <div className="w-full md:w-auto">
                    <button onClick={onBack} className="flex items-center gap-2 text-[10px] font-mono text-gray-500 hover:text-pandora-cyan mb-4 transition-colors">
                        <ArrowLeft size={12} /> RETURN_TO_BASE
                    </button>
                    <h1 className="text-3xl sm:text-4xl md:text-6xl font-display font-black text-white uppercase tracking-tighter leading-[0.9] mb-4">
                        PROTOCOL: <br/> <span className="text-transparent bg-clip-text bg-gradient-to-r from-pandora-cyan to-white/50">SYSTEM_BYPASS</span>
                    </h1>
                    <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-pandora-cyan/70">
                        <span className="flex items-center gap-1 bg-pandora-cyan/10 px-2 py-1 rounded-sm"><Activity size={12} /> NETWORK_ACTIVITY: HIGH</span>
                        <span className="hidden sm:inline">|</span>
                        <span className="hidden sm:inline">CYCLE_HASH: #A92-B</span>
                    </div>
                </div>

                {/* Global Stats Card */}
                <div className="w-full md:w-auto bg-[#0a0a0a] border border-white/10 p-4 rounded-sm relative overflow-hidden group">
                    <div className="absolute inset-0 bg-pandora-cyan/5 translate-y-full group-hover:translate-y-0 transition-transform duration-500" />
                    <div className="relative z-10">
                        <div className="text-[9px] font-mono text-gray-500 uppercase tracking-widest mb-1 flex items-center gap-2">
                            <ShieldCheck size={10} className="text-pandora-cyan" /> Total Corporate Loss
                        </div>
                        <div className="text-xl sm:text-2xl md:text-3xl font-mono font-bold text-white tracking-tight tabular-nums break-all sm:break-normal">
                            ₽ 14,892,420<span className="text-gray-600">.00</span>
                        </div>
                    </div>
                    {/* Decorative Corner */}
                    <div className="absolute top-0 right-0 w-3 h-3 border-t border-r border-pandora-cyan opacity-50" />
                </div>
            </div>

            {/* === TOP 3 OPERATIVES (PODIUM) === */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 md:gap-6 items-end mb-12 md:mb-20 relative">
                
                {/* Rank 2 */}
                <div className="order-2 md:order-1 relative group">
                    <div className="absolute inset-0 bg-gradient-to-b from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                    <div className="bg-[#0e0e0e] border border-white/10 p-6 relative overflow-hidden hover:border-pandora-cyan/30 transition-colors">
                        <div className="absolute top-0 left-0 bg-white/10 px-2 py-1 text-[10px] font-bold font-mono text-gray-300">RANK_02</div>
                        <div className="flex flex-col items-center text-center mt-4">
                            <div className="w-16 h-16 rounded-full border border-white/20 p-1 mb-3">
                                <div className="w-full h-full bg-gray-800 rounded-full flex items-center justify-center">
                                    <span className="font-display font-bold text-xl text-gray-500">{topThree[1].name[0]}</span>
                                </div>
                            </div>
                            <h3 className="font-bold text-white text-lg">{topThree[1].name}</h3>
                            <div className="text-xs font-mono text-pandora-cyan mb-4">{topThree[1].handle}</div>
                            
                            <div className="w-full bg-white/5 p-2 rounded-sm border border-white/5">
                                <div className="text-[9px] text-gray-500 uppercase">Total Saved</div>
                                <div className="text-lg font-bold text-white">₽ {(topThree[1].saved / 1000).toFixed(1)}k</div>
                            </div>
                        </div>
                    </div>
                </div>

                {/* Rank 1 (Center) */}
                <div className="order-1 md:order-2 relative z-10 mt-0 md:-mt-12 mb-4 md:mb-0">
                     {/* Glow Effect */}
                    <div className="absolute inset-0 bg-pandora-cyan/20 blur-3xl -z-10" />
                    
                    {/* Removed overflow-hidden to allow Crown to float on top */}
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
                                        <span className="font-display font-bold text-3xl text-white relative z-10">{topThree[0].name[0]}</span>
                                    </div>
                                    <div className="absolute bottom-0 right-0 w-6 h-6 bg-pandora-cyan rounded-full flex items-center justify-center text-black font-bold text-xs shadow-[0_0_10px_#00FFFF]">1</div>
                                </div>

                                <h3 className="font-display font-bold text-xl sm:text-2xl text-white tracking-wide">{topThree[0].name}</h3>
                                <div className="text-sm font-mono text-pandora-cyan mb-6">{topThree[0].handle}</div>

                                <div className="w-full grid grid-cols-2 gap-2">
                                    <div className="bg-pandora-cyan/10 border border-pandora-cyan/30 p-2 rounded-sm overflow-hidden">
                                        <div className="text-[9px] text-pandora-cyan uppercase font-bold truncate">Saved</div>
                                        <div className="text-base sm:text-xl font-bold text-white whitespace-normal break-all sm:break-normal leading-tight">₽ {(topThree[0].saved / 1000).toFixed(0)}k</div>
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

                {/* Rank 3 */}
                <div className="order-3 md:order-3 relative group">
                    <div className="absolute inset-0 bg-gradient-to-b from-white/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                    <div className="bg-[#0e0e0e] border border-white/10 p-6 relative overflow-hidden hover:border-pandora-cyan/30 transition-colors">
                        <div className="absolute top-0 left-0 bg-white/10 px-2 py-1 text-[10px] font-bold font-mono text-gray-300">RANK_03</div>
                        <div className="flex flex-col items-center text-center mt-4">
                            <div className="w-16 h-16 rounded-full border border-white/20 p-1 mb-3">
                                <div className="w-full h-full bg-gray-800 rounded-full flex items-center justify-center">
                                    <span className="font-display font-bold text-xl text-gray-500">{topThree[2].name[0]}</span>
                                </div>
                            </div>
                            <h3 className="font-bold text-white text-lg">{topThree[2].name}</h3>
                            <div className="text-xs font-mono text-pandora-cyan mb-4">{topThree[2].handle}</div>
                            
                            <div className="w-full bg-white/5 p-2 rounded-sm border border-white/5">
                                <div className="text-[9px] text-gray-500 uppercase">Total Saved</div>
                                <div className="text-lg font-bold text-white">₽ {(topThree[2].saved / 1000).toFixed(1)}k</div>
                            </div>
                        </div>
                    </div>
                </div>
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
                            onClick={() => setFilter('weekly')}
                            className={`px-3 py-1.5 text-[9px] font-mono font-bold uppercase transition-colors ${filter === 'weekly' ? 'bg-white/10 text-white' : 'text-gray-600 hover:text-gray-400'}`}
                        >
                            Weekly
                        </button>
                        <button 
                            onClick={() => setFilter('all_time')}
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

                {/* Rows */}
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
                                    <div className="w-8 h-8 bg-white/5 rounded-sm flex items-center justify-center border border-white/10 shrink-0">
                                        <User size={14} className="text-gray-500 group-hover:text-pandora-cyan" />
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
                                        {/* Market Spend Visual (Background) */}
                                        <div className="absolute inset-0 bg-white/5" />
                                        
                                        {/* Pandora Spend Visual (What they actually paid) */}
                                        <div 
                                            className="h-full bg-gray-600" 
                                            style={{ width: `${100 - efficiency}%` }} 
                                        />
                                        
                                        {/* Savings Visual (The Difference) */}
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
                                        {user.saved.toLocaleString()} <span className="text-sm text-gray-600">₽</span>
                                    </div>
                                </div>
                             </div>
                        </div>
                    );
                })}
            </div>

            {/* === USER HUD (STICKY DOCK) === */}
            {/* Docked perfectly above the 64px (h-16) mobile navbar */}
            {currentUser && (
                <div className="fixed bottom-16 md:bottom-0 left-0 md:left-20 right-0 z-40">
                    <div className="max-w-7xl mx-auto">
                        <div className="bg-[#050505]/95 backdrop-blur-xl border-t border-pandora-cyan/30 md:border-t-0 md:border-x md:border-t border-pandora-cyan/30 shadow-[0_-10px_30px_rgba(0,0,0,0.5)] md:rounded-t-sm p-4 relative overflow-hidden flex items-center justify-between group">
                            
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
                                    {currentUser.saved.toLocaleString()} ₽
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
