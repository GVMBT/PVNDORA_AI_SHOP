import React, { useState, useEffect } from 'react'
import { useApi } from '../hooks/useApi'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'
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
  Bitcoin
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

export default function ProfilePage({ onBack }) {
  const { get, post, loading } = useApi()
  const { t, formatPrice } = useLocale()
  const { setBackButton, user, showPopup, hapticFeedback } = useTelegram()
  
  const [profile, setProfile] = useState(null)
  const [referralStats, setReferralStats] = useState(null)
  const [bonusHistory, setBonusHistory] = useState([])
  const [withdrawals, setWithdrawals] = useState([])
  const [activeTab, setActiveTab] = useState('overview') // overview, referrals, history, withdraw
  const [withdrawDialog, setWithdrawDialog] = useState(false)
  const [withdrawAmount, setWithdrawAmount] = useState('')
  const [withdrawMethod, setWithdrawMethod] = useState('card')
  const [withdrawDetails, setWithdrawDetails] = useState('')
  const [submitting, setSubmitting] = useState(false)
  
  useEffect(() => {
    loadProfile()
    
    setBackButton({
      isVisible: true,
      onClick: onBack
    })
    
    return () => {
      setBackButton({ isVisible: false })
    }
  }, [])
  
  const loadProfile = async () => {
    try {
      const data = await get('/profile')
      setProfile(data.profile)
      setReferralStats(data.referral_stats)
      setBonusHistory(data.bonus_history || [])
      setWithdrawals(data.withdrawals || [])
    } catch (err) {
      console.error('Failed to load profile:', err)
    }
  }
  
  const handleCopyLink = () => {
    if (!profile?.referral_link) return
    navigator.clipboard.writeText(profile.referral_link)
    hapticFeedback('notification', 'success')
    showPopup({
      title: '✅',
      message: t('profile.linkCopied'),
      buttons: [{ type: 'ok' }]
    })
  }
  
  const handleShare = async () => {
    if (!profile?.referral_link) return
    hapticFeedback('impact', 'medium')
    
    const text = t('profile.shareText', { saved: formatPrice(profile.total_saved || 0) })
    
    if (navigator.share) {
      try {
        await navigator.share({
          title: 'PVNDORA',
          text: text,
          url: profile.referral_link
        })
      } catch (e) {
        // User cancelled
      }
    } else {
      handleCopyLink()
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
  
  return (
    <div className="pb-24">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b border-border/50 p-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={onBack} className="h-8 w-8 rounded-full">
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-lg font-bold">{t('profile.title')}</h1>
            <p className="text-xs text-muted-foreground">@{user?.username || 'user'}</p>
          </div>
        </div>
      </div>
      
      <div className="p-4 space-y-6">
        {/* Balance Card */}
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
                className="flex-1"
              >
                {t('profile.withdraw')}
              </Button>
              <Button variant="outline" onClick={handleShare} className="flex-1 gap-2">
                <Share2 className="h-4 w-4" />
                {t('profile.invite')}
              </Button>
            </div>
            
            {(profile?.balance || 0) < WITHDRAWAL_MIN && (
              <p className="text-xs text-muted-foreground text-center mt-3">
                {t('profile.minWithdrawalNote', { min: formatPrice(WITHDRAWAL_MIN) })}
              </p>
            )}
          </CardContent>
        </Card>
        
        {/* Referral Link */}
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium mb-1">{t('profile.yourReferralLink')}</p>
                <p className="text-xs text-muted-foreground truncate">
                  {profile?.referral_link}
                </p>
              </div>
              <Button variant="ghost" size="icon" onClick={handleCopyLink}>
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          </CardContent>
        </Card>
        
        {/* 3-Level Referral Stats */}
        <div className="space-y-3">
          <h2 className="font-semibold flex items-center gap-2">
            <Users className="h-4 w-4 text-primary" />
            {t('profile.referralNetwork')}
          </h2>
          
          <div className="grid gap-3">
            {/* Level 1 */}
            <Card className="bg-gradient-to-r from-green-500/10 to-transparent border-green-500/20">
              <CardContent className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-green-500/20 flex items-center justify-center">
                    <span className="font-bold text-green-500">1</span>
                  </div>
                  <div>
                    <p className="font-medium">{t('profile.level1')}</p>
                    <p className="text-xs text-muted-foreground">20% {t('profile.commission')}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-bold text-lg">{referralStats?.level1_count || 0}</p>
                  <p className="text-xs text-green-500">
                    +{formatPrice(referralStats?.level1_earnings || 0)}
                  </p>
                </div>
              </CardContent>
            </Card>
            
            {/* Level 2 */}
            <Card className="bg-gradient-to-r from-blue-500/10 to-transparent border-blue-500/20">
              <CardContent className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-blue-500/20 flex items-center justify-center">
                    <span className="font-bold text-blue-500">2</span>
                  </div>
                  <div>
                    <p className="font-medium">{t('profile.level2')}</p>
                    <p className="text-xs text-muted-foreground">10% {t('profile.commission')}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-bold text-lg">{referralStats?.level2_count || 0}</p>
                  <p className="text-xs text-blue-500">
                    +{formatPrice(referralStats?.level2_earnings || 0)}
                  </p>
                </div>
              </CardContent>
            </Card>
            
            {/* Level 3 */}
            <Card className="bg-gradient-to-r from-purple-500/10 to-transparent border-purple-500/20">
              <CardContent className="p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-full bg-purple-500/20 flex items-center justify-center">
                    <span className="font-bold text-purple-500">3</span>
                  </div>
                  <div>
                    <p className="font-medium">{t('profile.level3')}</p>
                    <p className="text-xs text-muted-foreground">5% {t('profile.commission')}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="font-bold text-lg">{referralStats?.level3_count || 0}</p>
                  <p className="text-xs text-purple-500">
                    +{formatPrice(referralStats?.level3_earnings || 0)}
                  </p>
                </div>
              </CardContent>
            </Card>
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

