import React from 'react'
import PartnerDashboard from '../components/PartnerDashboard'
import { CreditCard, Smartphone, Bitcoin, Wallet, Trophy } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Skeleton } from '../components/ui/skeleton'
import { HeaderBar } from '../components/ui/header-bar'
import { Badge } from '../components/ui/badge'
import { useProfileData } from '../hooks/useProfileData'
import LevelCard from '../components/profile/LevelCard'
import UserInfo from '../components/profile/UserInfo'
import BalanceCard from '../components/profile/BalanceCard'
import ReferralStatsGrid from '../components/profile/ReferralStatsGrid'
import CopyReferralLink from '../components/profile/CopyReferralLink'
import WithdrawDialog from '../components/profile/WithdrawDialog'
import { useTelegram } from '../hooks/useTelegram'
import LoginPage from './LoginPage'

const WITHDRAWAL_MIN = 500

export default function ProfilePage({ onBack }) {
  const {
    loading,
    profile,
    error,
    currency,
    referralStats,
    referralProgram,
    bonusHistory,
    withdrawals,
    withdrawDialog,
    setWithdrawDialog,
    shareLoading,
    withdrawAmount,
    setWithdrawAmount,
    withdrawMethod,
    setWithdrawMethod,
    withdrawDetails,
    setWithdrawDetails,
    submitting,
    handleCopyLink,
    handleShare,
    handleWithdraw,
    formatPrice,
    t,
    user,
  } = useProfileData({ onBack })
  const { openTelegramLink } = useTelegram()
  
  const getMethodIcon = (method) => {
    switch (method) {
      case 'card': return <CreditCard className="h-4 w-4" />
      case 'phone': return <Smartphone className="h-4 w-4" />
      case 'crypto': return <Bitcoin className="h-4 w-4" />
      default: return <Wallet className="h-4 w-4" />
    }
  }
  
  if ((error === 'unauthorized' || !user?.id) && !profile) {
    return (
      <LoginPage
        onLogin={() => window.location.reload()}
        botUsername="pvndora_ai_bot"
      />
    )
  }

  if (loading && !profile) {
    return (
      <div className="p-4 space-y-4">
        <Skeleton className="h-48 w-full rounded-3xl" />
        <Skeleton className="h-32 w-full rounded-2xl" />
        <Skeleton className="h-64 w-full rounded-2xl" />
      </div>
    )
  }
  
  const isPartner = profile?.is_partner || referralProgram?.is_partner
  
  return (
    <div className="bg-background relative">
      {/* Ambient Background */}
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-purple-500/10 via-background to-background pointer-events-none z-0" />

      <HeaderBar title={t('profile.title')} onBack={onBack} className="z-20" />
      
      <div className="px-4 space-y-6 relative z-10">
        
        <UserInfo user={user} isPartner={isPartner} />

        {isPartner ? (
          <PartnerDashboard 
            profile={profile}
            referralLink={`https://t.me/pvndora_ai_bot?start=ref_${user?.id}`}
            onWithdraw={() => setWithdrawDialog(true)}
            onShare={handleShare}
          />
        ) : (
          <>
            <BalanceCard
              balance={profile?.balance || 0}
              currency={currency}
              formatPrice={formatPrice}
              t={t}
              onWithdraw={() => setWithdrawDialog(true)}
              onShare={handleShare}
              shareLoading={shareLoading}
              minWithdrawal={WITHDRAWAL_MIN}
            />

            <ReferralStatsGrid referralStats={referralStats} currency={currency} formatPrice={formatPrice} />

            {/* Gamification Levels */}
            <div className="space-y-4">
               <div className="flex items-center justify-between px-1">
                 <h2 className="font-bold flex items-center gap-2">
                   <Trophy className="h-5 w-5 text-yellow-500" />
                   {t('profile.referralNetwork')}
                 </h2>
                 <Badge variant="outline" className="bg-secondary/30 border-0">
                    Level {referralProgram?.effective_level || 1}
                 </Badge>
               </div>
               
               <div className="space-y-3">
                  <LevelCard 
                    level={1}
                    commission={`${referralProgram?.commissions_percent?.level1 || 20}%`}
                    threshold={0}
                    isUnlocked={referralProgram?.level1_unlocked}
                    isProgramLocked={referralProgram?.status === 'locked'}
                    count={referralStats?.level1_count || 0}
                    earnings={referralStats?.level1_earnings || 0}
                    formatPrice={formatPrice}
                    t={t}
                    color="green"
                    isInstant={true}
                  />
                  <LevelCard 
                    level={2}
                    commission={`${referralProgram?.commissions_percent?.level2 || 10}%`}
                    threshold={referralProgram?.thresholds_usd?.level2 || 250}
                    isUnlocked={referralProgram?.level2_unlocked}
                    isProgramLocked={referralProgram?.status === 'locked'}
                    count={referralStats?.level2_count || 0}
                    earnings={referralStats?.level2_earnings || 0}
                    formatPrice={formatPrice}
                    t={t}
                    color="blue"
                  />
                  <LevelCard 
                    level={3}
                    commission={`${referralProgram?.commissions_percent?.level3 || 5}%`}
                    threshold={referralProgram?.thresholds_usd?.level3 || 1000}
                    isUnlocked={referralProgram?.level3_unlocked}
                    isProgramLocked={referralProgram?.status === 'locked'}
                    count={referralStats?.level3_count || 0}
                    earnings={referralStats?.level3_earnings || 0}
                    formatPrice={formatPrice}
                    t={t}
                    color="purple"
                  />
               </div>
            </div>
            
            <CopyReferralLink userId={user?.id} t={t} onCopy={handleCopyLink} />
          </>
        )}
      </div>

      <WithdrawDialog
        open={withdrawDialog}
        onOpenChange={setWithdrawDialog}
        t={t}
        formatPrice={formatPrice}
        currency={currency}
        profile={profile}
        withdrawAmount={withdrawAmount}
        setWithdrawAmount={setWithdrawAmount}
        withdrawMethod={withdrawMethod}
        setWithdrawMethod={setWithdrawMethod}
        withdrawDetails={withdrawDetails}
        setWithdrawDetails={setWithdrawDetails}
        submitting={submitting}
        handleWithdraw={handleWithdraw}
        getMethodIcon={getMethodIcon}
        minWithdrawal={WITHDRAWAL_MIN}
      />
    </div>
  )
}
