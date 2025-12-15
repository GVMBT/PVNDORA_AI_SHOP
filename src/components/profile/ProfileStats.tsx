/**
 * ProfileStats Component
 * 
 * Displays balance card, referral link generator, and stats overview.
 */

import React, { memo, useCallback } from 'react';
import { Wallet, Plus, ArrowUpRight, Network, Share2, Copy, Check, Percent, RefreshCw, Settings, QrCode } from 'lucide-react';
import { formatPrice, getCurrencySymbol } from '../../utils/currency';
import DecryptedText from './DecryptedText';
import type { ProfileDataProp } from './types';

interface ProfileStatsProps {
  user: ProfileDataProp;
  copied: boolean;
  rewardMode: 'cash' | 'discount';
  onHaptic?: (type?: 'light' | 'medium') => void;
  onTopUp?: () => void;
  onWithdraw?: () => void;
  onCopy: () => void;
  onShare: () => void;
  onToggleRewardMode: () => void;
  onUpdatePreferences?: (preferred_currency?: string, interface_language?: string) => Promise<{ success: boolean; message: string }>;
}

const ProfileStats: React.FC<ProfileStatsProps> = ({
  user,
  copied,
  rewardMode,
  onHaptic,
  onTopUp,
  onWithdraw,
  onCopy,
  onShare,
  onToggleRewardMode,
  onUpdatePreferences,
}) => {
  const handleCurrencyChange = useCallback(async (currency: 'USD' | 'RUB') => {
    if (onHaptic) onHaptic('light');
    if (onUpdatePreferences) {
      try {
        await onUpdatePreferences(currency, undefined);
        if (onHaptic) onHaptic('light');
        if (currency === 'USD') {
          window.location.reload(); // Reload to apply currency change
        }
      } catch (err) {
        // Error handled by logger in parent
      }
    }
  }, [onHaptic, onUpdatePreferences]);

  const handleLanguageChange = useCallback(async (lang: 'ru' | 'en') => {
    if (onHaptic) onHaptic('light');
    if (onUpdatePreferences) {
      try {
        await onUpdatePreferences(undefined, lang);
        if (onHaptic) onHaptic('light');
        if (lang === 'ru') {
          window.location.reload(); // Reload to apply language change
        }
      } catch (err) {
        // Error handled by logger in parent
      }
    }
  }, [onHaptic, onUpdatePreferences]);

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-12">
      {/* Internal Balance Card */}
      <div className="lg:col-span-4 flex flex-col">
        <div className="bg-[#080808] border border-white/10 p-6 relative overflow-hidden h-full flex flex-col justify-between group hover:border-pandora-cyan/30 transition-all">
          <div className="absolute top-0 right-0 p-4 opacity-50 group-hover:opacity-100 transition-opacity">
            <Wallet size={24} className="text-pandora-cyan" />
          </div>
          <div className="absolute bottom-0 left-0 w-full h-1 bg-gradient-to-r from-pandora-cyan/50 to-transparent scale-x-0 group-hover:scale-x-100 transition-transform duration-500 origin-left" />
          
          <div className="mb-6">
            <div className="text-[10px] font-mono text-gray-500 uppercase tracking-widest mb-2 flex items-center gap-2">
              Internal Balance <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
            </div>
            <div className="text-4xl sm:text-5xl font-display font-bold text-white flex items-baseline gap-2">
              <DecryptedText text={user.balance} /> 
              <span className="text-xl text-pandora-cyan">{getCurrencySymbol(user.currency)}</span>
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

      {/* Referral Link & Uplink Generator */}
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

          {/* Invite Card / Access Key */}
          <div className="flex flex-col md:flex-row gap-4 items-stretch">
            {/* Visual Access Card */}
            <div className="flex-1 bg-black border border-white/20 p-4 relative overflow-hidden flex flex-col justify-center min-h-[100px]">
              {/* Card Background Fx */}
              <div className="absolute inset-0 bg-[url('https://grainy-gradients.vercel.app/noise.svg')] opacity-10" />
              <div className="absolute top-0 right-0 p-2 opacity-50">
                <QrCode size={32} className="text-white" />
              </div>
              
              <div className="relative z-10">
                <div className="text-[9px] font-mono text-pandora-cyan mb-1 uppercase tracking-widest">
                  Personal Access Token
                </div>
                <code className="text-lg font-mono text-white font-bold tracking-widest break-all">
                  {user.referralLink.split('/').pop()}
                </code>
              </div>
            </div>

            {/* Actions */}
            <div className="flex flex-col gap-2 w-full md:w-48">
              <button 
                onClick={onShare}
                className="flex-1 bg-pandora-cyan text-black font-bold py-3 uppercase tracking-widest hover:bg-white transition-all flex items-center justify-center gap-2 rounded-sm shadow-[0_0_15px_rgba(0,255,255,0.3)] relative overflow-hidden group/btn"
              >
                <span className="relative z-10 flex items-center gap-2">
                  <Share2 size={16} /> SHARE KEY
                </span>
                <div className="absolute inset-0 bg-white/50 translate-y-full group-hover/btn:translate-y-0 transition-transform duration-300" />
              </button>
              
              <button 
                onClick={onCopy} 
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
                onClick={onToggleRewardMode}
                className={`flex items-center gap-2 font-bold px-3 py-1 border rounded-sm transition-colors ${
                  rewardMode === 'cash' 
                    ? 'border-green-500 text-green-500 bg-green-500/10' 
                    : 'border-purple-500 text-purple-500 bg-purple-500/10'
                }`}
              >
                {rewardMode === 'cash' ? <><Wallet size={12} /> CASH_OUT</> : <><Percent size={12} /> DISCOUNT</>}
                <RefreshCw size={12} className="ml-1 opacity-50" />
              </button>
            </div>
          )}

          {/* Language & Currency Settings */}
          {onUpdatePreferences && (
            <div className="mt-4 border-t border-white/5 pt-3">
              <div className="text-[10px] font-mono text-gray-500 uppercase mb-2 flex items-center gap-2">
                <Settings size={12} /> INTERFACE_SETTINGS
              </div>
              <div className="flex flex-col gap-2">
                {/* Currency Selector */}
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono text-gray-600">CURRENCY:</span>
                  <div className="flex gap-1">
                    <button
                      onClick={() => handleCurrencyChange('USD')}
                      className={`px-2 py-1 text-[9px] font-mono border rounded-sm transition-colors ${
                        user.currency === 'USD' 
                          ? 'border-pandora-cyan text-pandora-cyan bg-pandora-cyan/10' 
                          : 'border-white/10 text-gray-500 hover:border-white/20'
                      }`}
                    >
                      USD
                    </button>
                    <button
                      onClick={() => handleCurrencyChange('RUB')}
                      className={`px-2 py-1 text-[9px] font-mono border rounded-sm transition-colors ${
                        user.currency === 'RUB' 
                          ? 'border-pandora-cyan text-pandora-cyan bg-pandora-cyan/10' 
                          : 'border-white/10 text-gray-500 hover:border-white/20'
                      }`}
                    >
                      RUB
                    </button>
                  </div>
                </div>
                {/* Language Selector */}
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-mono text-gray-600">LANGUAGE:</span>
                  <div className="flex gap-1">
                    <button
                      onClick={() => handleLanguageChange('ru')}
                      className="px-2 py-1 text-[9px] font-mono border border-white/10 text-gray-500 hover:border-white/20 rounded-sm transition-colors"
                    >
                      RU
                    </button>
                    <button
                      onClick={() => handleLanguageChange('en')}
                      className="px-2 py-1 text-[9px] font-mono border border-white/10 text-gray-500 hover:border-white/20 rounded-sm transition-colors"
                    >
                      EN
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default memo(ProfileStats);




