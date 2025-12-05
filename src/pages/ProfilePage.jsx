import React, { useState, useEffect, useCallback } from 'react'
import { useApi } from '../hooks/useApi'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'
import PartnerDashboard from '../components/PartnerDashboard'
import { 
  ArrowLeft, 
  Wallet, 
  Users, 
  TrendingUp, 
  Copy, 
  Share2, 
  Gift,
  CheckCircle,
  XCircle,
  AlertCircle,
  CreditCard,
  Smartphone,
  Bitcoin,
  Lock,
  DollarSign,
  Star,
  Trophy
} from 'lucide-react'
import { Button } from '../components/ui/button'
import { Card, CardContent } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Skeleton } from '../components/ui/skeleton'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '../components/ui/dialog'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { motion } from 'framer-motion'
import { cn } from '../lib/utils'

const WITHDRAWAL_MIN = 500 

function LevelCard({ level, commission, threshold, isUnlocked, isProgramLocked, count, earnings, formatPrice, t, color, isInstant }) {
  const isLocked = !isUnlocked
  
  const colors = {
    green: {
      gradient: 'from-emerald-500/20 to-teal-500/5',
      border: 'border-emerald-500/20',
      text: 'text-emerald-500',
      bg: 'bg-emerald-500/10',
      shadow: 'shadow-emerald-500/10'
    },
    blue: {
      gradient: 'from-blue-500/20 to-indigo-500/5',
      border: 'border-blue-500/20',
      text: 'text-blue-500',
      bg: 'bg-blue-500/10',
      shadow: 'shadow-blue-500/10'
    },
    purple: {
      gradient: 'from-purple-500/20 to-fuchsia-500/5',
      border: 'border-purple-500/20',
      text: 'text-purple-500',
      bg: 'bg-purple-500/10',
      shadow: 'shadow-purple-500/10'
    }
  }
  
  const cfg = colors[color]
  
  return (
    <motion.div
      whileHover={{ scale: isLocked ? 1 : 1.02 }}
      whileTap={{ scale: isLocked ? 1 : 0.98 }}
      className={cn(
        "relative overflow-hidden rounded-2xl border p-4 transition-all duration-300",
        isLocked 
          ? "bg-card/30 border-white/5 grayscale opacity-60" 
          : `bg-gradient-to-br ${cfg.gradient} ${cfg.border} shadow-lg ${cfg.shadow}`
      )}
    >
       {/* Background Pattern */}
       <div className="absolute inset-0 bg-[url('/noise.png')] opacity-10 mix-blend-overlay pointer-events-none" />
       
       <div className="flex justify-between items-start relative z-10">
          <div className="flex gap-3">
             <div className={cn("w-10 h-10 rounded-xl flex items-center justify-center font-bold text-lg shadow-inner", isLocked ? "bg-white/5 text-muted-foreground" : `${cfg.bg} ${cfg.text}`)}>
               {isLocked ? <Lock className="w-4 h-4" /> : level}
             </div>
             <div>
                <h3 className="font-bold text-sm">{t(`profile.level${level}`)}</h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  {isUnlocked ? `${commission} ${t('profile.commission')}` : isInstant ? t('profile.unlockOnPurchase') : `${t('profile.unlockAt')} $${threshold}`}
                </p>
             </div>
          </div>
          
          <div className="text-right">
             <div className="text-xl font-bold font-mono tracking-tight">{count}</div>
             <div className={cn("text-[10px] font-medium", isLocked ? "text-muted-foreground" : cfg.text)}>
               {isUnlocked && earnings > 0 ? `+${formatPrice(earnings)}` : 'Referrals'}
             </div>
          </div>
       </div>
       
       {/* Progress Bar for Locked Levels */}
       {!isUnlocked && !isInstant && !isProgramLocked && (
         <div className="mt-3 h-1 bg-white/5 rounded-full overflow-hidden">
           <div className="h-full bg-white/20 w-1/3" /> 
         </div>
       )}
    </motion.div>
  )
}

export default function ProfilePage({ onBack }) {
  const { get, post, loading } = useApi()
  const { t, formatPrice } = useLocale()
  const { setBackButton, user, showPopup, hapticFeedback } = useTelegram()
  
  const [profile, setProfile] = useState(null)
  const [currency, setCurrency] = useState('USD')
  const [referralStats, setReferralStats] = useState(null)
  const [referralProgram, setReferralProgram] = useState(null)
  const [bonusHistory, setBonusHistory] = useState([])
  const [withdrawals, setWithdrawals] = useState([])
  const [withdrawDialog, setWithdrawDialog] = useState(false)
  const [shareLoading, setShareLoading] = useState(false)
  const [withdrawAmount, setWithdrawAmount] = useState('')
  const [withdrawMethod, setWithdrawMethod] = useState('card')
  const [withdrawDetails, setWithdrawDetails] = useState('')
  const [submitting, setSubmitting] = useState(false)
  
  const loadProfile = useCallback(async () => {
    try {
      const data = await get('/profile')
      setProfile(data.profile)
      setCurrency(data.currency || 'USD')
      setReferralStats(data.referral_stats)
      setReferralProgram(data.referral_program)
      setBonusHistory(data.bonus_history || [])
      setWithdrawals(data.withdrawals || [])
    } catch (err) {
      console.error('Failed to load profile:', err)
    }
  }, [get])
  
  useEffect(() => {
    loadProfile()
    setBackButton({ isVisible: true, onClick: onBack })
    return () => setBackButton({ isVisible: false })
  }, [loadProfile, onBack, setBackButton])
  
  const handleCopyLink = async () => {
    const refLink = `https://t.me/pvndora_ai_bot?start=ref_${user?.id}`
    try {
      await navigator.clipboard.writeText(refLink)
      hapticFeedback('notification', 'success')
      showPopup({ title: '✅', message: t('profile.linkCopied'), buttons: [{ type: 'ok' }] })
    } catch (e) {
      console.error('Copy failed', e)
    }
  }
  
  const handleShare = async () => {
    setShareLoading(true)
    hapticFeedback('impact', 'medium')
    try {
      const { prepared_message_id } = await post('/referral/share-link')
      if (window.Telegram?.WebApp?.shareMessage) {
        window.Telegram.WebApp.shareMessage(prepared_message_id, (success) => {
          if (success) console.log('Shared successfully')
        })
      } else if (window.Telegram?.WebApp?.switchInlineQuery) {
        window.Telegram.WebApp.switchInlineQuery("invite", ['users', 'groups', 'channels'])
      } else {
        await handleCopyLink()
      }
    } catch (err) {
      await handleCopyLink()
    } finally {
      setShareLoading(false)
    }
  }
  
  const handleWithdraw = async () => {
    const amount = parseFloat(withdrawAmount)
    if (isNaN(amount) || amount < WITHDRAWAL_MIN) {
      showPopup({ title: '❌', message: t('profile.minWithdrawal', { min: formatPrice(WITHDRAWAL_MIN, currency) }), buttons: [{ type: 'ok' }] })
      return
    }
    if (amount > (profile?.balance || 0)) {
      showPopup({ title: '❌', message: t('profile.insufficientBalance'), buttons: [{ type: 'ok' }] })
      return
    }
    if (!withdrawDetails.trim()) {
      showPopup({ title: '❌', message: t('profile.enterPaymentDetails'), buttons: [{ type: 'ok' }] })
      return
    }
    
    setSubmitting(true)
    try {
      await post('/profile/withdraw', { amount, method: withdrawMethod, details: withdrawDetails })
      hapticFeedback('notification', 'success')
      showPopup({ title: '✅', message: t('profile.withdrawalRequested'), buttons: [{ type: 'ok' }] })
      setWithdrawDialog(false)
      setWithdrawAmount('')
      setWithdrawDetails('')
      loadProfile()
    } catch (err) {
      showPopup({ title: '❌', message: err.message || t('common.error'), buttons: [{ type: 'ok' }] })
    } finally {
      setSubmitting(false)
    }
  }
  
  const getMethodIcon = (method) => {
    switch (method) {
      case 'card': return <CreditCard className="h-4 w-4" />
      case 'phone': return <Smartphone className="h-4 w-4" />
      case 'crypto': return <Bitcoin className="h-4 w-4" />
      default: return <Wallet className="h-4 w-4" />
    }
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

      {/* Header */}
      <div className="sticky top-0 z-20 p-4">
        <Button variant="ghost" size="icon" onClick={onBack} className="h-10 w-10 rounded-full bg-secondary/30 backdrop-blur-md">
          <ArrowLeft className="h-5 w-5" />
        </Button>
      </div>
      
      <div className="px-4 space-y-6 relative z-10">
        
        {/* User Info */}
        <div className="flex items-center gap-4 px-2">
           <div className="w-16 h-16 rounded-full bg-gradient-to-br from-primary to-blue-600 p-[2px]">
              <div className="w-full h-full rounded-full bg-background flex items-center justify-center text-2xl font-bold overflow-hidden">
                {user?.photo_url ? <img src={user.photo_url} alt="ava" className="w-full h-full object-cover" /> : (user?.username?.[0] || 'U')}
              </div>
           </div>
           <div>
              <h1 className="text-xl font-bold flex items-center gap-2">
                 {user?.first_name} {isPartner && <Badge variant="secondary" className="bg-purple-500/20 text-purple-400 text-[10px] h-5">VIP</Badge>}
              </h1>
              <p className="text-muted-foreground text-sm">@{user?.username || 'user'}</p>
           </div>
        </div>

        {isPartner ? (
          <PartnerDashboard 
            profile={profile}
            referralLink={`https://t.me/pvndora_ai_bot?start=ref_${user?.id}`}
            onWithdraw={() => setWithdrawDialog(true)}
            onShare={handleShare}
          />
        ) : (
          <>
            {/* Balance Card (Glassmorphism + Neon) */}
            <motion.div 
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="relative rounded-3xl overflow-hidden bg-gradient-to-br from-primary/20 via-background to-background border border-primary/20 shadow-[0_0_30px_rgba(0,245,212,0.15)]"
            >
               <div className="absolute top-0 right-0 w-32 h-32 bg-primary/20 blur-3xl rounded-full -mr-10 -mt-10 pointer-events-none" />
               
               <div className="p-6">
                  <p className="text-sm text-muted-foreground mb-1">{t('profile.balance')}</p>
                  <div className="flex items-baseline gap-1">
                    <span className="text-4xl font-black tracking-tighter bg-clip-text text-transparent bg-gradient-to-r from-primary to-emerald-400">
                      {formatPrice(profile?.balance || 0, currency)}
                    </span>
                  </div>
                  
                  <div className="mt-6 grid grid-cols-2 gap-3">
                     <Button 
                        onClick={() => setWithdrawDialog(true)}
                        disabled={(profile?.balance || 0) < WITHDRAWAL_MIN}
                        className="bg-background/50 backdrop-blur-md border border-white/10 hover:bg-background/80 shadow-sm"
                      >
                        <Wallet className="h-4 w-4 mr-2" />
                        {t('profile.withdraw')}
                      </Button>
                      <Button 
                        onClick={handleShare}
                        disabled={shareLoading}
                        className="bg-primary text-primary-foreground hover:bg-primary/90 shadow-[0_0_15px_rgba(0,245,212,0.4)]"
                      >
                        <Share2 className="h-4 w-4 mr-2" />
                        {t('profile.invite')}
                      </Button>
                  </div>
                  
                  {(profile?.balance || 0) < WITHDRAWAL_MIN && (
                     <div className="mt-3 flex items-center justify-center gap-1.5 text-[10px] text-muted-foreground opacity-70">
                       <Lock className="h-3 w-3" />
                       {t('profile.minWithdrawalNote', { min: formatPrice(WITHDRAWAL_MIN, currency) })}
                     </div>
                  )}
               </div>
            </motion.div>

            {/* Referral Stats Grid */}
            <div className="grid grid-cols-3 gap-3">
               <div className="bg-secondary/20 rounded-2xl p-3 text-center border border-white/5">
                  <div className="text-xl font-bold text-foreground">{referralStats?.active_referrals || 0}</div>
                  <div className="text-[10px] text-muted-foreground uppercase tracking-wider mt-1">Users</div>
               </div>
               <div className="bg-secondary/20 rounded-2xl p-3 text-center border border-white/5">
                  <div className="text-xl font-bold text-green-500">{referralStats?.conversion_rate || 0}%</div>
                  <div className="text-[10px] text-muted-foreground uppercase tracking-wider mt-1">Conv.</div>
               </div>
               <div className="bg-secondary/20 rounded-2xl p-3 text-center border border-white/5">
                  <div className="text-xl font-bold text-foreground">{formatPrice(referralStats?.avg_order_value || 0, currency)}</div>
                  <div className="text-[10px] text-muted-foreground uppercase tracking-wider mt-1">Avg.</div>
               </div>
            </div>

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
            
            {/* Copy Link */}
            <div className="bg-secondary/20 rounded-2xl p-4 flex items-center justify-between gap-4 border border-white/5">
               <div className="min-w-0">
                  <p className="text-xs font-medium text-muted-foreground mb-1">{t('profile.yourReferralLink')}</p>
                  <p className="text-sm font-mono truncate opacity-80">t.me/pvndora_bot?start=ref_{user?.id}</p>
               </div>
               <Button variant="secondary" size="icon" onClick={handleCopyLink} className="shrink-0 rounded-xl">
                  <Copy className="h-4 w-4" />
               </Button>
            </div>
          </>
        )}
      </div>

      {/* Withdrawal Dialog */}
      <Dialog open={withdrawDialog} onOpenChange={setWithdrawDialog}>
        <DialogContent className="sm:max-w-md bg-card/95 backdrop-blur-xl border-white/10">
          <DialogHeader>
            <DialogTitle>{t('profile.withdrawTitle')}</DialogTitle>
            <DialogDescription>{t('profile.withdrawDescription')}</DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>{t('profile.amount')}</Label>
              <div className="relative">
                 <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                 <Input
                  type="number"
                  className="pl-8"
                  placeholder={formatPrice(WITHDRAWAL_MIN, currency)}
                  value={withdrawAmount}
                  onChange={(e) => setWithdrawAmount(e.target.value)}
                />
              </div>
              <p className="text-xs text-right text-muted-foreground">
                {t('profile.available')}: {formatPrice(profile?.balance || 0, currency)}
              </p>
            </div>
            
            <div className="space-y-2">
              <Label>{t('profile.paymentMethod')}</Label>
              <div className="grid grid-cols-3 gap-2">
                {['card', 'phone', 'crypto'].map((method) => (
                  <button
                    key={method}
                    onClick={() => setWithdrawMethod(method)}
                    className={cn(
                      "flex flex-col items-center gap-2 p-3 rounded-xl border transition-all",
                      withdrawMethod === method ? "bg-primary/10 border-primary text-primary" : "bg-secondary/30 border-transparent hover:bg-secondary/50"
                    )}
                  >
                    {getMethodIcon(method)}
                    <span className="text-[10px] font-medium uppercase">{t(`profile.method.${method}`)}</span>
                  </button>
                ))}
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>{t('profile.paymentDetails')}</Label>
              <Input
                placeholder={withdrawMethod === 'card' ? '4276 **** **** ****' : withdrawMethod === 'phone' ? '+7 900 000 00 00' : 'Wallet Address'}
                value={withdrawDetails}
                onChange={(e) => setWithdrawDetails(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setWithdrawDialog(false)}>{t('common.cancel')}</Button>
            <Button onClick={handleWithdraw} disabled={submitting} className="bg-primary text-black hover:bg-primary/90">
              {submitting ? t('common.loading') : t('profile.requestWithdrawal')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
