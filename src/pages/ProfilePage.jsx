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
  ChevronRight,
  Gift,
  Clock,
  CheckCircle,
  XCircle,
  AlertCircle,
  CreditCard,
  Smartphone,
  Bitcoin,
  Lock,
  Unlock,
  DollarSign,
  Star
} from 'lucide-react'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Skeleton } from '../components/ui/skeleton'
import { Separator } from '../components/ui/separator'
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

const WITHDRAWAL_MIN = 500 // Минимум для вывода

// Level Card Component with visual states
function LevelCard({ level, commission, threshold, isUnlocked, isProgramLocked, count, earnings, formatPrice, t, color, isInstant }) {
  const isLocked = !isUnlocked
  
  // Color configs
  const colorConfig = {
    green: {
      active: 'bg-gradient-to-r from-green-500/10 to-transparent border-green-500/20',
      locked: 'bg-gradient-to-r from-gray-500/5 to-transparent border-gray-500/10',
      circle: isLocked ? 'bg-gray-500/10' : 'bg-green-500/20',
      text: isLocked ? 'text-gray-400' : 'text-green-500',
      earnings: isLocked ? 'text-gray-400' : 'text-green-500'
    },
    blue: {
      active: 'bg-gradient-to-r from-blue-500/10 to-transparent border-blue-500/20',
      locked: 'bg-gradient-to-r from-gray-500/5 to-transparent border-gray-500/10',
      circle: isLocked ? 'bg-gray-500/10' : 'bg-blue-500/20',
      text: isLocked ? 'text-gray-400' : 'text-blue-500',
      earnings: isLocked ? 'text-gray-400' : 'text-blue-500'
    },
    purple: {
      active: 'bg-gradient-to-r from-purple-500/10 to-transparent border-purple-500/20',
      locked: 'bg-gradient-to-r from-gray-500/5 to-transparent border-gray-500/10',
      circle: isLocked ? 'bg-gray-500/10' : 'bg-purple-500/20',
      text: isLocked ? 'text-gray-400' : 'text-purple-500',
      earnings: isLocked ? 'text-gray-400' : 'text-purple-500'
    }
  }
  
  const cfg = colorConfig[color]
  
  // Unlock description based on level type
  const getUnlockDescription = () => {
    if (isUnlocked) {
      return `${commission} ${t('profile.commission')}`
    }
    if (isInstant) {
      return t('profile.unlockOnPurchase')  // "Откроется при покупке"
    }
    return `${t('profile.unlockAt')} $${threshold}`
  }
  
  return (
    <Card className={`${isLocked ? cfg.locked : cfg.active} ${isLocked ? 'opacity-60' : ''} transition-all`}>
      <CardContent className="p-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className={`w-10 h-10 rounded-full ${cfg.circle} flex items-center justify-center relative`}>
            {isLocked ? (
              <Lock className={`h-4 w-4 ${cfg.text}`} />
            ) : (
              <span className={`font-bold ${cfg.text}`}>{level}</span>
            )}
          </div>
          <div>
            <p className={`font-medium ${isLocked ? 'text-muted-foreground' : ''}`}>
              {t(`profile.level${level}`)}
            </p>
            <p className="text-xs text-muted-foreground">
              {getUnlockDescription()}
            </p>
          </div>
        </div>
        <div className="text-right">
          <p className={`font-bold text-lg ${isLocked ? 'text-muted-foreground' : ''}`}>
            {count}
          </p>
          {isUnlocked && earnings > 0 ? (
            <p className={`text-xs ${cfg.earnings}`}>
              +{formatPrice(earnings)}
            </p>
          ) : isLocked && !isProgramLocked ? (
            <p className="text-xs text-muted-foreground">
              {t('profile.pendingRewards')}
            </p>
          ) : (
            <p className="text-xs text-muted-foreground">
              {formatPrice(0)}
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

export default function ProfilePage({ onBack }) {
  const { get, post, loading } = useApi()
  const { t, formatPrice } = useLocale()
  const { setBackButton, user, showPopup, hapticFeedback } = useTelegram()
  
  const [profile, setProfile] = useState(null)
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
    
    setBackButton({
      isVisible: true,
      onClick: onBack
    })
    
    return () => {
      setBackButton({ isVisible: false })
    }
  }, [loadProfile, onBack, setBackButton])
  
  const handleCopyLink = async () => {
    const refLink = `https://t.me/pvndora_ai_bot?start=ref_${user?.id}`
    try {
      await navigator.clipboard.writeText(refLink)
      hapticFeedback('notification', 'success')
      showPopup({
        title: '✅',
        message: t('profile.linkCopied'),
        buttons: [{ type: 'ok' }]
      })
    } catch (e) {
      console.error('Copy failed', e)
    }
  }
  
  const handleShare = async () => {
    setShareLoading(true)
    hapticFeedback('impact', 'medium')
    
    try {
      // 1. Generate prepared message via API
      const { prepared_message_id } = await post('/referral/share-link')
      
      // 2. Use Telegram shareMessage if supported
      if (window.Telegram?.WebApp?.shareMessage) {
        window.Telegram.WebApp.shareMessage(prepared_message_id, (success) => {
          if (success) {
            console.log('Shared successfully')
          }
        })
      } else {
        // Fallback to switchInlineQuery
        if (window.Telegram?.WebApp?.switchInlineQuery) {
          window.Telegram.WebApp.switchInlineQuery("invite", ['users', 'groups', 'channels'])
        } else {
          // Final fallback: copy link
          await handleCopyLink()
        }
      }
    } catch (err) {
      console.error('Share failed:', err)
      // Fallback: Copy link
      await handleCopyLink()
    } finally {
      setShareLoading(false)
    }
  }
  
  const handleWithdraw = async () => {
    const amount = parseFloat(withdrawAmount)
    if (isNaN(amount) || amount < WITHDRAWAL_MIN) {
      showPopup({
        title: '❌',
        message: t('profile.minWithdrawal', { min: formatPrice(WITHDRAWAL_MIN) }),
        buttons: [{ type: 'ok' }]
      })
      return
    }
    
    if (amount > (profile?.balance || 0)) {
      showPopup({
        title: '❌',
        message: t('profile.insufficientBalance'),
        buttons: [{ type: 'ok' }]
      })
      return
    }
    
    if (!withdrawDetails.trim()) {
      showPopup({
        title: '❌',
        message: t('profile.enterPaymentDetails'),
        buttons: [{ type: 'ok' }]
      })
      return
    }
    
    setSubmitting(true)
    try {
      await post('/profile/withdraw', {
        amount,
        method: withdrawMethod,
        details: withdrawDetails
      })
      
      hapticFeedback('notification', 'success')
      showPopup({
        title: '✅',
        message: t('profile.withdrawalRequested'),
        buttons: [{ type: 'ok' }]
      })
      
      setWithdrawDialog(false)
      setWithdrawAmount('')
      setWithdrawDetails('')
      loadProfile()
    } catch (err) {
      showPopup({
        title: '❌',
        message: err.message || t('common.error'),
        buttons: [{ type: 'ok' }]
      })
    } finally {
      setSubmitting(false)
    }
  }
  
  const getStatusIcon = (status) => {
    switch (status) {
      case 'completed': return <CheckCircle className="h-4 w-4 text-green-500" />
      case 'rejected': return <XCircle className="h-4 w-4 text-red-500" />
      case 'processing': return <Clock className="h-4 w-4 text-yellow-500" />
      default: return <AlertCircle className="h-4 w-4 text-muted-foreground" />
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
        <Skeleton className="h-32 w-full rounded-xl" />
        <Skeleton className="h-24 w-full rounded-xl" />
        <Skeleton className="h-48 w-full rounded-xl" />
      </div>
    )
  }
  
  // Check if user is a VIP Partner
  const isPartner = profile?.is_partner || referralProgram?.is_partner
  
  return (
    <div className="pb-24">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b border-border/50 p-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={onBack} className="h-8 w-8 rounded-full">
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-lg font-bold">
              {isPartner ? 'Partner Dashboard' : t('profile.title')}
            </h1>
            <p className="text-xs text-muted-foreground">
              @{user?.username || 'user'}
              {isPartner && <span className="text-purple-400 ml-2">⭐ VIP</span>}
            </p>
          </div>
        </div>
      </div>
      
      <div className="p-4 space-y-6">
        {/* VIP Partner Dashboard - completely different UI */}
        {isPartner ? (
          <PartnerDashboard 
            profile={profile}
            referralLink={`https://t.me/pvndora_ai_bot?start=ref_${user?.id}`}
            onWithdraw={() => setWithdrawDialog(true)}
            onShare={handleShare}
          />
        ) : (
          <>
        {/* Balance Card - Regular User */}
        <Card className="bg-gradient-to-br from-primary/20 via-primary/10 to-background border-primary/20">
          <CardContent className="p-6">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-muted-foreground mb-1">{t('profile.balance')}</p>
                <p className="text-4xl font-bold">{formatPrice(profile?.balance || 0)}</p>
                <p className="text-xs text-muted-foreground mt-2">
                  {t('profile.totalEarned')}: {formatPrice(profile?.total_referral_earnings || 0)}
                </p>
              </div>
              <div className="p-3 rounded-full bg-primary/20">
                <Wallet className="h-6 w-6 text-primary" />
              </div>
            </div>
            
            <div className="flex gap-3 mt-6">
              <Button 
                onClick={() => setWithdrawDialog(true)}
                disabled={(profile?.balance || 0) < WITHDRAWAL_MIN}
                variant="outline"
                className="flex-1 gap-2"
              >
                <Wallet className="h-4 w-4" />
                {t('profile.withdraw')}
              </Button>
              <Button 
                onClick={handleShare} 
                disabled={shareLoading}
                className="flex-1 gap-2 bg-gradient-to-r from-primary to-primary/80"
              >
                <Share2 className="h-4 w-4" />
                {shareLoading ? '...' : t('profile.invite')}
              </Button>
            </div>
            
            {(profile?.balance || 0) < WITHDRAWAL_MIN && (
              <p className="text-xs text-muted-foreground text-center mt-3">
                {t('profile.minWithdrawalNote', { min: formatPrice(WITHDRAWAL_MIN) })}
              </p>
            )}
          </CardContent>
        </Card>
        
        {/* Referral Program Status Card */}
        {referralProgram && (
          <Card className={
            referralProgram.status === 'locked' 
              ? "bg-gradient-to-r from-gray-500/10 to-gray-500/5 border-gray-500/20" 
              : "bg-gradient-to-r from-green-500/10 to-emerald-500/5 border-green-500/20"
          }>
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  {referralProgram.status === 'locked' ? (
                    <Lock className="h-5 w-5 text-gray-400" />
                  ) : (
                    <CheckCircle className="h-5 w-5 text-green-500" />
                  )}
                  <span className="font-semibold">
                    {referralProgram.status === 'locked' 
                      ? t('profile.programLocked')
                      : t('profile.programActive')
                    }
                  </span>
                  {referralProgram.status === 'active' && (
                    <Badge variant="outline" className="ml-2 text-green-500 border-green-500/30">
                      {t('profile.level')} {referralProgram.effective_level}
                    </Badge>
                  )}
                </div>
                {referralProgram.is_partner && (
                  <Badge className="bg-purple-500/20 text-purple-400 border-purple-500/30">
                    <Star className="h-3 w-3 mr-1" /> Partner
                  </Badge>
                )}
              </div>
              
              {/* State 0: Locked - No purchases yet */}
              {referralProgram.status === 'locked' && (
                <div className="space-y-3">
                  <p className="text-sm text-muted-foreground">
                    {t('profile.makeFirstPurchaseInstant')}
                  </p>
                  <Button variant="outline" className="w-full gap-2" onClick={onBack}>
                    <Gift className="h-4 w-4" />
                    {t('profile.goToCatalog')}
                  </Button>
                </div>
              )}
              
              {/* Active State - Level 1 instant, progress to Level 2/3 */}
              {referralProgram.status === 'active' && (
                <div className="space-y-3">
                  {/* Current commissions info */}
                  <div className="flex flex-wrap gap-2 text-xs">
                    <span className="px-2 py-1 rounded bg-green-500/10 text-green-500">
                      L1: {referralProgram.commissions_percent?.level1 || 20}%
                    </span>
                    {referralProgram.level2_unlocked && (
                      <span className="px-2 py-1 rounded bg-blue-500/10 text-blue-500">
                        L2: {referralProgram.commissions_percent?.level2 || 10}%
                      </span>
                    )}
                    {referralProgram.level3_unlocked && (
                      <span className="px-2 py-1 rounded bg-purple-500/10 text-purple-500">
                        L3: {referralProgram.commissions_percent?.level3 || 5}%
                      </span>
                    )}
                  </div>
                  
                  {/* Progress bar to next level */}
                  {referralProgram.effective_level < 3 && referralProgram.next_threshold_usd && (
                    <div className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-muted-foreground flex items-center gap-1">
                          <DollarSign className="h-3 w-3" /> {t('profile.yourTurnover')}
                        </span>
                        <span className="font-bold text-green-500">
                          ${referralProgram.turnover_usd?.toFixed(0) || 0} / ${referralProgram.next_threshold_usd}
                        </span>
                      </div>
                      <div className="h-3 bg-secondary rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-gradient-to-r from-green-500 to-emerald-400 rounded-full transition-all"
                          style={{ 
                            width: `${Math.min(100, ((referralProgram.turnover_usd || 0) / referralProgram.next_threshold_usd) * 100)}%` 
                          }}
                        />
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {t('profile.amountToNextLevel', { 
                          level: referralProgram.effective_level + 1, 
                          amount: `$${referralProgram.amount_to_next_level_usd?.toFixed(0) || 0}` 
                        })}
                      </p>
                    </div>
                  )}
                  
                  {referralProgram.effective_level >= 3 && (
                    <p className="text-sm text-green-600 font-medium flex items-center gap-2">
                      <CheckCircle className="h-4 w-4" />
                      {t('profile.maxLevelReached')}
                    </p>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        )}
        
        {/* Referral Link */}
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium mb-1">{t('profile.yourReferralLink')}</p>
                <p className="text-xs text-muted-foreground truncate font-mono">
                  {`t.me/pvndora_ai_bot?start=ref_${user?.id}`}
                </p>
              </div>
              <Button variant="outline" size="sm" onClick={handleCopyLink} className="gap-2">
                <Copy className="h-4 w-4" />
                {t('leaderboard.copyLink')}
              </Button>
            </div>
          </CardContent>
        </Card>
        
        {/* Referral Performance */}
        {referralStats && (referralStats.level1_count > 0 || referralStats.active_referrals > 0) && (
          <Card>
            <CardContent className="p-4">
              <h3 className="font-semibold mb-3 flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-primary" />
                Эффективность
              </h3>
              <div className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <p className="text-2xl font-bold text-primary">{referralStats.active_referrals || 0}</p>
                  <p className="text-xs text-muted-foreground">Активных</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-green-500">{referralStats.conversion_rate || 0}%</p>
                  <p className="text-xs text-muted-foreground">Конверсия</p>
                </div>
                <div>
                  <p className="text-2xl font-bold">{formatPrice(referralStats.avg_order_value || 0)}</p>
                  <p className="text-xs text-muted-foreground">Ср. чек</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}
        
        {/* 3-Level Referral Stats with Visual States */}
        <div className="space-y-3">
          <h2 className="font-semibold flex items-center gap-2">
            <Users className="h-4 w-4 text-primary" />
            {t('profile.referralNetwork')}
          </h2>
          
          <div className="grid gap-3">
            {/* Level 1 - Instant unlock (no threshold) */}
            <LevelCard 
              level={1}
              commission={`${referralProgram?.commissions_percent?.level1 || 20}%`}
              threshold={0}  // Instant!
              isUnlocked={referralProgram?.level1_unlocked}
              isProgramLocked={referralProgram?.status === 'locked'}
              count={referralStats?.level1_count || 0}
              earnings={referralStats?.level1_earnings || 0}
              formatPrice={formatPrice}
              t={t}
              color="green"
              isInstant={true}
            />
            
            {/* Level 2 - Dynamic threshold from settings */}
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
            
            {/* Level 3 - Dynamic threshold from settings */}
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
        
        {/* Recent Bonuses */}
        {bonusHistory.length > 0 && (
          <div className="space-y-3">
            <h2 className="font-semibold flex items-center gap-2">
              <Gift className="h-4 w-4 text-primary" />
              {t('profile.recentBonuses')}
            </h2>
            
            <Card>
              <CardContent className="p-0 divide-y divide-border">
                {bonusHistory.slice(0, 5).map((bonus, i) => (
                  <div key={i} className="p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <Badge variant="outline" className={
                        bonus.level === 1 ? 'bg-green-500/10 text-green-500 border-green-500/20' :
                        bonus.level === 2 ? 'bg-blue-500/10 text-blue-500 border-blue-500/20' :
                        'bg-purple-500/10 text-purple-500 border-purple-500/20'
                      }>
                        L{bonus.level}
                      </Badge>
                      <div>
                        <p className="text-sm font-medium">{t('profile.referralBonus')}</p>
                        <p className="text-xs text-muted-foreground">
                          {new Date(bonus.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <span className="font-bold text-green-500">
                      +{formatPrice(bonus.amount)}
                    </span>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        )}
        
        {/* Withdrawal History */}
        {withdrawals.length > 0 && (
          <div className="space-y-3">
            <h2 className="font-semibold flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-primary" />
              {t('profile.withdrawalHistory')}
            </h2>
            
            <Card>
              <CardContent className="p-0 divide-y divide-border">
                {withdrawals.map((w, i) => (
                  <div key={i} className="p-4 flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      {getMethodIcon(w.payment_method)}
                      <div>
                        <p className="text-sm font-medium">{formatPrice(w.amount)}</p>
                        <p className="text-xs text-muted-foreground">
                          {new Date(w.created_at).toLocaleDateString()}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {getStatusIcon(w.status)}
                      <Badge variant={
                        w.status === 'completed' ? 'success' :
                        w.status === 'rejected' ? 'destructive' :
                        'secondary'
                      }>
                        {t(`profile.status.${w.status}`)}
                      </Badge>
                    </div>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        )}
        
        {/* Info Card */}
        <Card className="bg-secondary/30 border-none">
          <CardContent className="p-4">
            <h3 className="font-medium mb-2">{t('profile.howItWorks')}</h3>
            <ul className="text-sm text-muted-foreground space-y-2">
              <li>• {t('profile.tip1')}</li>
              <li>• {t('profile.tip2')}</li>
              <li>• {t('profile.tip3')}</li>
            </ul>
          </CardContent>
        </Card>
        </>
        )}
      </div>
      
      {/* Withdrawal Dialog */}
      <Dialog open={withdrawDialog} onOpenChange={setWithdrawDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>{t('profile.withdrawTitle')}</DialogTitle>
            <DialogDescription>
              {t('profile.withdrawDescription')}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>{t('profile.amount')}</Label>
              <Input
                type="number"
                placeholder={formatPrice(WITHDRAWAL_MIN)}
                value={withdrawAmount}
                onChange={(e) => setWithdrawAmount(e.target.value)}
                min={WITHDRAWAL_MIN}
                max={profile?.balance || 0}
              />
              <p className="text-xs text-muted-foreground">
                {t('profile.available')}: {formatPrice(profile?.balance || 0)}
              </p>
            </div>
            
            <div className="space-y-2">
              <Label>{t('profile.paymentMethod')}</Label>
              <div className="grid grid-cols-3 gap-2">
                {['card', 'phone', 'crypto'].map((method) => (
                  <Button
                    key={method}
                    variant={withdrawMethod === method ? 'default' : 'outline'}
                    onClick={() => setWithdrawMethod(method)}
                    className="h-12 flex-col gap-1"
                  >
                    {getMethodIcon(method)}
                    <span className="text-xs">{t(`profile.method.${method}`)}</span>
                  </Button>
                ))}
              </div>
            </div>
            
            <div className="space-y-2">
              <Label>{t('profile.paymentDetails')}</Label>
              <Input
                placeholder={
                  withdrawMethod === 'card' ? '4276 **** **** ****' :
                  withdrawMethod === 'phone' ? '+7 (***) ***-**-**' :
                  'TRC20 / BTC address'
                }
                value={withdrawDetails}
                onChange={(e) => setWithdrawDetails(e.target.value)}
              />
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setWithdrawDialog(false)}>
              {t('common.cancel')}
            </Button>
            <Button onClick={handleWithdraw} disabled={submitting}>
              {submitting ? t('common.loading') : t('profile.requestWithdrawal')}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

