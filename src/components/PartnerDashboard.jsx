import React, { useState, useEffect, useCallback } from 'react'
import { useApi } from '../hooks/useApi'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'
import {
  Wallet,
  Users,
  TrendingUp,
  DollarSign,
  Copy,
  Share2,
  Star,
  RefreshCw,
  UserCheck,
  BarChart3,
  Percent,
  Gift,
  Coins,
  ArrowLeftRight,
  Info
} from 'lucide-react'
import { Button } from './ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from './ui/card'
import { Badge } from './ui/badge'
import { Skeleton } from './ui/skeleton'
import { Switch } from './ui/switch'
import { Tooltip, TooltipTrigger, TooltipContent } from './ui/tooltip'

/**
 * Partner Dashboard - VIP Partner exclusive view
 * Shows extended analytics, referral list, earnings chart
 */
export default function PartnerDashboard({ profile, referralLink, onWithdraw, onShare }) {
  const { get, post } = useApi()
  const { formatPrice, t } = useLocale()
  const { hapticFeedback, showPopup } = useTelegram()
  
  const [dashboard, setDashboard] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [discountMode, setDiscountMode] = useState(false)
  const [togglingMode, setTogglingMode] = useState(false)
  
  const loadDashboard = useCallback(async () => {
    setLoading(true)
    setError(null)
    
    try {
      const data = await get('/partner/dashboard')
      setDashboard(data)
      // Set discount mode from profile data
      setDiscountMode(data?.partner_mode === 'discount')
    } catch (err) {
      console.error('Failed to load partner dashboard:', err)
      setError(err.message || 'Ошибка загрузки')
    } finally {
      setLoading(false)
    }
  }, [get])
  
  useEffect(() => {
    loadDashboard()
  }, [loadDashboard])
  
  // Toggle discount mode vs commission mode
  const handleToggleMode = async () => {
    const newMode = !discountMode
    setTogglingMode(true)
    
    // Optimistic update
    setDiscountMode(newMode)
    hapticFeedback('impact', 'medium')
    
    try {
      await post('/partner/mode', {
        mode: newMode ? 'discount' : 'commission',
        discount_percent: newMode ? 15 : 0
      })
      
      hapticFeedback('notification', 'success')
      showPopup({
        title: newMode ? '🎁' : '💰',
        message: newMode 
          ? 'Режим скидок активирован. Ваши рефералы получат 15% скидку на все покупки!' 
          : 'Режим комиссий активирован. Вы будете получать вознаграждения за покупки рефералов.',
        buttons: [{ type: 'ok' }]
      })
    } catch (err) {
      // Rollback
      setDiscountMode(!newMode)
      hapticFeedback('notification', 'error')
      showPopup({
        title: '❌',
        message: err.message || 'Ошибка переключения режима',
        buttons: [{ type: 'ok' }]
      })
    } finally {
      setTogglingMode(false)
    }
  }
  
  const handleCopyLink = async () => {
    try {
      const link = dashboard?.referral_link || referralLink
      await navigator.clipboard.writeText(link)
      hapticFeedback('notification', 'success')
      showPopup({
        title: '✓',
        message: 'Ссылка скопирована',
        buttons: [{ type: 'ok' }]
      })
    } catch (err) {
      console.error('Copy failed:', err)
    }
  }
  
  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-32 w-full rounded-xl" />
        <div className="grid grid-cols-2 gap-3">
          <Skeleton className="h-24 rounded-xl" />
          <Skeleton className="h-24 rounded-xl" />
          <Skeleton className="h-24 rounded-xl" />
          <Skeleton className="h-24 rounded-xl" />
        </div>
        <Skeleton className="h-48 w-full rounded-xl" />
      </div>
    )
  }
  
  if (error) {
    return (
      <Card className="border-destructive/50">
        <CardContent className="p-6 text-center">
          <p className="text-destructive mb-4">{error}</p>
          <Button onClick={loadDashboard} variant="outline" className="gap-2">
            <RefreshCw className="h-4 w-4" />
            Повторить
          </Button>
        </CardContent>
      </Card>
    )
  }
  
  const summary = dashboard?.summary || {}
  const referrals = dashboard?.referrals || []
  const earningsHistory = dashboard?.earnings_history || []
  
  // Calculate 7-day earnings
  const weeklyEarnings = earningsHistory.reduce((sum, day) => sum + (day.amount || 0), 0)
  
  return (
    <div className="space-y-6">
      {/* VIP Header */}
      <Card className="bg-gradient-to-br from-purple-500/20 via-purple-500/10 to-background border-purple-500/20">
        <CardContent className="p-6">
          <div className="flex items-start justify-between mb-4">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-full bg-purple-500/20">
                <Star className="h-6 w-6 text-purple-400" />
              </div>
              <div>
                <h2 className="text-xl font-bold">Partner Dashboard</h2>
                <p className="text-sm text-purple-400">Level {summary.effective_level || 3} • Все уровни открыты</p>
              </div>
            </div>
            <Badge className="bg-purple-500/20 text-purple-400 border-purple-500/30">
              VIP
            </Badge>
          </div>
          
          {/* Balance */}
          <div className="mb-4">
            <p className="text-sm text-muted-foreground mb-1">Баланс</p>
            <p className="text-4xl font-bold">{formatPrice(summary.balance || 0)}</p>
          </div>
          
          {/* Actions */}
          <div className="flex gap-3">
            <Button 
              onClick={onWithdraw}
              disabled={(summary.balance || 0) < 500}
              variant="outline"
              className="flex-1 gap-2"
            >
              <Wallet className="h-4 w-4" />
              Вывести
            </Button>
            <Button 
              onClick={onShare || handleCopyLink}
              className="flex-1 gap-2 bg-gradient-to-r from-purple-500 to-purple-600"
            >
              <Share2 className="h-4 w-4" />
              Пригласить
            </Button>
          </div>
        </CardContent>
      </Card>
      
      {/* Partner Mode Switch */}
      <Card className="border-dashed overflow-hidden">
        <CardContent className="p-4">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3 min-w-0 flex-1">
              <div className={`p-2 rounded-lg transition-colors flex-shrink-0 ${
                discountMode 
                  ? 'bg-amber-500/20' 
                  : 'bg-green-500/20'
              }`}>
                {discountMode ? (
                  <Gift className="h-5 w-5 text-amber-500" />
                ) : (
                  <Coins className="h-5 w-5 text-green-500" />
                )}
              </div>
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <p className="font-medium text-sm whitespace-nowrap">
                    {discountMode ? 'Скидки' : 'Комиссии'}
                  </p>
                  <Tooltip>
                    <TooltipTrigger asChild>
                      <Info className="h-3.5 w-3.5 text-muted-foreground cursor-help flex-shrink-0" />
                    </TooltipTrigger>
                    <TooltipContent side="top" className="max-w-[250px]">
                      <p className="text-xs">
                        {discountMode 
                          ? 'Рефералы получают 15% скидку. Вы не получаете комиссию.'
                          : 'Вы получаете комиссию. Переключите, чтобы дать рефералам скидку.'}
                      </p>
                    </TooltipContent>
                  </Tooltip>
                </div>
                <p className="text-xs text-muted-foreground truncate">
                  {discountMode 
                    ? '15% скидка рефералам' 
                    : 'Комиссия с покупок'}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <span className="text-xs">
                {discountMode ? '🎁' : '💰'}
              </span>
              <Switch
                checked={discountMode}
                onCheckedChange={handleToggleMode}
                disabled={togglingMode}
                className={discountMode ? 'bg-amber-500' : ''}
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Key Metrics Grid */}
      <div className="grid grid-cols-2 gap-3">
        <Card className="bg-gradient-to-br from-green-500/10 to-transparent border-green-500/20">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <DollarSign className="h-4 w-4 text-green-500" />
              <span className="text-xs text-muted-foreground">Всего заработано</span>
            </div>
            <p className="text-2xl font-bold text-green-500">
              {formatPrice(summary.total_earned || 0)}
            </p>
          </CardContent>
        </Card>
        
        <Card className="bg-gradient-to-br from-blue-500/10 to-transparent border-blue-500/20">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="h-4 w-4 text-blue-500" />
              <span className="text-xs text-muted-foreground">За 7 дней</span>
            </div>
            <p className="text-2xl font-bold text-blue-500">
              {formatPrice(weeklyEarnings)}
            </p>
          </CardContent>
        </Card>
        
        <Card className="bg-gradient-to-br from-purple-500/10 to-transparent border-purple-500/20">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <Users className="h-4 w-4 text-purple-500" />
              <span className="text-xs text-muted-foreground">Рефералы</span>
            </div>
            <p className="text-2xl font-bold">
              <span className="text-purple-500">{summary.paying_referrals || 0}</span>
              <span className="text-muted-foreground text-lg"> / {summary.total_referrals || 0}</span>
            </p>
          </CardContent>
        </Card>
        
        <Card className="bg-gradient-to-br from-amber-500/10 to-transparent border-amber-500/20">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <Percent className="h-4 w-4 text-amber-500" />
              <span className="text-xs text-muted-foreground">Конверсия</span>
            </div>
            <p className="text-2xl font-bold text-amber-500">
              {summary.conversion_rate || 0}%
            </p>
          </CardContent>
        </Card>
      </div>
      
      {/* Earnings History */}
      {earningsHistory.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-base flex items-center gap-2">
              <BarChart3 className="h-4 w-4 text-primary" />
              Доходы за неделю
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {earningsHistory.slice(0, 7).map((day, idx) => {
                const maxAmount = Math.max(...earningsHistory.map(d => d.amount || 0))
                const barWidth = maxAmount > 0 ? ((day.amount || 0) / maxAmount) * 100 : 0
                
                return (
                  <div key={day.date || idx} className="flex items-center gap-3">
                    <span className="text-xs text-muted-foreground w-20">
                      {day.date ? new Date(day.date).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' }) : '-'}
                    </span>
                    <div className="flex-1 h-6 bg-secondary rounded overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-green-500 to-green-400 rounded"
                        style={{ width: `${barWidth}%` }}
                      />
                    </div>
                    <span className="text-sm font-medium w-24 text-right">
                      {formatPrice(day.amount || 0)}
                    </span>
                  </div>
                )
              })}
            </div>
          </CardContent>
        </Card>
      )}
      
      {/* Referrals List */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-base flex items-center gap-2">
              <Users className="h-4 w-4 text-primary" />
              Мои рефералы
            </CardTitle>
            <Badge variant="secondary">{referrals.length}</Badge>
          </div>
          <CardDescription>
            Пользователи, зарегистрированные по вашей ссылке
          </CardDescription>
        </CardHeader>
        <CardContent>
          {referrals.length > 0 ? (
            <div className="space-y-3 max-h-80 overflow-y-auto">
              {referrals.map((ref, idx) => (
                <div key={ref.telegram_id || idx} className="flex items-center justify-between py-2 border-b border-border/50 last:border-0">
                  <div className="flex items-center gap-3">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                      ref.is_paying ? 'bg-green-500/20' : 'bg-secondary'
                    }`}>
                      {ref.is_paying ? (
                        <UserCheck className="h-4 w-4 text-green-500" />
                      ) : (
                        <span className="text-sm font-medium">
                          {ref.first_name?.[0] || ref.username?.[0] || '?'}
                        </span>
                      )}
                    </div>
                    <div>
                      <p className="text-sm font-medium">
                        {ref.username || ref.first_name || `User`}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {ref.joined_at ? new Date(ref.joined_at).toLocaleDateString('ru-RU') : '-'}
                      </p>
                    </div>
                  </div>
                  <div className="text-right">
                    {ref.is_paying ? (
                      <>
                        <p className="text-sm font-medium text-green-500">
                          {formatPrice(ref.total_spent || 0)}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {ref.orders_count} заказ{ref.orders_count === 1 ? '' : ref.orders_count < 5 ? 'а' : 'ов'}
                        </p>
                      </>
                    ) : (
                      <Badge variant="secondary" className="text-xs">
                        Без покупок
                      </Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground">
              <Users className="h-10 w-10 mx-auto mb-3 opacity-50" />
              <p>Пока нет рефералов</p>
              <Button 
                onClick={handleCopyLink} 
                variant="outline" 
                size="sm" 
                className="mt-3 gap-2"
              >
                <Copy className="h-4 w-4" />
                Скопировать ссылку
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
      
      {/* Referral Link */}
      <Card className="bg-muted/50">
        <CardContent className="p-4">
          <p className="text-xs text-muted-foreground mb-2">Ваша реферальная ссылка</p>
          <div className="flex items-center gap-2">
            <code className="flex-1 text-xs bg-background p-2 rounded truncate">
              {dashboard?.referral_link || referralLink}
            </code>
            <Button size="icon" variant="ghost" onClick={handleCopyLink}>
              <Copy className="h-4 w-4" />
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

