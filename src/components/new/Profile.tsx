/**
 * Profile Component
 * 
 * Main profile page container that orchestrates all profile views.
 */

import React, { useState, useCallback } from 'react';
import { motion } from 'framer-motion';
import { User, ArrowLeft } from 'lucide-react';
import { AudioEngine } from '../../lib/AudioEngine';
import { useClipboard } from '../../hooks/useClipboard';
import { logger } from '../../utils/logger';
// Career levels come from API via profile.career - no hardcoded constants
import {
  ProfileHeader,
  ProfileStats,
  ProfileCareer,
  ProfileNetwork,
  ProfileBilling,
  ReferralDossier,
  type ProfileDataProp,
} from '../profile';

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
  onUpdatePreferences?: (preferred_currency?: string, interface_language?: string) => Promise<{ success: boolean; message: string }>;
}

// --- MAIN COMPONENT ---

const Profile: React.FC<ProfileProps> = ({ profile: propProfile, onBack, onHaptic, onAdminEnter, onCopyLink, onShare: onShareProp, shareLoading, onWithdraw, onTopUp, onUpdatePreferences }) => {
  const { copy: copyToClipboard, copied } = useClipboard();
  const [activeTab, setActiveTab] = useState<'network' | 'logs'>('network');
  const [networkLine, setNetworkLine] = useState<1 | 2 | 3>(1);
  const [rewardMode, setRewardMode] = useState<'cash' | 'discount'>('cash');
  
  // DOSSIER STATE
  const [selectedReferralId, setSelectedReferralId] = useState<number | string | null>(null);
  
  // Use provided profile data only - NO MOCK FALLBACK (production)
  if (!propProfile) {
    // Return empty state if no profile data provided
    return (
      <div className="min-h-screen text-white pt-20 md:pt-24 pb-32 px-4 md:px-8 md:pl-28 relative">
        <div className="max-w-7xl mx-auto">
          <button onClick={onBack} className="flex items-center gap-2 text-[10px] font-mono text-gray-500 hover:text-pandora-cyan mb-4 transition-colors">
            <ArrowLeft size={12} /> RETURN_TO_BASE
          </button>
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <User size={64} className="text-gray-700 mb-6" />
            <h2 className="text-2xl font-bold text-white mb-2">NO PROFILE DATA</h2>
            <p className="text-gray-500 font-mono text-sm max-w-md">
              Profile data is not available. Please try again later.
            </p>
          </div>
        </div>
      </div>
    );
  }
  
  const user = propProfile;
  const networkTree = propProfile?.networkTree || [];
  const billingLogs = propProfile?.billingLogs || [];
  
  // Use networkTree (which may be from API or mock) instead of hardcoded NETWORK_TREE
  const selectedReferral = networkTree.find((n) => n.id === selectedReferralId);

  // Career Progress - all data from API (thresholds loaded from DB)
  const currentTurnover = propProfile.career.currentTurnover;
  const currentLevel = propProfile.career.currentLevel;
  const nextLevel = propProfile.career.nextLevel;
  const maxTurnover = nextLevel ? nextLevel.min : currentLevel.max;
  const progressPercent = propProfile.career.progressPercent;


  const handleCopy = useCallback(async () => {
    if(onHaptic) onHaptic('light');
    if (onCopyLink) {
      onCopyLink();
    } else if (user.referralLink) {
      await copyToClipboard(user.referralLink);
    }
  }, [onHaptic, onCopyLink, user.referralLink, copyToClipboard]);

  const handleShare = useCallback(async () => {
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
          logger.error('Share failed', error);
            // Share cancelled or failed - silent handling
        }
    } else {
        // Fallback if native share is not supported
        handleCopy();
    }
  }, [onHaptic, onShareProp, user.referralLink, handleCopy]);

  const changeLine = (line: 1 | 2 | 3) => {
      if(onHaptic) onHaptic('light');
      setNetworkLine(line);
  }

  const handleOpenDossier = (id: number | string) => {
    if(onHaptic) onHaptic('medium');
    AudioEngine.decrypt(); // Play decrypt sound for dossier reveal
    setSelectedReferralId(id);
  };

  const handleCloseDossier = () => {
      if(onHaptic) onHaptic('light');
      AudioEngine.panelClose();
      setSelectedReferralId(null);
  }

  const toggleRewardMode = () => {
    if (!user.isVip && !user.role.includes('ADMIN')) return;
    if (onHaptic) onHaptic('medium');
    setRewardMode(prev => prev === 'cash' ? 'discount' : 'cash');
  };

  return (
    <motion.div 
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen text-white pt-20 md:pt-24 pb-32 px-4 md:px-8 md:pl-28 relative"
    >
      <div className="max-w-7xl mx-auto relative z-10">
        <ProfileHeader 
          user={user} 
          onBack={onBack} 
          onAdminEnter={onAdminEnter}
        />

        <ProfileStats
          user={user}
          copied={copied}
          rewardMode={rewardMode}
          onHaptic={onHaptic}
          onTopUp={onTopUp}
          onWithdraw={onWithdraw}
          onCopy={handleCopy}
          onShare={handleShare}
          onToggleRewardMode={toggleRewardMode}
          onUpdatePreferences={onUpdatePreferences}
        />

        <ProfileCareer
          currentLevel={currentLevel}
          nextLevel={nextLevel}
          currentTurnover={currentTurnover}
          maxTurnover={maxTurnover}
          progressPercent={progressPercent}
        />

        {/* System Logs & Scanner */}
        <div className="mb-12">
          <div className="bg-[#0a0a0a] border-b border-white/10 p-2 px-4 flex flex-col sm:flex-row items-center gap-6 mb-0">
            {/* Main Tabs */}
            <div className="flex items-center gap-6 overflow-x-auto w-full sm:w-auto">
              <button 
                onClick={() => { if(onHaptic) onHaptic('light'); setActiveTab('network'); }} 
                className={`text-[10px] font-mono font-bold uppercase flex items-center gap-2 whitespace-nowrap ${
                  activeTab === 'network' ? 'text-pandora-cyan' : 'text-gray-600'
                }`}
              >
                NETWORK_SCANNER
              </button>
              <button 
                onClick={() => { if(onHaptic) onHaptic('light'); setActiveTab('logs'); }} 
                className={`text-[10px] font-mono font-bold uppercase whitespace-nowrap ${
                  activeTab === 'logs' ? 'text-pandora-cyan' : 'text-gray-600'
                }`}
              >
                SYSTEM_LOGS
              </button>
            </div>
          </div>

          {activeTab === 'network' ? (
            <ProfileNetwork
              nodes={networkTree}
              networkLine={networkLine}
              onLineChange={changeLine}
              onNodeClick={handleOpenDossier}
            />
          ) : (
            <ProfileBilling logs={billingLogs} />
          )}
        </div>
      </div>

      {/* Referral Dossier */}
      <ReferralDossier
        referral={selectedReferral || null}
        onClose={handleCloseDossier}
      />
    </motion.div>
  );
};


export default Profile;
