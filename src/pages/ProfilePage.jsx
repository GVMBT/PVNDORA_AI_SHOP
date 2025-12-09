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
import LoginPage from './LoginPage'
import { useApi } from '../hooks/useApi'
import { useOrders } from '../hooks/useApi'

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
  // openTelegramLink not used here; keep hook for future? remove to avoid lint
  const { request } = useApi()
  const { getOrders } = useOrders()

  // Referral network state
  const [networkTab, setNetworkTab] = useState(1)
  const [networkData, setNetworkData] = useState({ 1: [], 2: [], 3: [] })
  const [networkFetched, setNetworkFetched] = useState({ 1: false, 2: false, 3: false })
  const [networkLoading, setNetworkLoading] = useState(false)
  const [networkHasMore, setNetworkHasMore] = useState({ 1: true, 2: true, 3: true })
  const [networkError, setNetworkError] = useState(null)
  const networkDataRef = React.useRef(networkData)

  // Billing (history) state
  const [billingTab, setBillingTab] = useState('balance') // balance | bonuses | orders | withdrawals
  const [ordersList, setOrdersList] = useState([])
  const [ordersOffset, setOrdersOffset] = useState(0)
  const [ordersHasMore, setOrdersHasMore] = useState(true)
  const [ordersLoading, setOrdersLoading] = useState(false)
  const [ordersError, setOrdersError] = useState(null)
  useEffect(() => {
    networkDataRef.current = networkData
  }, [networkData])
  
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

  const formatDate = (value) => {
    if (!value) return ''
    try {
      return new Date(value).toLocaleString()
    } catch (e) {
      return value
    }
  }

  const loadOrders = useCallback(
    async (reset = false) => {
      if (ordersLoading) return
      setOrdersLoading(true)
      setOrdersError(null)
      try {
        const limit = 10
        const offset = reset ? 0 : ordersOffset
        const res = await getOrders({ limit, offset })
        const items = res?.orders || []
        setOrdersList((prev) => (reset ? items : [...prev, ...items]))
        setOrdersOffset(reset ? items.length : offset + items.length)
        setOrdersHasMore(items.length === limit)
      } catch (e) {
        console.error('orders load failed', e)
        setOrdersError(e.message || 'Failed to load orders')
        setOrdersHasMore(false)
      } finally {
        setOrdersLoading(false)
      }
    },
    [getOrders, ordersLoading, ordersOffset]
  )

  const fetchNetwork = useCallback(async (level, reset = false) => {
    if (networkLoading) return
    if (effectiveLevel < level) {
      setNetworkError(t('profile.network.locked') || 'Level locked')
      setNetworkHasMore((prev) => ({ ...prev, [level]: false }))
      setNetworkFetched((prev) => ({ ...prev, [level]: true }))
      return
    }
    setNetworkLoading(true)
    setNetworkError(null)
    try {
      const prevData = networkDataRef.current
      const offset = reset ? 0 : (prevData[level]?.length || 0)
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
      if (!items.length) {
        setNetworkHasMore((prev) => ({ ...prev, [level]: false }))
      }
      setNetworkFetched((prev) => ({ ...prev, [level]: true }))
    } catch (e) {
      console.error('referral network load failed', e)
      setNetworkError(e.message || 'Failed to load network')
      setNetworkHasMore((prev) => ({ ...prev, [level]: false }))
      setNetworkFetched((prev) => ({ ...prev, [level]: true }))
    } finally {
      setNetworkLoading(false)
    }
  }, [effectiveLevel, request, t, networkLoading])

  // Initial fetch for level 1 if unlocked (once)
  useEffect(() => {
    if (effectiveLevel >= 1 && !networkFetched[1]) {
      fetchNetwork(1, true)
    }
  }, [effectiveLevel, fetchNetwork, networkFetched])

  const handleTabChange = (level) => {
    setNetworkTab(level)
    if (!networkFetched[level] && effectiveLevel >= level) {
      fetchNetwork(level, true)
    }
  }

  // Lazy load orders when billing tab is opened
  useEffect(() => {
    if (billingTab === 'orders' && ordersList.length === 0 && !ordersLoading) {
      loadOrders(true)
    }
  }, [billingTab, loadOrders, ordersList.length, ordersLoading])

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

  const ReferralInfo = () => {
    const level2Threshold = referralProgram?.thresholds_usd?.level2 || 250
    const level3Threshold = referralProgram?.thresholds_usd?.level3 || 1000
    const c1 = referralProgram?.commissions_percent?.level1 || 20
    const c2 = referralProgram?.commissions_percent?.level2 || 10
    const c3 = referralProgram?.commissions_percent?.level3 || 5
    return (
      <div className="p-3 rounded-2xl border border-border/60 bg-card/40 space-y-1">
        <div className="text-sm font-semibold">{t('profile.referralInfo.title') || 'Как работает программа'}</div>
        <ul className="text-xs text-muted-foreground space-y-1 list-disc list-inside">
          <li>{t('profile.referralInfo.how', { l1: c1, l2: c2, l3: c3 })}</li>
          <li>{t('profile.referralInfo.unlock', { l2: level2Threshold, l3: level3Threshold })}</li>
          <li>{t('profile.referralInfo.payouts')}</li>
        </ul>
      </div>
    )
  }

  const BillingSection = () => {
    const tabs = [
      { key: 'balance', label: t('profile.billing.balanceTab') || 'Баланс' },
      { key: 'bonuses', label: t('profile.billing.bonusesTab') || 'Бонусы' },
      { key: 'orders', label: t('profile.billing.ordersTab') || 'Заказы' },
      { key: 'withdrawals', label: t('profile.billing.withdrawalsTab') || 'Выводы' },
    ]

    const renderBalance = () => (
      <div className="grid grid-cols-1 gap-2">
        <div className="p-3 rounded-2xl border border-border/60 bg-card/40 flex justify-between items-center">
          <div className="text-sm text-muted-foreground">{t('profile.billing.currentBalance') || 'Баланс'}</div>
          <div className="text-base font-semibold">{formatPrice(profile?.balance || 0, currency)}</div>
        </div>
        <div className="p-3 rounded-2xl border border-border/60 bg-card/40 flex justify-between items-center">
          <div className="text-sm text-muted-foreground">{t('profile.billing.totalReferral') || 'Заработано рефералкой'}</div>
          <div className="text-base font-semibold">{formatPrice(profile?.total_referral_earnings || 0, currency)}</div>
        </div>
        <div className="p-3 rounded-2xl border border-border/60 bg-card/40 flex justify-between items-center">
          <div className="text-sm text-muted-foreground">{t('profile.billing.totalSaved') || 'Сэкономлено'}</div>
          <div className="text-base font-semibold">{formatPrice(profile?.total_saved || 0, currency)}</div>
        </div>
      </div>
    )

    const renderBonuses = () => {
      const items = bonusHistory || []
      if (!items.length) {
        return <div className="text-sm text-muted-foreground p-3 border border-dashed border-border/60 rounded-xl">{t('profile.billing.emptyBonuses') || 'Пока нет бонусов'}</div>
      }
      return (
        <div className="space-y-2">
          {items.map((b) => (
            <div key={b.id || `${b.order_id}-${b.created_at}`} className="p-3 rounded-2xl border border-border/60 bg-card/40 flex items-center justify-between">
              <div>
                <div className="text-sm font-semibold">
                  {t('profile.billing.bonusFrom', { level: b.level || b.level_name || 'L1' })}
                </div>
                <div className="text-xs text-muted-foreground">{formatDate(b.created_at)}</div>
              </div>
              <div className="text-base font-semibold text-green-500">+{formatPrice(b.amount || b.value || 0, currency)}</div>
            </div>
          ))}
        </div>
      )
    }

    const renderWithdrawals = () => {
      const items = withdrawals || []
      if (!items.length) {
        return <div className="text-sm text-muted-foreground p-3 border border-dashed border-border/60 rounded-xl">{t('profile.billing.emptyWithdrawals') || 'Пока нет заявок'}</div>
      }
      return (
        <div className="space-y-2">
          {items.map((w) => (
            <div key={w.id || w.created_at} className="p-3 rounded-2xl border border-border/60 bg-card/40 space-y-1">
              <div className="flex items-center justify-between">
                <div className="text-sm font-semibold">{formatPrice(w.amount || 0, currency)}</div>
                <Badge variant="outline" className="text-[10px]">
                  {w.status || 'pending'}
                </Badge>
              </div>
              <div className="text-xs text-muted-foreground flex items-center gap-1">
                {getMethodIcon(w.payment_method)}
                <span>{w.payment_method || 'card'}</span>
              </div>
              <div className="text-xs text-muted-foreground">{formatDate(w.created_at)}</div>
            </div>
          ))}
        </div>
      )
    }

    const renderOrders = () => {
      if (ordersError) {
        return <div className="text-sm text-destructive p-3 border border-destructive/40 rounded-xl">{ordersError}</div>
      }
      if (ordersLoading && ordersList.length === 0) {
        return <div className="space-y-2"><Skeleton className="h-16 w-full rounded-xl" /><Skeleton className="h-16 w-full rounded-xl" /></div>
      }
      if (ordersList.length === 0) {
        return <div className="text-sm text-muted-foreground p-3 border border-dashed border-border/60 rounded-xl">{t('profile.billing.emptyOrders') || 'Пока нет заказов'}</div>
      }
      return (
        <div className="space-y-2">
          {ordersList.map((o) => (
            <div key={o.id} className="p-3 rounded-2xl border border-border/60 bg-card/40 space-y-1">
              <div className="flex items-center justify-between">
                <div className="text-sm font-semibold">{formatPrice(o.amount || 0, currency)}</div>
                <Badge variant="outline" className="text-[10px]">
                  {o.status}
                </Badge>
              </div>
              <div className="text-xs text-muted-foreground">
                {o.products?.name || o.product_name || t('profile.billing.order') || 'Заказ'} • {formatDate(o.created_at)}
              </div>
            </div>
          ))}
          {ordersHasMore && (
            <Button variant="outline" size="sm" className="w-full" disabled={ordersLoading} onClick={() => loadOrders(false)}>
              {t('profile.network.loadMore') || 'Показать ещё'}
            </Button>
          )}
          {ordersLoading && ordersList.length > 0 && (
            <div className="text-xs text-muted-foreground text-center py-1">
              {t('common.loading') || 'Загрузка...'}
            </div>
          )}
        </div>
      )
    }

    const renderTabContent = () => {
      switch (billingTab) {
        case 'bonuses': return renderBonuses()
        case 'orders': return renderOrders()
        case 'withdrawals': return renderWithdrawals()
        case 'balance':
        default:
          return renderBalance()
      }
    }

    return (
      <div className="space-y-3">
        <div className="flex items-center justify-between px-1">
          <h2 className="font-bold">{t('profile.billing.title') || 'Биллинг'}</h2>
        </div>
        <div className="flex gap-2 flex-wrap">
          {tabs.map((tab) => (
            <Button
              key={tab.key}
              variant={billingTab === tab.key ? 'default' : 'outline'}
              size="sm"
              onClick={() => setBillingTab(tab.key)}
              className="text-xs"
            >
              {tab.label}
            </Button>
          ))}
        </div>
        {renderTabContent()}
      </div>
    )
  }

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
        {networkLoading && list.length > 0 && (
          <div className="text-xs text-muted-foreground text-center py-1">
            {t('common.loading') || 'Загрузка...'}
          </div>
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
          <>
            {/* Hero / Partner block with referral link embedded */}
            <div className="bg-card/60 border border-border/50 rounded-3xl p-4 space-y-3 shadow-lg">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">
                    {t('profile.title')}
                  </p>
                  <h2 className="text-xl font-bold flex items-center gap-2">
                    Partner Dashboard
                    {isPartner && <Badge variant="secondary" className="text-[10px]">VIP</Badge>}
                  </h2>
                  <p className="text-sm text-muted-foreground">
                    {t('profile.level')}: {referralProgram?.effective_level || 1} • {t('profile.referralNetwork')}
                  </p>
                </div>
                <Badge variant="outline" className="bg-secondary/30 border-0">
                  {isPartner ? 'VIP' : `Level ${referralProgram?.effective_level || 1}`}
                </Badge>
              </div>

              <div className="grid grid-cols-2 gap-2">
                <Button variant="secondary" className="w-full" onClick={() => setWithdrawDialog(true)}>
                  {t('profile.withdraw')}
                </Button>
                <Button className="w-full" onClick={handleShare}>
                  {t('profile.invite')}
                </Button>
              </div>

              {/* Referral link inline */}
              <CopyReferralLink userId={user?.id} t={t} onCopy={handleCopyLink} />
            </div>

            {/* Referral Program info + metrics */}
            <div className="space-y-3">
              <div className="flex items-center justify-between px-1">
                <h2 className="font-bold flex items-center gap-2">
                  <Trophy className="h-5 w-5 text-yellow-500" />
                  {t('profile.referralNetwork')}
                </h2>
                <Badge variant="outline" className="bg-secondary/30 border-0">
                  {isPartner ? 'VIP' : `Level ${referralProgram?.effective_level || 1}`}
                </Badge>
              </div>
              <ReferralInfo />
              <ReferralStatsGrid referralStats={referralStats} currency={currency} formatPrice={formatPrice} t={t} />
            </div>

            {/* Referral Network for partners */}
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
        ) : (
          <>
            {/* Single colored card with balance + actions + referral link */}
            <BalanceCard
              balance={profile?.balance || 0}
              currency={currency}
              formatPrice={formatPrice}
              t={t}
              onWithdraw={() => setWithdrawDialog(true)}
              onShare={handleShare}
              shareLoading={shareLoading}
              minWithdrawal={WITHDRAWAL_MIN}
              referralSlot={<CopyReferralLink userId={user?.id} t={t} onCopy={handleCopyLink} />}
            />

            {/* Referral program info */}
            <ReferralInfo />

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

            {/* Metrics under referral program */}
            <ReferralStatsGrid referralStats={referralStats} currency={currency} formatPrice={formatPrice} t={t} />

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

        {/* Billing embedded in profile */}
        <BillingSection />
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
