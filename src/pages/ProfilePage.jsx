import React, { useEffect, useState, useCallback } from 'react'
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
// import { useTelegram } from '../hooks/useTelegram'
import LoginPage from './LoginPage'
import { useApi } from '../hooks/useApi'

const WITHDRAWAL_MIN = 500

export default function ProfilePage({ onBack }) {
  const {
    loading,
    profile,
    error,
    currency,
    referralStats,
    referralProgram,
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
  // openTelegramLink not used here; keep hook for future? remove to avoid lint
  const { request } = useApi()

  // Referral network state
  const [networkTab, setNetworkTab] = useState(1)
  const [networkData, setNetworkData] = useState({ 1: [], 2: [], 3: [] })
  const [networkLoading, setNetworkLoading] = useState(false)
  const [networkHasMore, setNetworkHasMore] = useState({ 1: true, 2: true, 3: true })
  const [networkError, setNetworkError] = useState(null)
  
  const getMethodIcon = (method) => {
    switch (method) {
      case 'card': return <CreditCard className="h-4 w-4" />
      case 'phone': return <Smartphone className="h-4 w-4" />
      case 'crypto': return <Bitcoin className="h-4 w-4" />
      default: return <Wallet className="h-4 w-4" />
    }
  }
  
  const isPartner = profile?.is_partner || referralProgram?.is_partner
  const effectiveLevel = referralProgram?.effective_level || 0

  const fetchNetwork = useCallback(async (level, reset = false) => {
    if (networkLoading) return
    if (effectiveLevel < level) {
      setNetworkError(t('profile.network.locked') || 'Level locked')
      return
    }
    setNetworkLoading(true)
    setNetworkError(null)
    try {
      const offset = reset ? 0 : (networkData[level]?.length || 0)
      const data = await request(`/referral/network?level=${level}&limit=20&offset=${offset}`)
      const items = data?.referrals || []
      setNetworkData((prev) => ({
        ...prev,
        [level]: reset ? items : [...(prev[level] || []), ...items],
      }))
      setNetworkHasMore((prev) => ({
        ...prev,
        [level]: items.length === 20,
      }))
    } catch (e) {
      setNetworkError(e.message || 'Failed to load network')
    } finally {
      setNetworkLoading(false)
    }
  }, [effectiveLevel, networkData, networkLoading, request, t])

  // Initial fetch for level 1 if unlocked
  useEffect(() => {
    if (effectiveLevel >= 1) {
      fetchNetwork(1, true)
    }
  }, [effectiveLevel, fetchNetwork])

  const handleTabChange = (level) => {
    setNetworkTab(level)
    if (networkData[level]?.length === 0 && effectiveLevel >= level) {
      fetchNetwork(level, true)
    }
  }

  // Fallback views (no hooks below this point)
  let fallback = null
  if (loading && !profile) {
    fallback = (
      <div className="p-4 space-y-4">
        <Skeleton className="h-48 w-full rounded-3xl" />
        <Skeleton className="h-32 w-full rounded-2xl" />
        <Skeleton className="h-64 w-full rounded-2xl" />
      </div>
    )
  } else if ((error === 'unauthorized' || !user?.id) && !profile && !loading) {
    fallback = (
      <LoginPage
        onLogin={() => window.location.reload()}
        botUsername="pvndora_ai_bot"
      />
    )
  } else if (!loading && error && !profile) {
    fallback = (
      <div className="p-4 space-y-4">
        <HeaderBar title={t('profile.title')} onBack={onBack} />
        <div className="p-4 rounded-xl border border-destructive/30 bg-destructive/5 text-destructive">
          {error}
        </div>
        <Button onClick={() => window.location.reload()}>{t('common.retry') || 'Повторить'}</Button>
      </div>
    )
  }

  if (fallback) return fallback

  const NetworkList = ({ level }) => {
    const list = networkData[level] || []
    const locked = effectiveLevel < level

    if (locked) {
      return (
        <div className="p-4 border border-dashed border-border/60 rounded-xl text-sm text-muted-foreground">
          {t('profile.network.locked') || 'Уровень не открыт'}
        </div>
      )
    }

    if (networkError) {
      return (
        <div className="p-4 border border-dashed border-destructive/40 rounded-xl text-sm text-destructive">
          {networkError}
        </div>
      )
    }

    if (networkLoading && list.length === 0) {
      return (
        <div className="space-y-2">
          <Skeleton className="h-12 w-full rounded-xl" />
          <Skeleton className="h-12 w-full rounded-xl" />
        </div>
      )
    }

    if (list.length === 0) {
      return (
        <div className="p-4 border border-dashed border-border/60 rounded-xl text-sm text-muted-foreground">
          {t('profile.network.empty') || 'Пока нет рефералов'}
        </div>
      )
    }

    return (
      <div className="space-y-2">
        {list.map((ref) => {
          const isActive = ref.is_active
          return (
            <div
              key={ref.id}
              className="flex items-center justify-between gap-3 p-3 rounded-xl border border-border/60 bg-card/40"
            >
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-semibold truncate">
                    {ref.username ? (
                      <a
                        href={`https://t.me/${ref.username}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary hover:underline"
                      >
                        @{ref.username}
                      </a>
                    ) : (
                      ref.first_name || `#${ref.telegram_id}`
                    )}
                  </span>
                  <Badge variant={isActive ? 'default' : 'secondary'} className="text-[10px]">
                    {isActive ? (t('profile.network.active') || 'Активен') : (t('profile.network.inactive') || 'Не активен')}
                  </Badge>
                </div>
                <div className="text-xs text-muted-foreground mt-0.5 flex gap-3">
                  <span>{t('profile.network.orders') || 'Заказов'}: {ref.order_count || 0}</span>
                  <span>{t('profile.network.earned') || 'Заработано для вас'}: {ref.earnings_generated?.toFixed(2) || '0.00'}</span>
                </div>
              </div>
            </div>
          )
        })}

        {networkHasMore[level] && (
          <Button
            variant="outline"
            size="sm"
            className="w-full"
            onClick={() => fetchNetwork(level, false)}
            disabled={networkLoading}
          >
            {t('profile.network.loadMore') || 'Показать ещё'}
          </Button>
        )}
      </div>
    )
  }
  
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

            {/* Referral Network */}
            <div className="space-y-3">
              <div className="flex items-center justify-between px-1">
                <h2 className="font-bold flex items-center gap-2">
                  {t('profile.network.title') || 'Моя сеть'}
                </h2>
                <div className="flex gap-2">
                  {[1, 2, 3].map((lvl) => (
                    <Button
                      key={lvl}
                      variant={networkTab === lvl ? 'default' : 'outline'}
                      size="sm"
                      disabled={effectiveLevel < lvl}
                      onClick={() => handleTabChange(lvl)}
                      className="text-xs"
                    >
                      {t('profile.network.level', { level: lvl }) || `L${lvl}`}
                    </Button>
                  ))}
                </div>
              </div>

              <NetworkList level={networkTab} />
            </div>
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
