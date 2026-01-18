/**
 * Profile Component
 *
 * Main profile page container that orchestrates all profile views.
 */

import { motion } from "framer-motion";
import { ArrowLeft, User } from "lucide-react";
import type React from "react";
import { useCallback, useEffect, useState } from "react";
import { useClipboard } from "../../hooks/useClipboard";
import { useLocale } from "../../hooks/useLocale";
import { AudioEngine } from "../../lib/AudioEngine";
import { logger } from "../../utils/logger";
// Career levels come from API via profile.career - no hardcoded constants
import {
  ProfileBilling,
  ProfileCareer,
  type ProfileDataProp,
  ProfileHeader,
  ProfileNetwork,
  ProfileStats,
  ReferralDossier,
} from "../profile";

interface ProfileProps {
  profile?: ProfileDataProp;
  onBack: () => void;
  onHaptic?: (type?: "light" | "medium") => void;
  onAdminEnter?: () => void;
  onStudioEnter?: () => void;
  onCopyLink?: () => void;
  onShare?: () => void;
  shareLoading?: boolean;
  onWithdraw?: () => void;
  onTopUp?: () => void;
  onUpdatePreferences?: (
    preferred_currency?: string,
    interface_language?: string
  ) => Promise<{ success: boolean; message: string }>;
  onSetPartnerMode?: (mode: "commission" | "discount") => Promise<{ success: boolean }>;
  onApplyPartner?: () => void;
  onCancelWithdrawal?: (withdrawalId: string) => Promise<void>;
}

// --- MAIN COMPONENT ---

const Profile: React.FC<ProfileProps> = ({
  profile: propProfile,
  onBack,
  onHaptic,
  onAdminEnter,
  onStudioEnter,
  onCopyLink,
  onShare: onShareProp,
  shareLoading: _shareLoading,
  onWithdraw,
  onTopUp,
  onUpdatePreferences,
  onSetPartnerMode,
  onApplyPartner,
  onCancelWithdrawal,
}) => {
  const { t } = useLocale();
  const { copy: copyToClipboard, copied } = useClipboard();
  const [activeTab, setActiveTab] = useState<"network" | "logs">("network");
  const [networkLine, setNetworkLine] = useState<1 | 2 | 3>(1);
  // Initialize reward mode from profile data (map commission/discount to cash/discount)
  // Always initialize with 'cash' to maintain hook order consistency
  const [rewardMode, setRewardMode] = useState<"cash" | "discount">("cash");

  // DOSSIER STATE
  const [selectedReferralId, setSelectedReferralId] = useState<number | string | null>(null);

  // Sync reward mode with profile when it changes (useEffect to avoid conditional hook)
  useEffect(() => {
    if (propProfile?.partnerMode) {
      setRewardMode(propProfile.partnerMode === "discount" ? "discount" : "cash");
    }
  }, [propProfile?.partnerMode]);

  // All callbacks must be defined before any conditional returns
  const handleCopy = useCallback(async () => {
    if (onHaptic) onHaptic("light");
    if (onCopyLink) {
      onCopyLink();
    } else if (propProfile?.referralLink) {
      await copyToClipboard(propProfile.referralLink);
    }
  }, [onHaptic, onCopyLink, propProfile?.referralLink, copyToClipboard]);

  const handleShare = useCallback(async () => {
    if (onHaptic) onHaptic("medium");

    // Use prop handler if provided
    if (onShareProp) {
      onShareProp();
      return;
    }

    if (navigator.share) {
      try {
        await navigator.share({
          title: "PVNDORA // INVITE",
          text: "Access Restricted Neural Markets. Join via my secured node.",
          url: propProfile?.referralLink,
        });
      } catch (error) {
        logger.error("Share failed", error);
        // Share cancelled or failed - silent handling
      }
    } else {
      // Fallback if native share is not supported
      handleCopy();
    }
  }, [onHaptic, onShareProp, propProfile?.referralLink, handleCopy]);

  // Use provided profile data only - NO MOCK FALLBACK (production)
  if (!propProfile) {
    // Return empty state if no profile data provided
    return (
      <div className="min-h-screen text-white pt-20 md:pt-24 pb-32 px-4 md:px-8 md:pl-28 relative">
        <div className="max-w-7xl mx-auto">
          <button
            type="button"
            onClick={onBack}
            className="flex items-center gap-2 text-[10px] font-mono text-gray-500 hover:text-pandora-cyan mb-4 transition-colors"
          >
            <ArrowLeft size={12} /> {t("empty.returnToBase").toUpperCase()}
          </button>
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <User size={64} className="text-gray-700 mb-6" />
            <h2 className="text-2xl font-bold text-white mb-2">
              {t("empty.profile").toUpperCase()}
            </h2>
            <p className="text-gray-500 font-mono text-sm max-w-md">{t("empty.profileHint")}</p>
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

  const changeLine = (line: 1 | 2 | 3) => {
    if (onHaptic) onHaptic("light");
    setNetworkLine(line);
  };

  const handleOpenDossier = (id: number | string) => {
    if (onHaptic) onHaptic("medium");
    AudioEngine.decrypt(); // Play decrypt sound for dossier reveal
    setSelectedReferralId(id);
  };

  const handleCloseDossier = () => {
    if (onHaptic) onHaptic("light");
    AudioEngine.panelClose();
    setSelectedReferralId(null);
  };

  const toggleRewardMode = async () => {
    if (!user.isVip) return; // VIP only
    if (onHaptic) onHaptic("medium");

    const newMode = rewardMode === "cash" ? "discount" : "cash";
    const apiMode = newMode === "cash" ? "commission" : "discount";

    // Optimistic update
    setRewardMode(newMode);

    // Call API if handler provided
    if (onSetPartnerMode) {
      try {
        await onSetPartnerMode(apiMode);
      } catch {
        // Revert on error - use the previous mode (opposite of new)
        setRewardMode(newMode === "cash" ? "discount" : "cash");
      }
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="min-h-screen text-white pt-20 md:pt-24 pb-32 px-4 md:px-8 md:pl-28 relative"
    >
      <div className="max-w-7xl mx-auto relative z-10">
        <ProfileHeader user={user} onBack={onBack} onAdminEnter={onAdminEnter} onStudioEnter={onStudioEnter} />

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
          onCancelWithdrawal={onCancelWithdrawal}
        />

        <ProfileCareer
          currentLevel={currentLevel}
          nextLevel={nextLevel}
          currentTurnover={currentTurnover}
          maxTurnover={maxTurnover}
          progressPercent={progressPercent}
          thresholds={propProfile.career.thresholds}
          commissions={propProfile.career.commissions}
          currency={user.currency}
          exchangeRate={user.exchangeRate}
          isVip={user.isVip}
          onApplyPartner={onApplyPartner}
        />

        {/* System Logs & Scanner */}
        <div className="mb-12">
          <div className="bg-[#0a0a0a] border-b border-white/10 p-2 px-4 flex flex-col sm:flex-row items-center gap-6 mb-0">
            {/* Main Tabs */}
            <div className="flex items-center gap-6 overflow-x-auto w-full sm:w-auto">
              <button
                type="button"
                onClick={() => {
                  if (onHaptic) onHaptic("light");
                  setActiveTab("network");
                }}
                className={`text-[10px] font-mono font-bold uppercase flex items-center gap-2 whitespace-nowrap ${
                  activeTab === "network" ? "text-pandora-cyan" : "text-gray-600"
                }`}
              >
                {t("profile.tabs.network")}
              </button>
              <button
                type="button"
                onClick={() => {
                  if (onHaptic) onHaptic("light");
                  setActiveTab("logs");
                }}
                className={`text-[10px] font-mono font-bold uppercase whitespace-nowrap ${
                  activeTab === "logs" ? "text-pandora-cyan" : "text-gray-600"
                }`}
              >
                {t("profile.tabs.history")}
              </button>
            </div>
          </div>

          {activeTab === "network" ? (
            <ProfileNetwork
              nodes={networkTree}
              networkLine={networkLine}
              currency={user.currency || "USD"}
              exchangeRate={user.exchangeRate || 1}
              onLineChange={changeLine}
              onNodeClick={handleOpenDossier}
            />
          ) : (
            <ProfileBilling
              logs={billingLogs}
              currency={user.currency || "USD"}
              exchangeRate={user.exchangeRate || 1}
            />
          )}
        </div>
      </div>

      {/* Referral Dossier */}
      <ReferralDossier referral={selectedReferral || null} onClose={handleCloseDossier} />
    </motion.div>
  );
};

export default Profile;
