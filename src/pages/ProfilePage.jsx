import React, { useEffect, useState, useCallback, useRef } from 'react'
import { CreditCard, Smartphone, Bitcoin, Wallet, Trophy, Info } from 'lucide-react'
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
import { useApi, useOrders } from '../hooks/useApi'

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

  const { request } = useApi()
  const { getOrders } = useOrders()

  // --- State for Referral Network ---
  const [networkTab, setNetworkTab] = useState(1)
  const [networkData, setNetworkData] = useState({ 1: [], 2: [], 3: [] })
  const [networkFetched, setNetworkFetched] = useState({ 1: false, 2: false, 3: false })
  const [networkLoading, setNetworkLoading] = useState(false)
  const [networkHasMore, setNetworkHasMore] = useState({ 1: true, 2: true, 3: true })
  const [networkError, setNetworkError] = useState(null)
  const networkDataRef = useRef(networkData)

  // --- State for Billing (Orders) ---
  const [billingTab, setBillingTab] = useState('balance') // balance | bonuses | orders | withdrawals
  const [ordersList, setOrdersList] = useState([])
  const [ordersOffset, setOrdersOffset] = useState(0)
  const [ordersHasMore, setOrdersHasMore] = useState(true)
  const [ordersLoading, setOrdersLoading] = useState(false)
  const [ordersError, setOrdersError] = useState(null)

  // Keep ref updated
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

  // --- Network Fetch Logic ---
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

  // Initial network fetch L1
  useEffect(() => {
    if (effectiveLevel >= 1 && !networkFetched[1]) {
      fetchNetwork(1, true)
    }
  }, [effectiveLevel, fetchNetwork, networkFetched])

  const handleNetworkTabChange = (level) => {
    setNetworkTab(level)
    if (!networkFetched[level] && effectiveLevel >= level) {
      fetchNetwork(level, true)
    }
  }

  // --- Orders Fetch Logic ---
  const loadOrders = useCallback(async (reset = false) => {
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
  }, [getOrders, ordersLoading, ordersOffset])

  // Initial orders fetch when tab active
  useEffect(() => {
    if (billingTab === 'orders' && ordersList.length === 0 && !ordersLoading) {
      loadOrders(true)
    }
  }, [billingTab, loadOrders, ordersList.length, ordersLoading])

  // --- Render Helpers ---

  // 1. Fallback / Loading / Error
  if (loading && !profile) {
    return (
      <div className="p-4 space-y-4">
        <Skeleton className="h-48 w-full rounded-3xl" />
        <Skeleton className="h-32 w-full rounded-2xl" />
        <Skeleton className="h-64 w-full rounded-2xl" />
      </div>
    )
  }
  
  if ((error === 'unauthorized' || !user?.id) && !profile && !loading) {
    return (
      <LoginPage
        onLogin={() => window.location.reload()}
        botUsername="pvndora_ai_bot"
      />
    )
  }
  
  if (!loading && error && !profile) {
    return (
      <div className="p-4 space-y-4">
        <HeaderBar title={t('profile.title')} onBack={onBack} />
        <div className="p-4 rounded-xl border border-destructive/30 bg-destructive/5 text-destructive">
          {error}
        </div>
        <Button onClick={() => window.location.reload()}>{t('common.retry') || 'Повторить'}</Button>
      </div>
    )
  }

  // 2. Info Block
  const ReferralInfoBlock = () => {
    const level2Threshold = referralProgram?.thresholds_usd?.level2 || 250
    const level3Threshold = referralProgram?.thresholds_usd?.level3 || 1000
    const c1 = referralProgram?.commissions_percent?.level1 || 20
    const c2 = referralProgram?.commissions_percent?.level2 || 10
    const c3 = referralProgram?.commissions_percent?.level3 || 5
    return (
      <div className="bg-card/40 border border-border/60 rounded-2xl p-4 space-y-2">
         <div className="flex items-center gap-2 text-sm font-semibold">
           <Info className="h-4 w-4 text-primary" />
           {t('profile.referralInfo.title') || 'Как работает программа'}
         </div>
         <ul className="text-xs text-muted-foreground space-y-1 list-disc list-inside pl-1">
           <li>{t('profile.referralInfo.how', { l1: c1, l2: c2, l3: c3 })}</li>
           <li>{t('profile.referralInfo.unlock', { l2: level2Threshold, l3: level3Threshold })}</li>
           <li>{t('profile.referralInfo.payouts')}</li>
         </ul>
      </div>
    )
  }

  // 3. Network List
  const NetworkListView = () => {
    const list = networkData[networkTab] || []
    const locked = effectiveLevel < networkTab

    if (locked) {
      return (
        <div className="p-8 border border-dashed border-border/60 rounded-xl text-center text-sm text-muted-foreground">
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
        <div className="p-8 border border-dashed border-border/60 rounded-xl text-center text-sm text-muted-foreground">
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
                  <span>{t('profile.network.earned') || 'Вам'}: {ref.earnings_generated?.toFixed(2) || '0.00'}</span>
                </div>
              </div>
            </div>
          )
        })}

        {networkHasMore[networkTab] && (
          <Button
            variant="ghost"
            size="sm"
            className="w-full text-xs text-muted-foreground"
            onClick={() => fetchNetwork(networkTab, false)}
            disabled={networkLoading}
          >
            {networkLoading ? (t('common.loading') || 'Загрузка...') : (t('profile.network.loadMore') || 'Показать ещё')}
          </Button>
        )}
      </div>
    )
  }

  // 4. Billing Views
  const renderBalanceView = () => (
    <div className="space-y-2">
      <div className="p-4 rounded-2xl border border-border/60 bg-card/40 flex justify-between items-center">
        <div className="text-sm text-muted-foreground">{t('profile.billing.currentBalance') || 'Баланс'}</div>
        <div className="text-lg font-bold">{formatPrice(profile?.balance || 0, currency)}</div>
      </div>
      <div className="p-4 rounded-2xl border border-border/60 bg-card/40 flex justify-between items-center">
        <div className="text-sm text-muted-foreground">{t('profile.billing.totalReferral') || 'Заработано рефералкой'}</div>
        <div className="text-base font-semibold">{formatPrice(profile?.total_referral_earnings || 0, currency)}</div>
      </div>
      <div className="p-4 rounded-2xl border border-border/60 bg-card/40 flex justify-between items-center">
        <div className="text-sm text-muted-foreground">{t('profile.billing.totalSaved') || 'Сэкономлено'}</div>
        <div className="text-base font-semibold">{formatPrice(profile?.total_saved || 0, currency)}</div>
      </div>
    </div>
  )

  const renderBonusesView = () => {
    const items = bonusHistory || []
    if (!items.length) {
      return <div className="p-8 text-center text-sm text-muted-foreground border border-dashed border-border/60 rounded-xl">{t('profile.billing.emptyBonuses') || 'Пока нет бонусов'}</div>
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

  const renderWithdrawalsView = () => {
    const items = withdrawals || []
    if (!items.length) {
      return <div className="p-8 text-center text-sm text-muted-foreground border border-dashed border-border/60 rounded-xl">{t('profile.billing.emptyWithdrawals') || 'Пока нет заявок'}</div>
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
            <div className="flex items-center justify-between text-xs text-muted-foreground">
              <div className="flex items-center gap-1">
                {getMethodIcon(w.payment_method)}
                <span>{w.payment_method || 'card'}</span>
              </div>
              <div>{formatDate(w.created_at)}</div>
            </div>
          </div>
        ))}
      </div>
    )
  }

  const renderOrdersView = () => {
    if (ordersError) {
      return <div className="text-sm text-destructive p-3 border border-destructive/40 rounded-xl">{ordersError}</div>
    }
    if (ordersList.length === 0 && !ordersLoading) {
      return <div className="p-8 text-center text-sm text-muted-foreground border border-dashed border-border/60 rounded-xl">{t('profile.billing.emptyOrders') || 'Пока нет заказов'}</div>
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
           <Button variant="ghost" size="sm" className="w-full text-xs text-muted-foreground" disabled={ordersLoading} onClick={() => loadOrders(false)}>
              {ordersLoading ? (t('common.loading') || 'Загрузка...') : (t('profile.network.loadMore') || 'Показать ещё')}
           </Button>
        )}
      </div>
    )
  }

  // --- Main Render ---
  return (
    <div className="min-h-screen bg-background relative pb-safe">
      {/* Background Gradient */}
      <div className="fixed inset-0 bg-[radial-gradient(ellipse_at_top_right,_var(--tw-gradient-stops))] from-purple-500/10 via-background to-background pointer-events-none z-0" />

      <HeaderBar title={t('profile.title')} onBack={onBack} className="z-20 relative" />
      
      <div className="px-4 pb-12 space-y-8 relative z-10 max-w-md mx-auto">
        
        {/* 1. User Info Header */}
        <UserInfo user={user} isPartner={isPartner} />

        {/* 2. Balance / Actions Card */}
        {isPartner ? (
           <div className="bg-card/60 border border-border/50 rounded-3xl p-5 space-y-4 shadow-sm backdrop-blur-xl">
             <div className="flex items-center justify-between">
               <div>
                 <p className="text-xs text-muted-foreground uppercase tracking-wider mb-1">
                   {t('profile.title')}
                 </p>
                 <h2 className="text-2xl font-bold flex items-center gap-2">
                   Partner
                   <Badge variant="secondary" className="text-[10px] bg-yellow-500/10 text-yellow-500 border-yellow-500/20">VIP</Badge>
                 </h2>
               </div>
               <div className="text-right">
                 <div className="text-2xl font-bold">{formatPrice(profile?.balance || 0, currency)}</div>
               </div>
             </div>

             <div className="grid grid-cols-2 gap-3">
               <Button variant="secondary" className="w-full h-10" onClick={() => setWithdrawDialog(true)}>
                 {t('profile.withdraw')}
               </Button>
               <Button className="w-full h-10" onClick={handleShare}>
                 {t('profile.invite')}
               </Button>
             </div>
             
             <div className="pt-2 border-t border-border/40">
                <CopyReferralLink userId={user?.id} t={t} onCopy={handleCopyLink} />
             </div>
           </div>
        ) : (
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
        )}

        {/* 3. Referral Program Section */}
        <section className="space-y-4">
           <div className="flex items-center justify-between px-1">
             <h3 className="font-bold text-lg flex items-center gap-2">
               <Trophy className="h-5 w-5 text-yellow-500" />
               {t('profile.referralNetwork')}
             </h3>
             <Badge variant="outline" className="bg-secondary/30 border-0">
                Level {referralProgram?.effective_level || 1}
             </Badge>
           </div>
           
           <ReferralInfoBlock />
           
           {/* Level Cards */}
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

           {/* Metrics */}
           <div className="pt-2">
              <ReferralStatsGrid referralStats={referralStats} currency={currency} formatPrice={formatPrice} t={t} />
           </div>
        </section>

        {/* 4. Network List Section */}
        <section className="space-y-4">
           <div className="flex items-center justify-between px-1">
             <h3 className="font-bold text-lg">{t('profile.network.title') || 'Моя сеть'}</h3>
             <div className="flex bg-secondary/20 p-1 rounded-lg">
               {[1, 2, 3].map((lvl) => (
                 <button
                   key={lvl}
                   onClick={() => handleNetworkTabChange(lvl)}
                   disabled={effectiveLevel < lvl}
                   className={`
                     px-3 py-1 rounded-md text-xs font-medium transition-all
                     ${networkTab === lvl ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground'}
                     ${effectiveLevel < lvl ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
                   `}
                 >
                   L{lvl}
                 </button>
               ))}
             </div>
           </div>
           
           <NetworkListView />
        </section>

        {/* 5. Billing Section */}
        <section className="space-y-4 pt-4 border-t border-border/40">
           <h3 className="font-bold text-lg px-1">{t('profile.billing.title') || 'Биллинг'}</h3>
           
           {/* Custom Tab Switcher */}
           <div className="flex p-1 bg-secondary/20 rounded-xl overflow-x-auto no-scrollbar gap-1">
             {[
               { id: 'balance', label: t('profile.billing.balanceTab') || 'Баланс' },
               { id: 'bonuses', label: t('profile.billing.bonusesTab') || 'Бонусы' },
               { id: 'orders', label: t('profile.billing.ordersTab') || 'Заказы' },
               { id: 'withdrawals', label: t('profile.billing.withdrawalsTab') || 'Выводы' },
             ].map((tab) => (
               <button
                 key={tab.id}
                 onClick={() => setBillingTab(tab.id)}
                 className={`
                   flex-1 px-3 py-2 rounded-lg text-xs font-medium whitespace-nowrap transition-all
                   ${billingTab === tab.id ? 'bg-background shadow-sm text-foreground' : 'text-muted-foreground hover:text-foreground'}
                 `}
               >
                 {tab.label}
               </button>
             ))}
           </div>

           <div className="min-h-[150px]">
             {billingTab === 'balance' && renderBalanceView()}
             {billingTab === 'bonuses' && renderBonusesView()}
             {billingTab === 'orders' && renderOrdersView()}
             {billingTab === 'withdrawals' && renderWithdrawalsView()}
           </div>
        </section>

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
