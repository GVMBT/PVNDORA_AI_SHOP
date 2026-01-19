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
    if (onHaptic) {
      onHaptic("light");
    }
    if (onCopyLink) {
      onCopyLink();
    } else if (propProfile?.referralLink) {
      await copyToClipboard(propProfile.referralLink);
    }
  }, [onHaptic, onCopyLink, propProfile?.referralLink, copyToClipboard]);

  const handleShare = useCallback(async () => {
    if (onHaptic) {
      onHaptic("medium");
    }

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
      <div className="relative min-h-screen px-4 pt-20 pb-32 text-white md:px-8 md:pt-24 md:pl-28">
        <div className="mx-auto max-w-7xl">
          <button
            className="mb-4 flex items-center gap-2 font-mono text-[10px] text-gray-500 transition-colors hover:text-pandora-cyan"
            onClick={onBack}
            type="button"
          >
            <ArrowLeft size={12} /> {t("empty.returnToBase").toUpperCase()}
          </button>
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <User className="mb-6 text-gray-700" size={64} />
            <h2 className="mb-2 font-bold text-2xl text-white">
              {t("empty.profile").toUpperCase()}
            </h2>
            <p className="max-w-md font-mono text-gray-500 text-sm">{t("empty.profileHint")}</p>
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
    if (onHaptic) {
      onHaptic("light");
    }
    setNetworkLine(line);
  };

  const handleOpenDossier = (id: number | string) => {
    if (onHaptic) {
      onHaptic("medium");
    }
    AudioEngine.decrypt(); // Play decrypt sound for dossier reveal
    setSelectedReferralId(id);
  };

  const handleCloseDossier = () => {
    if (onHaptic) {
      onHaptic("light");
    }
    AudioEngine.panelClose();
    setSelectedReferralId(null);
  };

  const toggleRewardMode = async () => {
    if (!user.isVip) {
      return; // VIP only
    }
    if (onHaptic) {
      onHaptic("medium");
    }

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
      animate={{ opacity: 1 }}
      className="relative min-h-screen px-4 pt-20 pb-32 text-white md:px-8 md:pt-24 md:pl-28"
      exit={{ opacity: 0 }}
      initial={{ opacity: 0 }}
    >
      <div className="relative z-10 mx-auto max-w-7xl">
        <ProfileHeader
          onAdminEnter={onAdminEnter}
          onBack={onBack}
          onStudioEnter={onStudioEnter}
          user={user}
        />

        <ProfileStats
          copied={copied}
          onCancelWithdrawal={onCancelWithdrawal}
          onCopy={handleCopy}
          onHaptic={onHaptic}
          onShare={handleShare}
          onToggleRewardMode={toggleRewardMode}
          onTopUp={onTopUp}
          onUpdatePreferences={onUpdatePreferences}
          onWithdraw={onWithdraw}
          rewardMode={rewardMode}
          user={user}
        />

        <ProfileCareer
          commissions={propProfile.career.commissions}
          currency={user.currency}
          currentLevel={currentLevel}
          currentTurnover={currentTurnover}
          exchangeRate={user.exchangeRate}
          isVip={user.isVip}
          maxTurnover={maxTurnover}
          nextLevel={nextLevel}
          onApplyPartner={onApplyPartner}
          progressPercent={progressPercent}
          thresholds={propProfile.career.thresholds}
        />

        {/* System Logs & Scanner */}
        <div className="mb-12">
          <div className="mb-0 flex flex-col items-center gap-6 border-white/10 border-b bg-[#0a0a0a] p-2 px-4 sm:flex-row">
            {/* Main Tabs */}
            <div className="flex w-full items-center gap-6 overflow-x-auto sm:w-auto">
              <button
                className={`flex items-center gap-2 whitespace-nowrap font-bold font-mono text-[10px] uppercase ${
                  activeTab === "network" ? "text-pandora-cyan" : "text-gray-600"
                }`}
                onClick={() => {
                  if (onHaptic) {
                    onHaptic("light");
                  }
                  setActiveTab("network");
                }}
                type="button"
              >
                {t("profile.tabs.network")}
              </button>
              <button
                className={`whitespace-nowrap font-bold font-mono text-[10px] uppercase ${
                  activeTab === "logs" ? "text-pandora-cyan" : "text-gray-600"
                }`}
                onClick={() => {
                  if (onHaptic) {
                    onHaptic("light");
                  }
                  setActiveTab("logs");
                }}
                type="button"
              >
                {t("profile.tabs.history")}
              </button>
            </div>
          </div>

          {activeTab === "network" ? (
            <ProfileNetwork
              currency={user.currency || "USD"}
              exchangeRate={user.exchangeRate || 1}
              networkLine={networkLine}
              nodes={networkTree}
              onLineChange={changeLine}
              onNodeClick={handleOpenDossier}
            />
          ) : (
            <ProfileBilling
              currency={user.currency || "USD"}
              exchangeRate={user.exchangeRate || 1}
              logs={billingLogs}
            />
          )}
        </div>
      </div>

      {/* Referral Dossier */}
      <ReferralDossier onClose={handleCloseDossier} referral={selectedReferral || null} />
    </motion.div>
  );
};

export default Profile;
