import React, { useState, useEffect, useCallback } from 'react'
import { useAdmin } from '../hooks/useAdmin'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'
import {
  ArrowLeft,
  Settings,
  Users,
  TrendingUp,
  DollarSign,
  Percent,
  Save,
  RefreshCw,
  Star,
  UserPlus,
  ChevronDown,
  ChevronUp,
  Search,
  BarChart3
} from 'lucide-react'
import { Button } from '../components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Skeleton } from '../components/ui/skeleton'
import { Input } from '../components/ui/input'
import { Label } from '../components/ui/label'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs'
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from '../components/ui/dialog'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../components/ui/select'
import { Switch } from '../components/ui/switch'
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../components/ui/tooltip'

export default function AdminReferralPage({ onBack }) {
  const { 
    getReferralSettings, 
    updateReferralSettings, 
    getReferralDashboard, 
    getReferralPartnersCRM,
    setPartner 
  } = useAdmin()
  const { formatPrice } = useLocale()
  const { setBackButton, showPopup, hapticFeedback } = useTelegram()
  
  const [activeTab, setActiveTab] = useState('dashboard')
  const [dashboard, setDashboard] = useState(null)
  const [partners, setPartners] = useState([])
  const [totalPartners, setTotalPartners] = useState(0)
  const [sortBy, setSortBy] = useState('referral_revenue')
  const [sortOrder, setSortOrder] = useState('desc')
  const [searchQuery, setSearchQuery] = useState('')
  const [partnerType, setPartnerType] = useState('all') // 'all', 'business', 'referral'
  const [saving, setSaving] = useState(false)
  const [partnerDialog, setPartnerDialog] = useState(false)
  const [newPartnerTelegramId, setNewPartnerTelegramId] = useState('')
  const [newPartnerLevel, setNewPartnerLevel] = useState('3')
  
  // Loading and error states
  const [isLoading, setIsLoading] = useState(true)
  const [loadError, setLoadError] = useState(null)
  
  // Form state for settings
  const [formSettings, setFormSettings] = useState({
    level2_threshold: '',
    level3_threshold: '',
    level1_commission: '',
    level2_commission: '',
    level3_commission: ''
  })
  
  // Load data on mount
  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true)
      setLoadError(null)
      
      try {
        const [settingsData, dashboardData] = await Promise.all([
          getReferralSettings(),
          getReferralDashboard()
        ])
        
        setDashboard(dashboardData)
        
        // Initialize form with current settings
        const currentSettings = dashboardData?.settings || settingsData?.settings
        if (currentSettings) {
          setFormSettings({
            level2_threshold: currentSettings.level2_threshold || currentSettings.level2_threshold_usd || 250,
            level3_threshold: currentSettings.level3_threshold || currentSettings.level3_threshold_usd || 1000,
            level1_commission: currentSettings.level1_commission || currentSettings.level1_commission_percent || 20,
            level2_commission: currentSettings.level2_commission || currentSettings.level2_commission_percent || 10,
            level3_commission: currentSettings.level3_commission || currentSettings.level3_commission_percent || 5
          })
        }
      } catch (err) {
        console.error('[AdminReferralPage] Failed to load data:', err)
        setLoadError(err.message || 'Failed to load data')
      } finally {
        setIsLoading(false)
      }
    }
    
    fetchData()
    
    setBackButton({
      isVisible: true,
      onClick: onBack
    })
    
    return () => {
      setBackButton({ isVisible: false })
    }
  }, [onBack, setBackButton, getReferralSettings, getReferralDashboard])
  
  // Load partners when tab changes
  useEffect(() => {
    if (activeTab === 'partners') {
      loadPartners()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab, partnerType])
  
  // Manual reload function
  const loadData = useCallback(async () => {
    setIsLoading(true)
    setLoadError(null)
    
    try {
      const [settingsData, dashboardData] = await Promise.all([
        getReferralSettings(),
        getReferralDashboard()
      ])
      
      setDashboard(dashboardData)
      
      const currentSettings = dashboardData?.settings || settingsData?.settings
      if (currentSettings) {
        setFormSettings({
          level2_threshold: currentSettings.level2_threshold || currentSettings.level2_threshold_usd || 250,
          level3_threshold: currentSettings.level3_threshold || currentSettings.level3_threshold_usd || 1000,
          level1_commission: currentSettings.level1_commission || currentSettings.level1_commission_percent || 20,
          level2_commission: currentSettings.level2_commission || currentSettings.level2_commission_percent || 10,
          level3_commission: currentSettings.level3_commission || currentSettings.level3_commission_percent || 5
        })
      }
    } catch (err) {
      setLoadError(err.message || 'Failed to load data')
    } finally {
      setIsLoading(false)
    }
  }, [getReferralSettings, getReferralDashboard])
  
  const [loadingPartners, setLoadingPartners] = useState(false)
  
  const loadPartners = useCallback(async () => {
    setLoadingPartners(true)
    try {
      const data = await getReferralPartnersCRM(sortBy, sortOrder, 500, partnerType)
      
      if (!data) {
        setPartners([])
        setTotalPartners(0)
        return
      }
      
      setPartners(data.partners || [])
      setTotalPartners(data.total || 0)
    } catch (err) {
      // Don't show popup for initial load errors, just log
      setPartners([])
      setTotalPartners(0)
      setLoadError(err.message || 'Ошибка загрузки партнёров')
    } finally {
      setLoadingPartners(false)
    }
  }, [getReferralPartnersCRM, sortBy, sortOrder, partnerType])
  
  const handleSaveSettings = async () => {
    setSaving(true)
    try {
      await updateReferralSettings({
        level2_threshold_usd: parseFloat(formSettings.level2_threshold),
        level3_threshold_usd: parseFloat(formSettings.level3_threshold),
        level1_commission_percent: parseFloat(formSettings.level1_commission),
        level2_commission_percent: parseFloat(formSettings.level2_commission),
        level3_commission_percent: parseFloat(formSettings.level3_commission)
      })
      
      hapticFeedback('notification', 'success')
      showPopup({
        title: '✅',
        message: 'Настройки сохранены',
        buttons: [{ type: 'ok' }]
      })
      
      loadData()
    } catch (err) {
      showPopup({
        title: '❌',
        message: err.message || 'Ошибка сохранения',
        buttons: [{ type: 'ok' }]
      })
    } finally {
      setSaving(false)
    }
  }
  
  const handleSetPartnerSubmit = async () => {
    if (!newPartnerTelegramId) {
      showPopup({
        title: '❌',
        message: 'Введите Telegram ID',
        buttons: [{ type: 'ok' }]
      })
      return
    }
    
    try {
      await setPartner({
        telegram_id: parseInt(newPartnerTelegramId),
        is_partner: true,
        level_override: parseInt(newPartnerLevel)
      })
      
      hapticFeedback('notification', 'success')
      showPopup({
        title: '✅',
        message: 'Партнёр добавлен',
        buttons: [{ type: 'ok' }]
      })
      
      setPartnerDialog(false)
      setNewPartnerTelegramId('')
      loadPartners()
      loadData()
    } catch (err) {
      showPopup({
        title: '❌',
        message: err.message || 'Ошибка добавления',
        buttons: [{ type: 'ok' }]
      })
    }
  }
  
  // Optimistic update helper
  const updatePartnerOptimistically = (partnerId, updates) => {
    setPartners(prev => prev.map(p => 
      p.user_id === partnerId ? { ...p, ...updates } : p
    ))
  }
  
  const handleUpdatePartnerLevel = async (partner, newLevel) => {
    const previousLevel = partner.effective_level
    const level = parseInt(newLevel)
    
    // Optimistic update
    updatePartnerOptimistically(partner.user_id, { 
      effective_level: level,
      _loading: true 
    })
    hapticFeedback('impact', 'light')
    
    try {
      await setPartner({
        telegram_id: partner.telegram_id,
        is_partner: partner.status === 'VIP',
        level_override: level
      })
      
      // Success - remove loading state
      updatePartnerOptimistically(partner.user_id, { _loading: false })
      hapticFeedback('notification', 'success')
    } catch (err) {
      // Rollback on error
      updatePartnerOptimistically(partner.user_id, { 
        effective_level: previousLevel,
        _loading: false 
      })
      hapticFeedback('notification', 'error')
      showPopup({
        title: '❌',
        message: err.message || 'Ошибка обновления уровня',
        buttons: [{ type: 'ok' }]
      })
    }
  }
  
  // Toggle VIP Partner status with auto-set level=3
  const handleTogglePartnerStatus = async (partner) => {
    const wasVIP = partner.status === 'VIP'
    const newIsPartner = !wasVIP
    
    // Optimistic update - use 'Regular' to match API response format
    updatePartnerOptimistically(partner.user_id, { 
      status: newIsPartner ? 'VIP' : 'Regular',
      effective_level: newIsPartner ? 3 : partner.effective_level,
      _loading: true
    })
    hapticFeedback('impact', 'medium')
    
    try {
      await setPartner({
        telegram_id: partner.telegram_id,
        is_partner: newIsPartner,
        level_override: newIsPartner ? 3 : null
      })
      
      // Success - keep optimistic state, only remove loading
      updatePartnerOptimistically(partner.user_id, { _loading: false })
      hapticFeedback('notification', 'success')
      showPopup({
        title: newIsPartner ? '⭐' : '✓',
        message: newIsPartner 
          ? 'VIP-партнёр назначен (Level 3)' 
          : 'VIP-статус снят',
        buttons: [{ type: 'ok' }]
      })
      // Note: Dashboard metrics refresh removed - keep optimistic update stable
    } catch (err) {
      // Rollback on error - use 'Regular' to match API response format
      updatePartnerOptimistically(partner.user_id, { 
        status: wasVIP ? 'VIP' : 'Regular',
        effective_level: partner.effective_level,
        _loading: false 
      })
      hapticFeedback('notification', 'error')
      showPopup({
        title: '❌',
        message: err.message || 'Ошибка обновления статуса',
        buttons: [{ type: 'ok' }]
      })
    }
  }
  
  const filteredPartners = partners.filter(p => {
    if (!searchQuery) return true
    const query = searchQuery.toLowerCase()
    return (
      p.username?.toLowerCase().includes(query) ||
      p.first_name?.toLowerCase().includes(query) ||
      p.telegram_id?.toString().includes(query)
    )
  })
  
  // Loading state
  if (isLoading && !dashboard) {
    return (
      <div className="p-4 space-y-4">
        <div className="flex items-center gap-4 mb-4">
          <Button variant="ghost" size="icon" onClick={onBack} className="h-8 w-8 rounded-full">
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-lg font-bold">Реферальная система</h1>
            <p className="text-xs text-muted-foreground">Загрузка...</p>
          </div>
        </div>
        <Skeleton className="h-12 w-full rounded-xl" />
        <Skeleton className="h-32 w-full rounded-xl" />
        <Skeleton className="h-48 w-full rounded-xl" />
      </div>
    )
  }
  
  // Error state
  if (loadError && !dashboard) {
    return (
      <div className="p-4 space-y-4">
        <div className="flex items-center gap-4 mb-4">
          <Button variant="ghost" size="icon" onClick={onBack} className="h-8 w-8 rounded-full">
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-lg font-bold">Реферальная система</h1>
            <p className="text-xs text-destructive">Ошибка загрузки</p>
          </div>
        </div>
        <Card className="border-destructive/50">
          <CardContent className="p-6 text-center">
            <p className="text-destructive mb-4">{loadError}</p>
            <Button onClick={loadData} variant="outline" className="gap-2">
              <RefreshCw className="h-4 w-4" />
              Повторить
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }
  
  return (
    <div>
      {/* Header */}
      <div className="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b border-border/50 p-4">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="icon" onClick={onBack} className="h-8 w-8 rounded-full">
            <ArrowLeft className="h-5 w-5" />
          </Button>
          <div>
            <h1 className="text-lg font-bold">Реферальная система</h1>
            <p className="text-xs text-muted-foreground">Настройки и аналитика</p>
          </div>
        </div>
      </div>
      
      <div className="p-4">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="space-y-4">
          <TabsList className="grid w-full grid-cols-3">
            <TabsTrigger value="dashboard" className="gap-2">
              <BarChart3 className="h-4 w-4" />
              ROI
            </TabsTrigger>
            <TabsTrigger value="partners" className="gap-2">
              <Users className="h-4 w-4" />
              CRM
            </TabsTrigger>
            <TabsTrigger value="settings" className="gap-2">
              <Settings className="h-4 w-4" />
              Настройки
            </TabsTrigger>
          </TabsList>
          
          {/* ROI Dashboard Tab */}
          <TabsContent value="dashboard" className="space-y-4">
            {/* Key Metrics */}
            <div className="grid grid-cols-2 gap-3">
              <Card className="bg-gradient-to-br from-green-500/10 to-transparent border-green-500/20">
                <CardContent className="p-4">
                  <p className="text-xs text-muted-foreground">Оборот рефералов</p>
                  <p className="text-2xl font-bold text-green-500">
                    {formatPrice(dashboard?.roi?.total_referral_revenue || 0)}
                  </p>
                </CardContent>
              </Card>
              
              <Card className="bg-gradient-to-br from-red-500/10 to-transparent border-red-500/20">
                <CardContent className="p-4">
                  <p className="text-xs text-muted-foreground">Выплачено</p>
                  <p className="text-2xl font-bold text-red-500">
                    {formatPrice(dashboard?.roi?.total_payouts || 0)}
                  </p>
                </CardContent>
              </Card>
              
              <Card className="bg-gradient-to-br from-blue-500/10 to-transparent border-blue-500/20">
                <CardContent className="p-4">
                  <p className="text-xs text-muted-foreground">Net Profit</p>
                  <p className="text-2xl font-bold text-blue-500">
                    {formatPrice(dashboard?.roi?.net_profit || 0)}
                  </p>
                </CardContent>
              </Card>
              
              <Card className="bg-gradient-to-br from-purple-500/10 to-transparent border-purple-500/20">
                <CardContent className="p-4">
                  <p className="text-xs text-muted-foreground">Маржа</p>
                  <p className="text-2xl font-bold text-purple-500">
                    {dashboard?.roi?.margin_percent || 100}%
                  </p>
                </CardContent>
              </Card>
            </div>
            
            {/* Partners Stats */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Партнёры</CardTitle>
              </CardHeader>
              <CardContent className="grid grid-cols-3 gap-4 text-center">
                <div>
                  <p className="text-2xl font-bold">{dashboard?.partners?.active || 0}</p>
                  <p className="text-xs text-muted-foreground">Активные</p>
                </div>
                <div>
                  <p className="text-2xl font-bold">{dashboard?.partners?.total || 0}</p>
                  <p className="text-xs text-muted-foreground">Всего</p>
                </div>
                <div>
                  <p className="text-2xl font-bold text-purple-500">{dashboard?.partners?.vip || 0}</p>
                  <p className="text-xs text-muted-foreground">VIP</p>
                </div>
              </CardContent>
            </Card>
            
            {/* Current Settings Display */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Текущие настройки</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Level 1</span>
                  <span className="font-medium">Мгновенно • {dashboard?.settings?.level1_commission}%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Level 2</span>
                  <span className="font-medium">${dashboard?.settings?.level2_threshold} • {dashboard?.settings?.level2_commission}%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Level 3</span>
                  <span className="font-medium">${dashboard?.settings?.level3_threshold} • {dashboard?.settings?.level3_commission}%</span>
                </div>
              </CardContent>
            </Card>
          </TabsContent>
          
          {/* Partners CRM Tab */}
          <TabsContent value="partners" className="space-y-4">
            {/* Partner Type Filter */}
            <div className="flex gap-2">
              <Button
                variant={partnerType === 'all' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setPartnerType('all')}
                className="flex-1"
              >
                Все
              </Button>
              <Button
                variant={partnerType === 'business' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setPartnerType('business')}
                className="flex-1 gap-1"
              >
                <Star className="h-3 w-3" /> VIP
              </Button>
              <Button
                variant={partnerType === 'referral' ? 'default' : 'outline'}
                size="sm"
                onClick={() => setPartnerType('referral')}
                className="flex-1"
              >
                Программа
              </Button>
            </div>
            
            {/* Search and Add */}
            <div className="flex gap-2">
              <div className="relative flex-1">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Поиск по имени или ID..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10"
                />
              </div>
              {partnerType === 'business' && (
                <Button onClick={() => setPartnerDialog(true)} className="gap-2">
                  <UserPlus className="h-4 w-4" />
                  VIP
                </Button>
              )}
            </div>
            
            {/* Sort Options */}
            <div className="flex gap-2 overflow-x-auto pb-2">
              {[
                { value: 'referral_revenue', label: 'Оборот' },
                { value: 'total_earned', label: 'Заработок' },
                { value: 'paying_referrals', label: 'Покупатели' },
                { value: 'conversion_rate', label: 'Конверсия' }
              ].map((option) => (
                <Button
                  key={option.value}
                  variant={sortBy === option.value ? 'default' : 'outline'}
                  size="sm"
                  onClick={() => {
                    if (sortBy === option.value) {
                      setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')
                    } else {
                      setSortBy(option.value)
                      setSortOrder('desc')
                    }
                  }}
                  className="gap-1 whitespace-nowrap"
                >
                  {option.label}
                  {sortBy === option.value && (
                    sortOrder === 'desc' ? <ChevronDown className="h-3 w-3" /> : <ChevronUp className="h-3 w-3" />
                  )}
                </Button>
              ))}
            </div>
            
            {/* Partners Table */}
            <div className="space-y-2">
              {loadingPartners ? (
                <div className="space-y-2">
                  <Skeleton className="h-32 w-full rounded-xl" />
                  <Skeleton className="h-32 w-full rounded-xl" />
                </div>
              ) : (
                <>
                  <div className="flex items-center justify-between">
                    <p className="text-xs text-muted-foreground">
                      Показано: {filteredPartners.length} из {totalPartners}
                    </p>
                  </div>
                  
                  {filteredPartners.length > 0 ? (
                    <TooltipProvider>
                    {filteredPartners.map((partner) => (
                      <Card key={partner.user_id} className="overflow-hidden">
                        <CardContent className="p-4">
                          <div className="flex items-start justify-between mb-3 gap-2">
                            <div className="flex items-center gap-2 min-w-0 flex-1">
                              <div className={`w-10 h-10 rounded-full flex-shrink-0 flex items-center justify-center ${
                                partner.status === 'VIP' 
                                  ? 'bg-purple-500/20' 
                                  : 'bg-primary/10'
                              }`}>
                                <span className="text-lg font-bold">
                                  {partner.first_name?.[0] || partner.username?.[0] || '?'}
                                </span>
                              </div>
                              <div className="min-w-0 flex-1">
                                <a 
                                  href={partner.username 
                                    ? `https://t.me/${partner.username}`
                                    : `tg://user?id=${partner.telegram_id}`
                                  }
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="font-medium flex items-center gap-2 hover:text-primary truncate"
                                >
                                  {partner.username ? `@${partner.username}` : partner.first_name || `User`}
                                </a>
                                <p className="text-xs text-muted-foreground truncate">
                                  ID: {partner.telegram_id}
                                </p>
                              </div>
                            </div>
                            
                            {/* VIP Toggle + Level Override */}
                            <div className={`flex items-center gap-1 flex-shrink-0 transition-opacity ${partner._loading ? 'opacity-50 pointer-events-none' : ''}`}>
                              {/* VIP Partner Toggle */}
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <div className="flex items-center gap-1">
                                    <Switch
                                      key={`switch-${partner.user_id}-${partner.status}`}
                                      checked={partner.status === 'VIP'}
                                      onCheckedChange={() => handleTogglePartnerStatus(partner)}
                                      disabled={partner._loading}
                                      className={partner.status === 'VIP' ? 'bg-purple-500' : ''}
                                    />
                                    {partner.status === 'VIP' && (
                                      <Star className={`h-4 w-4 text-purple-400 ${partner._loading ? 'animate-pulse' : ''}`} />
                                    )}
                                  </div>
                                </TooltipTrigger>
                                <TooltipContent side="bottom">
                                  <p>
                                    {partner.status === 'VIP' 
                                      ? 'VIP: доступ к Dashboard' 
                                      : 'Сделать VIP (Level 3)'}
                                  </p>
                                </TooltipContent>
                              </Tooltip>
                              
                              {/* Level Override */}
                              <Tooltip>
                                <TooltipTrigger asChild>
                                  <div>
                                    <Select
                                      value={partner.effective_level?.toString() || '0'}
                                      onValueChange={(value) => handleUpdatePartnerLevel(partner, value)}
                                      disabled={partner._loading}
                                    >
                                      <SelectTrigger className={`w-[68px] h-8 text-xs px-2 ${partner._loading ? 'animate-pulse' : ''}`}>
                                        <SelectValue />
                                      </SelectTrigger>
                                      <SelectContent>
                                        <SelectItem value="0">L0 (0%)</SelectItem>
                                        <SelectItem value="1">L1 (20%)</SelectItem>
                                        <SelectItem value="2">L2 (+10%)</SelectItem>
                                        <SelectItem value="3">L3 (+5%)</SelectItem>
                                      </SelectContent>
                                    </Select>
                                  </div>
                                </TooltipTrigger>
                                <TooltipContent side="bottom">
                                  <p>
                                    Принудительный уровень комиссии
                                  </p>
                                </TooltipContent>
                              </Tooltip>
                            </div>
                          </div>
                          
                          <div className="grid grid-cols-4 gap-2 text-center text-xs">
                            <div>
                              <p className="font-bold text-primary">{partner.total_referrals}</p>
                              <p className="text-muted-foreground">Регистр.</p>
                            </div>
                            <div>
                              <p className="font-bold text-green-500">{partner.paying_referrals}</p>
                              <p className="text-muted-foreground">Покупат.</p>
                            </div>
                            <div>
                              <p className="font-bold text-blue-500">{partner.conversion_rate}%</p>
                              <p className="text-muted-foreground">Конверсия</p>
                            </div>
                            <div>
                              <p className="font-bold">{formatPrice(partner.referral_revenue)}</p>
                              <p className="text-muted-foreground">Оборот</p>
                            </div>
                          </div>
                          
                          <div className="flex justify-between items-center mt-3 pt-3 border-t border-border/50 text-xs">
                            <span className="text-muted-foreground">
                              Заработано: <span className="text-green-500 font-medium">{formatPrice(partner.total_earned)}</span>
                            </span>
                            <span className="text-muted-foreground">
                              Баланс: <span className="font-medium">{formatPrice(partner.current_balance)}</span>
                            </span>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                    </TooltipProvider>
                  ) : (
                    <div className="text-center py-8 text-muted-foreground">
                      {partners.length === 0 
                        ? 'Партнёры не найдены. Проверьте консоль для отладки.' 
                        : `Нет результатов по фильтру "${searchQuery}". Всего партнёров: ${partners.length}`}
                    </div>
                  )}
                </>
              )}
            </div>
          </TabsContent>
          
          {/* Settings Tab */}
          <TabsContent value="settings" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <DollarSign className="h-4 w-4" />
                  Пороги разблокировки
                </CardTitle>
                <CardDescription>
                  Level 1 открывается мгновенно при первой покупке
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Level 1 (мгновенный)</Label>
                  <Input value="$0 — При первой покупке" disabled className="bg-muted" />
                </div>
                
                <div className="space-y-2">
                  <Label>Level 2 (оборот USD)</Label>
                  <div className="relative">
                    <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      type="number"
                      value={formSettings.level2_threshold}
                      onChange={(e) => setFormSettings(prev => ({ ...prev, level2_threshold: e.target.value }))}
                      className="pl-10"
                      placeholder="250"
                    />
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label>Level 3 (оборот USD)</Label>
                  <div className="relative">
                    <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                    <Input
                      type="number"
                      value={formSettings.level3_threshold}
                      onChange={(e) => setFormSettings(prev => ({ ...prev, level3_threshold: e.target.value }))}
                      className="pl-10"
                      placeholder="1000"
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Percent className="h-4 w-4" />
                  Комиссии
                </CardTitle>
                <CardDescription>
                  Процент от покупок рефералов
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="space-y-2">
                  <Label>Level 1 (%)</Label>
                  <div className="relative">
                    <Input
                      type="number"
                      value={formSettings.level1_commission}
                      onChange={(e) => setFormSettings(prev => ({ ...prev, level1_commission: e.target.value }))}
                      placeholder="20"
                      min="0"
                      max="100"
                    />
                    <Percent className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label>Level 2 (%)</Label>
                  <div className="relative">
                    <Input
                      type="number"
                      value={formSettings.level2_commission}
                      onChange={(e) => setFormSettings(prev => ({ ...prev, level2_commission: e.target.value }))}
                      placeholder="10"
                      min="0"
                      max="100"
                    />
                    <Percent className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  </div>
                </div>
                
                <div className="space-y-2">
                  <Label>Level 3 (%)</Label>
                  <div className="relative">
                    <Input
                      type="number"
                      value={formSettings.level3_commission}
                      onChange={(e) => setFormSettings(prev => ({ ...prev, level3_commission: e.target.value }))}
                      placeholder="5"
                      min="0"
                      max="100"
                    />
                    <Percent className="absolute right-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                  </div>
                </div>
              </CardContent>
            </Card>
            
            <Button
              onClick={handleSaveSettings}
              disabled={saving}
              className="w-full gap-2"
            >
              {saving ? <RefreshCw className="h-4 w-4 animate-spin" /> : <Save className="h-4 w-4" />}
              {saving ? 'Сохранение...' : 'Сохранить настройки'}
            </Button>
          </TabsContent>
        </Tabs>
      </div>
      
      {/* Add Partner Dialog */}
      <Dialog open={partnerDialog} onOpenChange={setPartnerDialog}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Добавить VIP-партнёра</DialogTitle>
            <DialogDescription>
              Блогеру, школе или арбитражнику можно сразу открыть все уровни
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label>Telegram ID</Label>
              <Input
                type="number"
                placeholder="123456789"
                value={newPartnerTelegramId}
                onChange={(e) => setNewPartnerTelegramId(e.target.value)}
              />
            </div>
            
            <div className="space-y-2">
              <Label>Уровень доступа</Label>
              <Select value={newPartnerLevel} onValueChange={setNewPartnerLevel}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="1">Level 1 (20%)</SelectItem>
                  <SelectItem value="2">Level 2 (20% + 10%)</SelectItem>
                  <SelectItem value="3">Level 3 (20% + 10% + 5%) — Полный доступ</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>
          
          <DialogFooter>
            <Button variant="outline" onClick={() => setPartnerDialog(false)}>
              Отмена
            </Button>
            <Button onClick={handleSetPartnerSubmit}>
              Добавить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

