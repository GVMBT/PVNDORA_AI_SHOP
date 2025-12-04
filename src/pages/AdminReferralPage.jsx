import React, { useState, useEffect, useCallback } from 'react'
import { useAdminApi } from '../hooks/useAdminApi'
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

export default function AdminReferralPage({ onBack }) {
  const { get, put, post, loading } = useAdminApi()
  const { formatPrice } = useLocale()
  const { setBackButton, showPopup, hapticFeedback } = useTelegram()
  
  const [activeTab, setActiveTab] = useState('dashboard')
  const [settings, setSettings] = useState(null)
  const [dashboard, setDashboard] = useState(null)
  const [partners, setPartners] = useState([])
  const [totalPartners, setTotalPartners] = useState(0)
  const [sortBy, setSortBy] = useState('referral_revenue')
  const [sortOrder, setSortOrder] = useState('desc')
  const [searchQuery, setSearchQuery] = useState('')
  const [saving, setSaving] = useState(false)
  const [partnerDialog, setPartnerDialog] = useState(false)
  const [selectedPartner, setSelectedPartner] = useState(null)
  const [newPartnerTelegramId, setNewPartnerTelegramId] = useState('')
  const [newPartnerLevel, setNewPartnerLevel] = useState('3')
  
  // Form state for settings
  const [formSettings, setFormSettings] = useState({
    level2_threshold: '',
    level3_threshold: '',
    level1_commission: '',
    level2_commission: '',
    level3_commission: ''
  })
  
  useEffect(() => {
    loadData()
    
    setBackButton({
      isVisible: true,
      onClick: onBack
    })
    
    return () => {
      setBackButton({ isVisible: false })
    }
  }, [])
  
  useEffect(() => {
    if (activeTab === 'partners') {
      loadPartners()
    }
  }, [sortBy, sortOrder, activeTab])
  
  const loadData = async () => {
    try {
      const [settingsData, dashboardData] = await Promise.all([
        get('/referral/settings'),
        get('/referral/dashboard')
      ])
      
      setSettings(settingsData.settings)
      setDashboard(dashboardData)
      
      // Initialize form with current settings
      if (settingsData.settings) {
        setFormSettings({
          level2_threshold: settingsData.settings.level2_threshold_usd || 250,
          level3_threshold: settingsData.settings.level3_threshold_usd || 1000,
          level1_commission: settingsData.settings.level1_commission_percent || 20,
          level2_commission: settingsData.settings.level2_commission_percent || 10,
          level3_commission: settingsData.settings.level3_commission_percent || 5
        })
      }
    } catch (err) {
      console.error('Failed to load referral data:', err)
    }
  }
  
  const loadPartners = useCallback(async () => {
    try {
      const data = await get(`/referral/partners-crm?sort_by=${sortBy}&sort_order=${sortOrder}&limit=50`)
      setPartners(data.partners || [])
      setTotalPartners(data.total || 0)
    } catch (err) {
      console.error('Failed to load partners:', err)
    }
  }, [get, sortBy, sortOrder])
  
  const handleSaveSettings = async () => {
    setSaving(true)
    try {
      await put('/referral/settings', {
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
  
  const handleSetPartner = async () => {
    if (!newPartnerTelegramId) {
      showPopup({
        title: '❌',
        message: 'Введите Telegram ID',
        buttons: [{ type: 'ok' }]
      })
      return
    }
    
    try {
      await post('/partners/set', {
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
  
  const handleUpdatePartnerLevel = async (partner, newLevel) => {
    try {
      await post('/partners/set', {
        telegram_id: partner.telegram_id,
        is_partner: true,
        level_override: parseInt(newLevel)
      })
      
      hapticFeedback('notification', 'success')
      loadPartners()
    } catch (err) {
      showPopup({
        title: '❌',
        message: err.message || 'Ошибка обновления',
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
  
  if (loading && !dashboard) {
    return (
      <div className="p-4 space-y-4">
        <Skeleton className="h-12 w-full rounded-xl" />
        <Skeleton className="h-32 w-full rounded-xl" />
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
              <Button onClick={() => setPartnerDialog(true)} className="gap-2">
                <UserPlus className="h-4 w-4" />
                VIP
              </Button>
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
              <p className="text-xs text-muted-foreground">
                Найдено: {filteredPartners.length} из {totalPartners}
              </p>
              
              {filteredPartners.map((partner) => (
                <Card key={partner.user_id} className="overflow-hidden">
                  <CardContent className="p-4">
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                          <span className="text-lg font-bold">
                            {partner.first_name?.[0] || partner.username?.[0] || '?'}
                          </span>
                        </div>
                        <div>
                          <p className="font-medium flex items-center gap-2">
                            {partner.username || partner.first_name || `User ${partner.telegram_id}`}
                            {partner.status === 'VIP' && (
                              <Badge className="bg-purple-500/20 text-purple-400 border-purple-500/30 text-xs">
                                <Star className="h-3 w-3 mr-1" /> VIP
                              </Badge>
                            )}
                          </p>
                          <p className="text-xs text-muted-foreground">
                            ID: {partner.telegram_id} • Level {partner.effective_level}
                          </p>
                        </div>
                      </div>
                      
                      <Select
                        value={partner.effective_level?.toString()}
                        onValueChange={(value) => handleUpdatePartnerLevel(partner, value)}
                      >
                        <SelectTrigger className="w-20 h-8">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="1">L1</SelectItem>
                          <SelectItem value="2">L2</SelectItem>
                          <SelectItem value="3">L3</SelectItem>
                        </SelectContent>
                      </Select>
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
              
              {filteredPartners.length === 0 && (
                <div className="text-center py-8 text-muted-foreground">
                  Партнёры не найдены
                </div>
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
            <Button onClick={handleSetPartner}>
              Добавить
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}

