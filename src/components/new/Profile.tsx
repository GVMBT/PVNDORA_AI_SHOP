
import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  User, Copy, Share2, Terminal, Wallet, Shield, 
  Check, Lock, Settings, Globe, Banknote, X, 
  Cpu, Network, Signal, Zap, ChevronRight, Activity, ArrowUpRight, ArrowDownLeft,
  Plus, Crown, GitBranch, ChevronDown, ChevronUp, BarChart3, MousePointer2, Percent, Target, Wifi, Radio,
  FileCode, Hash, RefreshCw, ShieldCheck, Layers, LayoutDashboard, ToggleRight, ToggleLeft, QrCode, ArrowLeft
} from 'lucide-react';

// Types matching types/component.ts ProfileData
interface CareerLevelData {
  id: number;
  label: string;
  min: number;
  max: number;
  color: string;
}

interface NetworkNodeData {
  id: string | number;
  name?: string;
  handle: string;
  status: 'active' | 'inactive' | string;
  earned: number;
  ordersCount: number;
  photoUrl?: string;
}

interface BillingLogData {
  id: string;
  type: 'INCOME' | 'OUTCOME' | 'SYSTEM';
  source: string;
  amount: string;
  date: string;
}

interface ProfileStatsData {
  referrals: number;
  clicks: number;
  conversion: number;
  turnover: number;
}

interface CareerProgressData {
  currentTurnover: number;
  currentLevel: CareerLevelData;
  nextLevel?: CareerLevelData;
  progressPercent: number;
}

interface ProfileDataProp {
  name: string;
  handle: string;
  id: string;
  balance: number;
  earnedRef: number;
  saved: number;
  role: 'USER' | 'VIP' | 'ADMIN';
  isVip: boolean;
  referralLink: string;
  stats: ProfileStatsData;
  career: CareerProgressData;
  networkTree: NetworkNodeData[];
  billingLogs: BillingLogData[];
  currency: string;
  photoUrl?: string;
}

interface ProfileProps {
  profile?: ProfileDataProp;
  onBack: () => void;
  onHaptic?: (type?: 'light' | 'medium') => void;
  onAdminEnter?: () => void;
  onCopyLink?: () => void;
  onShare?: () => void;
  shareLoading?: boolean;
  onWithdraw?: () => void;
  onTopUp?: () => void;
}

// --- UTILITY: DECRYPTED TEXT ANIMATION ---
const CHARS = "ABCDEF0123456789!@#$%^&*()_+-=[]{}|;':\",./<>?";

const DecryptedText: React.FC<{ text: string | number; speed?: number; className?: string; reveal?: boolean }> = ({ text, speed = 30, className = "", reveal = true }) => {
  const [displayText, setDisplayText] = useState('');
  const [isFinished, setIsFinished] = useState(false);
  const textStr = String(text);

  useEffect(() => {
    if (!reveal) return;
    
    let iteration = 0;
    const interval = setInterval(() => {
      setDisplayText(
        textStr
          .split("")
          .map((letter, index) => {
            if (index < iteration) {
              return textStr[index];
            }
            return CHARS[Math.floor(Math.random() * CHARS.length)];
          })
          .join("")
      );

      if (iteration >= textStr.length) {
        setIsFinished(true);
        clearInterval(interval);
      }

      iteration += 1 / 2; // Speed of decryption
    }, speed);

    return () => clearInterval(interval);
  }, [textStr, speed, reveal]);

  return <span className={className}>{displayText || (reveal ? '' : textStr)}</span>;
};

// --- MOCK DATA ---
const MOCK_USER = {
  name: "Nikita",
  handle: "@gvmbt158",
  id: "UID-8492-X",
  balance: 12500,
  earnedRef: 12500,
  saved: 4500,
  role: "ADMIN", // Roles: USER, VIP, ADMIN
  isVip: true, // Allow VIP toggle testing
  referralLink: "https://pvndora.io/ref/8492X",
  stats: {
    referrals: 11,
    clicks: 142,
    conversion: 7.8, // %
    turnover: 120 // $ turnover (current progress)
  }
};

const CAREER_LEVELS = [
    { id: 1, label: "PROXY", min: 0, max: 250, color: "text-gray-400" },
    { id: 2, label: "OPERATOR", min: 250, max: 1000, color: "text-purple-400" },
    { id: 3, label: "ARCHITECT", min: 1000, max: 5000, color: "text-yellow-400" }
];

const NETWORK_TREE = [
    // LINE 1 (Direct Invites)
    { 
        id: 1, line: 1, handle: "@crypto_whale", rank: "ARCHITECT", status: "VIP", volume: 5400, profit: 540, subs: 12, signal: 100, lastActive: '2m ago',
        invitedBy: null, activityData: [20, 45, 30, 80, 50, 90, 100]
    },
    { 
        id: 2, line: 1, handle: "@neon_runner", rank: "PROXY", status: "ACTIVE", volume: 250, profit: 25, subs: 3, signal: 75, lastActive: '1h ago',
        invitedBy: null, activityData: [10, 20, 15, 40, 30, 25, 60]
    },
    { 
        id: 3, line: 1, handle: "@silent_bob", rank: "PROXY", status: "SLEEP", volume: 0, profit: 0, subs: 0, signal: 10, lastActive: '5d ago',
        invitedBy: null, activityData: [5, 5, 0, 0, 0, 0, 0]
    },
    { 
        id: 4, line: 1, handle: "@ai_artist_x", rank: "OPERATOR", status: "ACTIVE", volume: 890, profit: 89, subs: 5, signal: 90, lastActive: '15m ago',
        invitedBy: null, activityData: [30, 40, 50, 45, 60, 80, 70]
    },
    // LINE 2 (Invited by Line 1)
    { 
        id: 10, line: 2, handle: "@sub_zero", rank: "ARCHITECT", status: "ACTIVE", volume: 1500, profit: 105, subs: 0, signal: 85, lastActive: '10m ago',
        invitedBy: "@crypto_whale", activityData: [10, 40, 20, 50, 30, 80, 40]
    },
    { 
        id: 11, line: 2, handle: "@matrix_fan", rank: "OPERATOR", status: "ACTIVE", volume: 300, profit: 21, subs: 0, signal: 60, lastActive: '3h ago',
        invitedBy: "@crypto_whale", activityData: [5, 10, 5, 20, 15, 10, 30]
    },
    { 
        id: 12, line: 2, handle: "@pixel_dust", rank: "PROXY", status: "SLEEP", volume: 50, profit: 3.5, subs: 0, signal: 20, lastActive: '1d ago',
        invitedBy: "@neon_runner", activityData: [5, 5, 0, 0, 0, 0, 0]
    },
    // LINE 3 (Invited by Line 2)
    { 
        id: 20, line: 3, handle: "@deep_diver", rank: "ARCHITECT", status: "ACTIVE", volume: 2000, profit: 60, subs: 0, signal: 95, lastActive: '5m ago',
        invitedBy: "@sub_zero", activityData: [50, 60, 70, 80, 70, 90, 100]
    },
];

const BILLING_LOGS = [
    { id: "TX-9921", type: "INCOME", source: "REF_BONUS (L1)", amount: "+250.00", date: "10.12.24 14:20" },
    { id: "TX-9920", type: "OUTCOME", source: "WITHDRAWAL", amount: "-5000.00", date: "09.12.24 09:15" },
    { id: "TX-9919", type: "INCOME", source: "REF_BONUS (L2)", amount: "+120.50", date: "08.12.24 18:40" },
    { id: "TX-9918", type: "SYSTEM", source: "CASHBACK", amount: "+45.00", date: "05.12.24 11:00" },
];

// --- MAIN COMPONENT ---

const Profile: React.FC<ProfileProps> = ({ profile: propProfile, onBack, onHaptic, onAdminEnter, onCopyLink, onShare: onShareProp, shareLoading, onWithdraw, onTopUp }) => {
  const [copied, setCopied] = useState(false);
  const [activeTab, setActiveTab] = useState<'network' | 'logs'>('network');
  const [networkLine, setNetworkLine] = useState<1 | 2 | 3>(1);
  const [rewardMode, setRewardMode] = useState<'cash' | 'discount'>('cash');
  
  // DOSSIER STATE
  const [selectedReferralId, setSelectedReferralId] = useState<number | string | null>(null);
  
  // Use provided profile or fallback to mock
  const user = propProfile || MOCK_USER;
  const networkTree = propProfile?.networkTree?.length ? propProfile.networkTree : NETWORK_TREE;
  const billingLogs = propProfile?.billingLogs?.length ? propProfile.billingLogs : BILLING_LOGS;
  
  // Use networkTree (which may be from API or mock) instead of hardcoded NETWORK_TREE
  const selectedReferral = networkTree.find((n: any) => n.id === selectedReferralId);
  const displayedNodes = networkTree.filter((n: any) => (n as any).line === networkLine || !('line' in n));

  // Logic for Career Progress - use profile data if available
  const currentTurnover = propProfile?.career.currentTurnover ?? user.stats.turnover;
  const currentLevel = propProfile?.career.currentLevel ?? (CAREER_LEVELS.find(l => currentTurnover >= l.min && currentTurnover < l.max) || CAREER_LEVELS[CAREER_LEVELS.length - 1]);
  const nextLevel = propProfile?.career.nextLevel ?? CAREER_LEVELS.find(l => l.id === currentLevel.id + 1);
  const maxTurnover = nextLevel ? nextLevel.min : currentLevel.max;
  const progressPercent = propProfile?.career.progressPercent ?? (nextLevel 
    ? Math.min(100, Math.max(0, ((currentTurnover - currentLevel.min) / (nextLevel.min - currentLevel.min)) * 100))
    : 100);


  const handleCopy = () => {
    if(onHaptic) onHaptic('light');
    if (onCopyLink) {
      onCopyLink();
    } else {
      navigator.clipboard.writeText(user.referralLink);
    }
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleShare = async () => {
    if (onHaptic) onHaptic('medium');
    
    // Use prop handler if provided
    if (onShareProp) {
      onShareProp();
      return;
    }
    
    if (navigator.share) {
        try {
            await navigator.share({
                title: 'PVNDORA // INVITE',
                text: 'Access Restricted Neural Markets. Join via my secured node.',
                url: user.referralLink,
            });
        } catch (error) {
            console.log('Error sharing:', error);
        }
    } else {
        // Fallback if native share is not supported
        handleCopy();
    }
  };

  const changeLine = (line: 1 | 2 | 3) => {
      if(onHaptic) onHaptic('light');
      setNetworkLine(line);
  }

  const handleOpenDossier = (id: number) => {
      if(onHaptic) onHaptic('medium');
      setSelectedReferralId(id);
  }

  const handleCloseDossier = () => {
      if(onHaptic) onHaptic('light');
      setSelectedReferralId(null);
  }

  const toggleRewardMode = () => {
      if (!user.isVip && !user.role.includes('ADMIN')) return;
      if (onHaptic) onHaptic('medium');
      setRewardMode(prev => prev === 'cash' ? 'discount' : 'cash');
  }

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen text-white pt-24 pb-32 px-4 md:px-8 md:pl-28 relative"
    >
      <div className="max-w-7xl mx-auto relative z-10">
        
        {/* === UNIFIED HEADER (Leaderboard Style) === */}
        <div className="mb-8 md:mb-16">
            <button onClick={onBack} className="flex items-center gap-2 text-[10px] font-mono text-gray-500 hover:text-pandora-cyan mb-4 transition-colors">
                <ArrowLeft size={12} /> RETURN_TO_BASE
            </button>
            <h1 className="text-3xl sm:text-4xl md:text-6xl font-display font-black text-white uppercase tracking-tighter leading-[0.9] mb-4">
                OPERATIVE <br/> <span className="text-transparent bg-clip-text bg-gradient-to-r from-pandora-cyan to-white/50">PROFILE</span>
            </h1>
            <div className="flex items-center gap-2 text-[10px] font-mono text-pandora-cyan tracking-widest uppercase">
                    <User size={12} />
                    <span>User_Identity // Stats</span>
            </div>
        </div>

        {/* === USER CARD / IDENTITY === */}
        <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 mb-12 border-b border-white/10 pb-6">
            <div className="flex items-center gap-6">
                <div className="relative group">
                    <div className="w-20 h-20 bg-black border border-white/20 flex items-center justify-center relative overflow-hidden rounded-sm">
                         {user.photoUrl ? (
                           <img src={user.photoUrl} alt={user.name} className="w-full h-full object-cover relative z-10" />
                         ) : (
                           <User size={40} className="text-gray-400 relative z-10" />
                         )}
                         <div className="absolute inset-0 bg-gradient-to-tr from-pandora-cyan/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity" />
                         <div className="absolute top-0 w-full h-full bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-20 mix-blend-overlay" />
                    </div>
                    {/* Online Status Dot */}
                    <div className="absolute bottom-1 right-1 w-3 h-3 bg-green-500 rounded-full border-2 border-black animate-pulse" />
                </div>
                <div>
                    <h2 className="text-2xl font-display font-bold text-white tracking-tight mb-1 flex items-center gap-2">
                        {user.name}
                        {user.isVip && <Crown size={18} className="text-yellow-500 fill-yellow-500/20" />}
                    </h2>
                    <div className="flex items-center gap-3 text-xs font-mono text-gray-500">
                        <span>{user.handle}</span>
                        <span className="text-pandora-cyan">//</span>
                        <span>{user.id}</span>
                        {user.role === 'ADMIN' && (
                             <span className="text-red-500 font-bold bg-red-900/10 px-1 border border-red-500/30">ROOT_ADMIN</span>
                        )}
                    </div>
                </div>
            </div>
            {/* ADMIN ENTRY */}
            {user.role === 'ADMIN' && (
                <button 
                    onClick={onAdminEnter}
                    className="flex items-center gap-2 bg-red-900/10 border border-red-500/30 text-red-500 px-4 py-2 hover:bg-red-500 hover:text-white transition-all text-xs font-mono font-bold uppercase tracking-widest"
                >
                    <LayoutDashboard size={14} />
                    ACCESS_ADMIN_PANEL
                </button>
            )}
        </div>

        {/* === STATS OVERVIEW === */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-12">
            
            {/* 1. Internal Balance Card */}
            <div className="lg:col-span-4 flex flex-col">
                <div className="bg-[#080808] border border-white/10 p-6 relative overflow-hidden h-full flex flex-col justify-between group hover:border-pandora-cyan/30 transition-all">
                    <div className="absolute top-0 right-0 p-4 opacity-50 group-hover:opacity-100 transition-opacity"><Wallet size={24} className="text-pandora-cyan" /></div>
                    <div className="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-pandora-cyan/50 to-transparent scale-x-0 group-hover:scale-x-100 transition-transform duration-500 origin-left" />
                    
                    <div className="mb-6">
                        <div className="text-[10px] font-mono text-gray-500 uppercase tracking-widest mb-2 flex items-center gap-2">
                             Internal Balance <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
                        </div>
                        <div className="text-4xl sm:text-5xl font-display font-bold text-white flex items-baseline gap-2">
                            <DecryptedText text={user.balance} /> <span className="text-xl text-pandora-cyan">{user.currency === 'RUB' ? '₽' : '$'}</span>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-3 mt-auto">
                        <button 
                            onClick={() => { if(onHaptic) onHaptic('light'); if(onTopUp) onTopUp(); }}
                            className="bg-white/5 border border-white/10 hover:border-pandora-cyan text-white hover:text-pandora-cyan font-bold py-3 text-xs uppercase tracking-wider transition-colors flex items-center justify-center gap-2 rounded-sm"
                        >
                            <Plus size={14} /> Top Up
                        </button>
                        <button 
                            onClick={() => { if(onHaptic) onHaptic('medium'); if(onWithdraw) onWithdraw(); }}
                            className="bg-pandora-cyan text-black font-bold py-3 text-xs uppercase tracking-wider hover:bg-white transition-colors flex items-center justify-center gap-2 rounded-sm shadow-[0_0_15px_rgba(0,255,255,0.2)]"
                        >
                            <ArrowUpRight size={14} /> Withdraw
                        </button>
                    </div>
                </div>
            </div>

            {/* 2. Referral Link & Uplink Generator */}
            <div className="lg:col-span-8 flex flex-col">
                <div className="bg-[#0a0a0a] border border-white/10 p-6 h-full flex flex-col justify-between relative group hover:border-pandora-cyan/30 transition-all">
                     
                     {/* Header */}
                     <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 mb-6">
                        <div>
                            <h3 className="text-sm font-bold text-white flex items-center gap-2 mb-1">
                                <Network size={16} className="text-pandora-cyan" /> UPLINK_GENERATOR
                            </h3>
                            <p className="text-[10px] text-gray-500 font-mono">Invite users to build your node network.</p>
                        </div>

                        {/* Stats Summary */}
                        <div className="flex items-center gap-6 text-[10px] font-mono bg-white/5 px-4 py-2 rounded-sm border border-white/5 w-full sm:w-auto justify-between sm:justify-start">
                            <div className="flex flex-col items-center sm:items-start">
                                <span className="text-gray-500">CLICKS</span>
                                <span className="text-white font-bold text-base">{user.stats.clicks}</span>
                            </div>
                            <div className="w-px h-6 bg-white/10" />
                            <div className="flex flex-col items-center sm:items-start">
                                <span className="text-gray-500">CONVERSION</span>
                                <span className="text-pandora-cyan font-bold text-base">{user.stats.conversion}%</span>
                            </div>
                        </div>
                    </div>

                    {/* === INVITE CARD / ACCESS KEY === */}
                    <div className="flex flex-col md:flex-row gap-4 items-stretch">
                        
                        {/* Visual Access Card */}
                        <div className="flex-1 bg-black border border-white/20 p-4 relative overflow-hidden flex flex-col justify-center min-h-[100px]">
                            {/* Card Background Fx */}
                            <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10" />
                            <div className="absolute top-0 right-0 p-2 opacity-50"><QrCode size={32} className="text-white" /></div>
                            
                            <div className="relative z-10">
                                <div className="text-[9px] font-mono text-pandora-cyan mb-1 uppercase tracking-widest">Personal Access Token</div>
                                <code className="text-lg font-mono text-white font-bold tracking-widest break-all">
                                    {user.referralLink.split('/').pop()}
                                </code>
                            </div>
                        </div>

                        {/* Actions */}
                        <div className="flex flex-col gap-2 w-full md:w-48">
                            <button 
                                onClick={handleShare}
                                className="flex-1 bg-pandora-cyan text-black font-bold py-3 uppercase tracking-widest hover:bg-white transition-all flex items-center justify-center gap-2 rounded-sm shadow-[0_0_15px_rgba(0,255,255,0.3)] relative overflow-hidden group/btn"
                            >
                                <span className="relative z-10 flex items-center gap-2">
                                    <Share2 size={16} /> SHARE KEY
                                </span>
                                <div className="absolute inset-0 bg-white/50 translate-y-full group-hover/btn:translate-y-0 transition-transform duration-300" />
                            </button>
                            
                            <button 
                                onClick={handleCopy} 
                                className="flex-1 bg-white/5 hover:bg-white/10 text-white font-mono text-xs uppercase tracking-widest transition-colors flex items-center justify-center gap-2 rounded-sm border border-white/10"
                            >
                                {copied ? <><Check size={14} /> COPIED</> : <><Copy size={14} /> COPY LINK</>}
                            </button>
                        </div>
                    </div>

                    {/* Reward Toggle */}
                    {user.isVip && (
                        <div className="mt-4 flex items-center justify-between text-[10px] font-mono text-gray-500 border-t border-white/5 pt-3">
                            <span>REWARD PREFERENCE:</span>
                            <button 
                                onClick={toggleRewardMode}
                                className={`flex items-center gap-2 font-bold px-3 py-1 border rounded-sm transition-colors ${rewardMode === 'cash' ? 'border-green-500 text-green-500 bg-green-500/10' : 'border-purple-500 text-purple-500 bg-purple-500/10'}`}
                            >
                                {rewardMode === 'cash' ? <><Wallet size={12} /> CASH_OUT</> : <><Percent size={12} /> DISCOUNT</>}
                                <RefreshCw size={12} className="ml-1 opacity-50" />
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div>

        {/* === NETWORK CLEARANCE === */}
        <div className="mb-12">
            <h3 className="text-xs font-mono text-gray-500 uppercase mb-4 flex items-center gap-2">
                <ShieldCheck size={14} /> Network Clearance // Career Path
            </h3>
            
            <div className="bg-[#080808] border border-white/10 p-6 md:p-8 relative overflow-hidden group hover:border-white/20 transition-all">
                <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-6 relative z-10">
                    
                    {/* Current Status Info */}
                    <div className="w-full md:w-48 shrink-0">
                         <div className="text-[10px] text-gray-500 font-mono uppercase mb-1">Current Rank</div>
                         <div className={`text-2xl font-display font-bold ${currentLevel.color} flex items-center gap-2`}>
                            {currentLevel.label}
                            {currentLevel.id === 1 ? <Wifi size={18} /> : currentLevel.id === 2 ? <Radio size={18} /> : <Crown size={18} />}
                         </div>
                         <div className="text-[10px] text-gray-600 mt-1 font-mono">
                            Turnover: <span className="text-white font-bold">{currentTurnover}$</span> / {maxTurnover}$
                         </div>
                    </div>

                    {/* Progress Bar Container */}
                    <div className="flex-1 w-full relative pt-2 pb-6 md:py-0 md:px-8">
                        {/* Background Track */}
                        <div className="h-3 w-full bg-black border border-white/10 rounded-sm overflow-hidden relative">
                             {/* Fill */}
                             <motion.div 
                                initial={{ width: 0 }}
                                animate={{ width: `${progressPercent}%` }}
                                transition={{ duration: 1.5, ease: "circOut" }}
                                className="h-full bg-gradient-to-r from-gray-500 via-pandora-cyan to-white shadow-[0_0_15px_#00FFFF] relative overflow-hidden"
                             >
                                 {/* Scanline inside bar */}
                                 <div className="absolute inset-0 bg-white/30 w-full h-full -skew-x-12 translate-x-[-150%] animate-[scan_2s_infinite]" />
                             </motion.div>
                        </div>
                        
                        {/* Markers */}
                        <div className="flex justify-between text-[9px] font-mono text-gray-600 mt-2 absolute w-full bottom-0 md:static">
                            <span>{currentLevel.min}$</span>
                            {nextLevel ? <span>NEXT: {nextLevel.label} ({nextLevel.min}$)</span> : <span>MAX LEVEL</span>}
                        </div>
                    </div>

                    {/* Next Reward Preview */}
                    <div className="hidden md:flex flex-col items-end w-40 shrink-0 text-right opacity-80">
                         {nextLevel ? (
                             <>
                                <div className="text-[9px] text-gray-500 font-mono uppercase mb-1">Next Unlock</div>
                                <div className={`text-sm font-bold ${nextLevel.color}`}>{nextLevel.label}</div>
                             </>
                         ) : (
                             <div className="text-pandora-cyan font-bold text-sm">MAXIMUM CLEARANCE</div>
                         )}
                    </div>

                </div>
            </div>
        </div>

        {/* === SYSTEM LOGS & SCANNER === */}
        <div className="border border-white/10 bg-[#050505] shadow-[0_0_50px_rgba(0,0,0,0.5)]">
            <div className="bg-[#0a0a0a] border-b border-white/10 p-2 px-4 flex flex-col sm:flex-row items-center gap-6">
                 
                 {/* Main Tabs */}
                 <div className="flex items-center gap-6 overflow-x-auto w-full sm:w-auto">
                    <button onClick={() => { if(onHaptic) onHaptic('light'); setActiveTab('network'); }} className={`text-[10px] font-mono font-bold uppercase flex items-center gap-2 whitespace-nowrap ${activeTab === 'network' ? 'text-pandora-cyan' : 'text-gray-600'}`}><GitBranch size={12} /> NETWORK_SCANNER</button>
                    <button onClick={() => { if(onHaptic) onHaptic('light'); setActiveTab('logs'); }} className={`text-[10px] font-mono font-bold uppercase whitespace-nowrap ${activeTab === 'logs' ? 'text-pandora-cyan' : 'text-gray-600'}`}>SYSTEM_LOGS</button>
                 </div>

                 {/* Network Level Filter (Only visible when Network tab is active) */}
                 {activeTab === 'network' && (
                     <div className="flex items-center bg-[#050505] border border-white/10 rounded-sm ml-auto overflow-hidden">
                        {[1, 2, 3].map((line) => (
                            <button
                                key={line}
                                onClick={() => changeLine(line as 1 | 2 | 3)}
                                className={`px-4 py-1.5 text-[9px] font-mono font-bold border-r border-white/10 last:border-0 hover:bg-white/5 transition-colors ${networkLine === line ? 'bg-pandora-cyan/20 text-pandora-cyan' : 'text-gray-500'}`}
                            >
                                LINE {line}
                            </button>
                        ))}
                     </div>
                 )}
            </div>

            <div className="p-0 font-mono text-xs">
                {activeTab === 'network' && (
                    <div className="relative min-h-[300px]">
                        {/* Vertical Connection Line */}
                        <div className="absolute top-0 bottom-0 left-6 w-px bg-gradient-to-b from-pandora-cyan/30 via-white/5 to-transparent z-0" />
                        
                        {displayedNodes.length === 0 ? (
                            <div className="flex flex-col items-center justify-center py-20 text-gray-600">
                                <Network size={24} className="mb-2 opacity-20" />
                                <span className="uppercase tracking-widest text-[10px]">NO_DATA_ON_LINE_{networkLine}</span>
                            </div>
                        ) : (
                            displayedNodes.map((node) => (
                                <div key={node.id} className="relative pl-12 pr-4 py-4 border-b border-white/5 hover:bg-white/[0.02] transition-colors group">
                                    {/* Node Connector Dot */}
                                    <div className="absolute left-[21px] top-8 w-1.5 h-1.5 rounded-full bg-[#050505] border border-pandora-cyan z-10 box-content" />
                                    {/* Horizontal Connector Line */}
                                    <div className="absolute left-6 top-9 w-6 h-px bg-white/10 group-hover:bg-pandora-cyan/50 transition-colors" />

                                    <div 
                                        onClick={() => handleOpenDossier(node.id)}
                                        className={`
                                            bg-[#0a0a0a] border border-white/10 hover:border-pandora-cyan/50 hover:shadow-[0_0_15px_rgba(0,255,255,0.1)] 
                                            transition-all duration-300 rounded-sm p-4 relative overflow-hidden cursor-pointer
                                            ${node.status === 'VIP' ? 'border-l-2 border-l-yellow-500' : ''}
                                        `}
                                    >
                                        <div className="flex justify-between items-center">
                                            <div className="flex items-center gap-3">
                                                <div className="w-8 h-8 bg-white/5 flex items-center justify-center rounded-sm overflow-hidden">
                                                    {node.photoUrl ? (
                                                      <img src={node.photoUrl} alt={node.handle} className="w-full h-full object-cover" />
                                                    ) : node.status === 'VIP' ? (
                                                      <Crown size={14} className="text-yellow-500" />
                                                    ) : (
                                                      <User size={14} className="text-gray-400" />
                                                    )}
                                                </div>
                                                <div>
                                                    <div className="flex items-center gap-2">
                                                        <span className="font-bold text-white text-sm">{node.handle}</span>
                                                        <span className={`text-[8px] px-1 rounded-sm border ${node.rank === 'ARCHITECT' ? 'border-yellow-500 text-yellow-500' : node.rank === 'OPERATOR' ? 'border-purple-500 text-purple-500' : 'border-gray-500 text-gray-500'}`}>{node.rank}</span>
                                                    </div>
                                                    <div className="flex items-center gap-2 text-[9px] text-gray-600">
                                                        <span>ID: #{node.id}</span>
                                                        {node.invitedBy && (
                                                            <>
                                                                <span>&bull;</span>
                                                                <span className="text-gray-500">UPLINK: {node.invitedBy}</span>
                                                            </>
                                                        )}
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="text-right">
                                                <div className="text-xs font-bold text-pandora-cyan">+{node.profit} $</div>
                                                <div className="text-[9px] text-gray-500">COMMISSION</div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            ))
                        )}
                    </div>
                )}
                {activeTab === 'logs' && (
                    <div className="divide-y divide-white/5">
                        {billingLogs.map((log, i) => (
                            <div key={i} className="grid grid-cols-12 px-4 py-3 hover:bg-white/5 transition-colors">
                                <div className="col-span-3 sm:col-span-2 text-gray-500">{log.id}</div>
                                <div className="col-span-3 sm:col-span-2"><span className={`px-1 text-[9px] border ${log.type === 'INCOME' ? 'text-green-500 border-green-500/30' : 'text-blue-500 border-blue-500/30'}`}>{log.type}</span></div>
                                <div className="col-span-3 sm:col-span-4 text-gray-300 truncate">{log.source}</div>
                                <div className="col-span-3 sm:col-span-4 text-right text-white font-bold">{log.amount}</div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
      </div>

      {/* === REFERRAL DOSSIER (SIDE DRAWER) === */}
      <AnimatePresence>
        {selectedReferralId && selectedReferral && (
            <div className="fixed inset-0 z-[200] flex justify-end">
                {/* Backdrop (Click to close) */}
                <motion.div 
                    initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
                    onClick={handleCloseDossier}
                    className="absolute inset-0 bg-black/60 backdrop-blur-sm"
                />
                
                {/* The Drawer */}
                <motion.div 
                    initial={{ x: "100%" }}
                    animate={{ x: 0 }}
                    exit={{ x: "100%" }}
                    transition={{ type: "spring", damping: 25, stiffness: 200 }}
                    className="relative w-full max-w-md bg-[#050505] border-l border-pandora-cyan/30 shadow-[-20px_0_50px_rgba(0,0,0,0.8)] h-full overflow-y-auto"
                >
                    {/* Header */}
                    <div className="p-6 border-b border-white/10 bg-[#0a0a0a] flex justify-between items-start sticky top-0 z-20">
                        <div>
                             <div className="flex items-center gap-2 text-[10px] font-mono text-pandora-cyan mb-1 animate-pulse">
                                <ShieldCheck size={12} />
                                DECRYPTING_SECURE_FILE...
                             </div>
                             <h2 className="text-2xl font-display font-bold text-white uppercase flex items-center gap-2">
                                <DecryptedText text={selectedReferral.handle} speed={40} />
                             </h2>
                             {selectedReferral.line > 1 && (
                                 <div className="text-[10px] font-mono text-gray-500 mt-1">
                                     UPLINK_SOURCE: {selectedReferral.invitedBy}
                                 </div>
                             )}
                        </div>
                        <button onClick={handleCloseDossier} className="text-gray-500 hover:text-white transition-colors">
                            <X size={24} />
                        </button>
                    </div>

                    <div className="p-6 pb-24 space-y-8 relative">
                        {/* 1. Identity Matrix */}
                        <div className="flex gap-4 items-center">
                            <div className="w-20 h-20 bg-black border border-white/20 p-1 relative">
                                <div className="w-full h-full bg-gray-900 flex items-center justify-center overflow-hidden">
                                     {selectedReferral.photoUrl ? (
                                       <img src={selectedReferral.photoUrl} alt={selectedReferral.handle} className="w-full h-full object-cover" />
                                     ) : (
                                       <User size={32} className="text-gray-600" />
                                     )}
                                </div>
                                <div className="absolute top-0 right-0 w-3 h-3 border-t border-r border-pandora-cyan" />
                                <div className="absolute bottom-0 left-0 w-3 h-3 border-b border-l border-pandora-cyan" />
                            </div>
                            <div className="space-y-1">
                                <div className="text-xs text-gray-500 font-mono">STATUS: 
                                    <span className={`ml-2 font-bold ${selectedReferral.status === 'VIP' ? 'text-yellow-500' : selectedReferral.status === 'SLEEP' ? 'text-red-500' : 'text-green-500'}`}>
                                        <DecryptedText text={selectedReferral.status} reveal={true} />
                                    </span>
                                </div>
                                <div className="text-xs text-gray-500 font-mono">LAST_SEEN: <span className="text-white">{selectedReferral.lastActive}</span></div>
                                <div className="text-xs text-gray-500 font-mono">RANK: <span className="text-pandora-cyan">{selectedReferral.rank}</span></div>
                            </div>
                        </div>

                        {/* 2. Visual Activity Graph */}
                        <div className="bg-white/5 border border-white/10 p-4 rounded-sm relative group">
                            <div className="flex justify-between items-center mb-4">
                                <div className="text-[10px] font-mono text-gray-500 uppercase flex items-center gap-2"><Activity size={12} /> Signal Activity (7D)</div>
                                <div className="text-pandora-cyan text-xs font-bold">+12.4%</div>
                            </div>
                            
                            {/* CSS-based Line Chart Simulation */}
                            <div className="h-32 w-full flex items-end gap-1 relative">
                                {/* Grid lines */}
                                <div className="absolute inset-0 flex flex-col justify-between opacity-10 pointer-events-none">
                                    <div className="w-full h-px bg-white" />
                                    <div className="w-full h-px bg-white" />
                                    <div className="w-full h-px bg-white" />
                                </div>
                                
                                {selectedReferral.activityData.map((val, i) => (
                                    <div key={i} className="flex-1 flex flex-col justify-end group/bar h-full">
                                        <motion.div 
                                            initial={{ height: 0 }}
                                            animate={{ height: `${val}%` }}
                                            transition={{ duration: 0.5, delay: 0.1 * i }}
                                            className="w-full bg-pandora-cyan/20 border-t border-pandora-cyan relative hover:bg-pandora-cyan/40 transition-colors"
                                        >
                                            <div className="absolute -top-6 left-1/2 -translate-x-1/2 bg-black text-white text-[9px] px-1 opacity-0 group-hover/bar:opacity-100 transition-opacity">
                                                {val}
                                            </div>
                                        </motion.div>
                                    </div>
                                ))}
                            </div>
                        </div>

                        {/* 3. Financial Metrics */}
                        <div className="grid grid-cols-2 gap-4">
                             <div className="bg-[#0e0e0e] p-3 border border-white/10">
                                 <div className="text-[9px] text-gray-500 font-mono uppercase mb-1">Total Volume</div>
                                 <div className="text-xl font-bold text-white flex items-center gap-1">
                                    <DecryptedText text={selectedReferral.volume} /> $
                                 </div>
                             </div>
                             <div className="bg-[#0e0e0e] p-3 border border-white/10">
                                 <div className="text-[9px] text-gray-500 font-mono uppercase mb-1">Commission Earned</div>
                                 <div className="text-xl font-bold text-pandora-cyan flex items-center gap-1">
                                    +<DecryptedText text={selectedReferral.profit} /> $
                                 </div>
                             </div>
                        </div>

                        {/* 4. Connection Details */}
                        <div className="space-y-3">
                            <h4 className="text-xs font-mono text-gray-500 uppercase border-b border-white/10 pb-2">Connection Telemetry</h4>
                            <div className="flex justify-between items-center text-xs">
                                <span className="text-gray-400">Signal Strength</span>
                                <div className="flex items-center gap-1">
                                    <div className={`w-12 h-1 bg-gray-800 rounded-full overflow-hidden`}>
                                        <div className="h-full bg-green-500" style={{ width: `${selectedReferral.signal}%` }} />
                                    </div>
                                    <span className="font-mono text-green-500">{selectedReferral.signal}%</span>
                                </div>
                            </div>
                            <div className="flex justify-between items-center text-xs">
                                <span className="text-gray-400">Downlink Nodes</span>
                                <span className="font-mono text-white">{selectedReferral.subs} Active</span>
                            </div>
                            <div className="flex justify-between items-center text-xs">
                                <span className="text-gray-400">Encryption</span>
                                <span className="font-mono text-pandora-cyan">AES-256</span>
                            </div>
                        </div>

                        {/* 5. Close Button (Mobile Friendly) */}
                        <button 
                            onClick={handleCloseDossier}
                            className="w-full py-4 border border-white/10 text-gray-500 hover:text-white hover:bg-white/5 text-xs font-mono uppercase tracking-widest transition-colors mt-8"
                        >
                            // CLOSE_FILE
                        </button>

                    </div>
                </motion.div>
            </div>
        )}
      </AnimatePresence>

    </motion.div>
  );
};

export default Profile;
