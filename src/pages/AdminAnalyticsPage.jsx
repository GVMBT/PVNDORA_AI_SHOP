import React, { useState, useEffect } from 'react'
import { useAdmin } from '../hooks/useAdmin'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'
import { 
  ArrowLeft, 
  BarChart2, 
  DollarSign, 
  ShoppingBag, 
  TrendingUp, 
  Users,
  Target,
  Percent,
  Award,
  RefreshCcw
} from 'lucide-react'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Skeleton } from '../components/ui/skeleton'
import { Separator } from '../components/ui/separator'

export default function AdminAnalyticsPage({ onBack }) {
  const { loading } = useAdmin()
  const { formatPrice } = useLocale()
  const { showAlert, hapticFeedback } = useTelegram()
  
  const [metrics, setMetrics] = useState(null)
  const [days, setDays] = useState(30)
  const [activeTab, setActiveTab] = useState('overview')
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    loadMetrics()
  }, [days])

  const loadMetrics = async () => {
    setRefreshing(true)
    try {
      const headers = {
        'Content-Type': 'application/json'
      }
      
      // Try Telegram initData first (Mini App)
      const initData = window.Telegram?.WebApp?.initData || ''
      if (initData) {
        headers['X-Init-Data'] = initData
      } else {
        // Fallback to Bearer token (web session)
        const sessionToken = window.localStorage?.getItem('pvndora_session')
        if (sessionToken) {
          headers['Authorization'] = `Bearer ${sessionToken}`
        }
      }
      
      const response = await fetch(`/api/admin/metrics/business?days=${days}`, { headers })
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || errorData.error || 'Failed to load metrics')
      }
      const data = await response.json()
      setMetrics(data)
    } catch (err) {
      await showAlert(`Error: ${err.message}`)
    } finally {
      setRefreshing(false)
    }
  }

  const StatCard = ({ title, value, subtitle, icon: Icon, color = "primary", trend }) => (
    <Card>
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{title}</p>
            <h3 className="text-2xl font-bold">{value}</h3>
            {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
          </div>
          <div className={`h-10 w-10 rounded-lg bg-${color}/10 flex items-center justify-center text-${color}`}>
            <Icon className="h-5 w-5" />
          </div>
        </div>
        {trend !== undefined && (
          <div className={`mt-2 text-xs font-medium ${trend >= 0 ? 'text-green-500' : 'text-red-500'}`}>
            {trend >= 0 ? '↑' : '↓'} {Math.abs(trend)}% vs prev period
          </div>
        )}
      </CardContent>
    </Card>
  )

  const tabs = [
    { id: 'overview', label: 'Обзор' },
    { id: 'products', label: 'Товары' },
    { id: 'referrals', label: 'Рефералы' },
    { id: 'retention', label: 'Удержание' }
  ]

  return (
    <div className="pb-24">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b border-border/50 p-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="icon" onClick={onBack} className="h-8 w-8">
              <ArrowLeft className="h-5 w-5" />
            </Button>
            <h1 className="text-lg font-bold">Бизнес-метрики</h1>
          </div>
          <Button 
            variant="ghost" 
            size="icon" 
            onClick={() => { hapticFeedback('impact', 'light'); loadMetrics() }}
            disabled={refreshing}
          >
            <RefreshCcw className={`h-5 w-5 ${refreshing ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      <div className="p-4 space-y-6">
        {/* Period Selector */}
        <div className="flex p-1 bg-secondary/50 rounded-lg">
          {[7, 30, 90].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`flex-1 py-2 text-sm font-medium rounded-md transition-all ${
                days === d
                  ? 'bg-background shadow-sm text-foreground'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {d} дней
            </button>
          ))}
        </div>

        {/* Tab Navigation */}
        <div className="flex gap-2 overflow-x-auto pb-2">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 text-sm font-medium rounded-full whitespace-nowrap transition-all ${
                activeTab === tab.id
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-secondary text-muted-foreground hover:text-foreground'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {refreshing && !metrics ? (
          <div className="space-y-4">
            <Skeleton className="h-24 w-full rounded-xl" />
            <Skeleton className="h-24 w-full rounded-xl" />
            <Skeleton className="h-48 w-full rounded-xl" />
          </div>
        ) : metrics ? (
          <>
            {/* Overview Tab */}
            {activeTab === 'overview' && (
              <div className="space-y-4">
                <div className="grid gap-4">
                  <StatCard 
                    title="Выручка" 
                    value={formatPrice(metrics.summary?.total_revenue || 0)}
                    subtitle={`Ср. в день: ${formatPrice(metrics.summary?.avg_daily_revenue || 0)}`}
                    icon={DollarSign}
                    color="green-500"
                  />
                  <div className="grid grid-cols-2 gap-4">
                    <StatCard 
                      title="Заказы" 
                      value={metrics.summary?.total_orders || 0}
                      icon={ShoppingBag}
                    />
                    <StatCard 
                      title="Новые" 
                      value={metrics.summary?.total_new_users || 0}
                      icon={Users}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <StatCard 
                      title="Конверсия" 
                      value={`${metrics.summary?.avg_conversion_rate?.toFixed(1) || 0}%`}
                      icon={Target}
                    />
                    <StatCard 
                      title="Ср. чек" 
                      value={formatPrice(metrics.summary?.avg_order_value || 0)}
                      icon={TrendingUp}
                    />
                  </div>
                </div>

                {/* Daily Chart Preview */}
                {metrics.daily_metrics?.length > 0 && (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium">Выручка по дням</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-end gap-1 h-24">
                        {metrics.daily_metrics.slice(0, 14).reverse().map((day, idx) => (
                          <div 
                            key={idx}
                            className="flex-1 bg-primary/20 hover:bg-primary/40 rounded-t transition-all cursor-pointer"
                            style={{ 
                              height: `${Math.max(4, (day.revenue / Math.max(...metrics.daily_metrics.map(d => d.revenue || 1))) * 100)}%` 
                            }}
                            title={`${day.date}: ${formatPrice(day.revenue)}`}
                          />
                        ))}
                      </div>
                      <div className="flex justify-between mt-2 text-xs text-muted-foreground">
                        <span>14 дней назад</span>
                        <span>Сегодня</span>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            )}

            {/* Products Tab */}
            {activeTab === 'products' && (
              <div className="space-y-4">
                {metrics.product_metrics?.length > 0 ? (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium flex items-center gap-2">
                        <BarChart2 className="h-4 w-4 text-primary" />
                        Топ продуктов
                      </CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-4">
                      {metrics.product_metrics.map((product, idx) => (
                        <div key={idx} className="flex items-center justify-between">
                          <div className="flex items-center gap-3">
                            <span className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-medium ${
                              idx === 0 ? 'bg-yellow-500/20 text-yellow-600' :
                              idx === 1 ? 'bg-gray-300/20 text-gray-500' :
                              idx === 2 ? 'bg-orange-500/20 text-orange-600' :
                              'bg-secondary text-muted-foreground'
                            }`}>
                              {idx + 1}
                            </span>
                            <div>
                              <span className="font-medium text-sm">{product.name}</span>
                              <div className="flex gap-2 text-xs text-muted-foreground">
                                <span>{product.completed_orders || 0} продаж</span>
                                {product.avg_rating && (
                                  <span>★ {product.avg_rating.toFixed(1)}</span>
                                )}
                              </div>
                            </div>
                          </div>
                          <div className="text-right">
                            <p className="font-bold text-sm">{formatPrice(product.total_revenue || 0)}</p>
                            <p className="text-xs text-muted-foreground">{product.current_stock || 0} шт</p>
                          </div>
                        </div>
                      ))}
                    </CardContent>
                  </Card>
                ) : (
                  <Card>
                    <CardContent className="py-8 text-center text-muted-foreground">
                      Нет данных по продуктам
                    </CardContent>
                  </Card>
                )}
              </div>
            )}

            {/* Referrals Tab */}
            {activeTab === 'referrals' && (
              <div className="space-y-4">
                {metrics.referral_metrics ? (
                  <>
                    <div className="grid grid-cols-2 gap-4">
                      <StatCard 
                        title="Партнёры" 
                        value={metrics.referral_metrics.total_active_referrers || 0}
                        icon={Users}
                      />
                      <StatCard 
                        title="Рефералы" 
                        value={metrics.referral_metrics.total_referred_users || 0}
                        icon={Award}
                      />
                    </div>
                    <StatCard 
                      title="Выплачено бонусов" 
                      value={formatPrice(metrics.referral_metrics.total_bonuses_paid || 0)}
                      subtitle={`${metrics.referral_metrics.total_bonus_transactions || 0} транзакций`}
                      icon={DollarSign}
                      color="green-500"
                    />
                    
                    <Card>
                      <CardHeader className="pb-2">
                        <CardTitle className="text-sm font-medium">По уровням</CardTitle>
                      </CardHeader>
                      <CardContent className="space-y-3">
                        <div className="flex justify-between items-center">
                          <span className="text-sm">Уровень 1 (5%)</span>
                          <Badge variant="outline">{metrics.referral_metrics.level1_users || 0}</Badge>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-sm">Уровень 2 (+2%)</span>
                          <Badge variant="outline">{metrics.referral_metrics.level2_users || 0}</Badge>
                        </div>
                        <div className="flex justify-between items-center">
                          <span className="text-sm">Уровень 3 (+1%)</span>
                          <Badge variant="outline">{metrics.referral_metrics.level3_users || 0}</Badge>
                        </div>
                      </CardContent>
                    </Card>

                    {metrics.referral_metrics.top_referrers && (
                      <Card>
                        <CardHeader className="pb-2">
                          <CardTitle className="text-sm font-medium">Топ партнёры</CardTitle>
                        </CardHeader>
                        <CardContent className="space-y-3">
                          {(typeof metrics.referral_metrics.top_referrers === 'string' 
                            ? JSON.parse(metrics.referral_metrics.top_referrers) 
                            : metrics.referral_metrics.top_referrers
                          )?.slice(0, 5).map((ref, idx) => (
                            <div key={idx} className="flex justify-between items-center">
                              <div className="flex items-center gap-2">
                                <span className="text-xs text-muted-foreground">#{idx + 1}</span>
                                <span className="text-sm font-medium">
                                  @{ref.username || `user_${ref.telegram_id}`}
                                </span>
                              </div>
                              <div className="text-right">
                                <p className="text-sm font-bold">{formatPrice(ref.total_referral_earnings || 0)}</p>
                                <p className="text-xs text-muted-foreground">{ref.total_referrals || 0} реф.</p>
                              </div>
                            </div>
                          ))}
                        </CardContent>
                      </Card>
                    )}
                  </>
                ) : (
                  <Card>
                    <CardContent className="py-8 text-center text-muted-foreground">
                      Нет данных по рефералам
                    </CardContent>
                  </Card>
                )}
              </div>
            )}

            {/* Retention Tab */}
            {activeTab === 'retention' && (
              <div className="space-y-4">
                {metrics.retention_cohorts?.length > 0 ? (
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium">Когортный анализ</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="overflow-x-auto">
                        <table className="w-full text-xs">
                          <thead>
                            <tr className="border-b">
                              <th className="text-left py-2 font-medium">Когорта</th>
                              <th className="text-center py-2 font-medium">Размер</th>
                              <th className="text-center py-2 font-medium">W0</th>
                              <th className="text-center py-2 font-medium">W1</th>
                              <th className="text-center py-2 font-medium">W2</th>
                              <th className="text-center py-2 font-medium">W3</th>
                            </tr>
                          </thead>
                          <tbody>
                            {metrics.retention_cohorts.slice(0, 6).map((cohort, idx) => (
                              <tr key={idx} className="border-b border-border/50">
                                <td className="py-2 text-muted-foreground">
                                  {new Date(cohort.cohort_week).toLocaleDateString('ru', { day: '2-digit', month: 'short' })}
                                </td>
                                <td className="text-center py-2">{cohort.cohort_size}</td>
                                <td className={`text-center py-2 ${cohort.week0 > 0 ? 'bg-green-500/20' : ''}`}>
                                  {cohort.cohort_size > 0 ? Math.round((cohort.week0 / cohort.cohort_size) * 100) : 0}%
                                </td>
                                <td className={`text-center py-2 ${cohort.week1 > 0 ? 'bg-green-500/10' : ''}`}>
                                  {cohort.cohort_size > 0 ? Math.round((cohort.week1 / cohort.cohort_size) * 100) : 0}%
                                </td>
                                <td className={`text-center py-2 ${cohort.week2 > 0 ? 'bg-green-500/10' : ''}`}>
                                  {cohort.cohort_size > 0 ? Math.round((cohort.week2 / cohort.cohort_size) * 100) : 0}%
                                </td>
                                <td className={`text-center py-2 ${cohort.week3 > 0 ? 'bg-green-500/10' : ''}`}>
                                  {cohort.cohort_size > 0 ? Math.round((cohort.week3 / cohort.cohort_size) * 100) : 0}%
                                </td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                      <p className="text-xs text-muted-foreground mt-3">
                        W0-W3: % пользователей, сделавших покупку в неделю 0-3 после регистрации
                      </p>
                    </CardContent>
                  </Card>
                ) : (
                  <Card>
                    <CardContent className="py-8 text-center text-muted-foreground">
                      Недостаточно данных для когортного анализа
                    </CardContent>
                  </Card>
                )}
              </div>
            )}
          </>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-center space-y-4">
            <div className="p-4 rounded-full bg-secondary text-muted-foreground">
              <BarChart2 className="h-12 w-12" />
            </div>
            <p className="text-muted-foreground">Нет данных</p>
            <Button onClick={loadMetrics}>Обновить</Button>
          </div>
        )}
      </div>
    </div>
  )
}
