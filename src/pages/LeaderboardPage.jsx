import React, { useState, useEffect } from 'react'
import { useLeaderboard, useApi } from '../hooks/useApi'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'
import { ArrowLeft, Trophy, Medal, Award, TrendingUp, Info, Share2, Copy } from 'lucide-react'
import { Button } from '../components/ui/button'
import { Card, CardContent } from '../components/ui/card'
import { Badge } from '../components/ui/badge'
import { Skeleton } from '../components/ui/skeleton'

export default function LeaderboardPage({ onBack }) {
  const { getLeaderboard, loading, error } = useLeaderboard()
  const { post } = useApi()
  const { t, formatPrice } = useLocale()
  const { setBackButton, user, showPopup } = useTelegram()
  
  const [leaderboard, setLeaderboard] = useState([])
  const [userRank, setUserRank] = useState(null)
  const [userSaved, setUserSaved] = useState(0)
  const [shareLoading, setShareLoading] = useState(false)
  
  useEffect(() => {
    loadLeaderboard()
    
    setBackButton({
      isVisible: true,
      onClick: onBack
    })
    
    return () => {
      setBackButton({ isVisible: false })
    }
  }, [])
  
  const loadLeaderboard = async () => {
    try {
      const data = await getLeaderboard()
      setLeaderboard(data.leaderboard || [])
      setUserRank(data.user_rank)
      setUserSaved(data.user_saved || 0)
    } catch (err) {
      console.error('Failed to load leaderboard:', err)
    }
  }

  const handleShare = async () => {
    setShareLoading(true)
    try {
      // 1. Generate prepared message
      const { prepared_message_id } = await post('/referral/share-link')
      
      // 2. Use shareMessage if supported
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
             showPopup({
                title: t('common.error'),
                message: "Sharing not supported",
                buttons: [{ type: 'ok' }]
             })
          }
      }
    } catch (err) {
      console.error('Share failed:', err)
      
      // Fallback: Copy link
      const refLink = `https://t.me/pvndora_ai_bot?start=ref_${user?.id}`
      if (navigator.clipboard) {
        await navigator.clipboard.writeText(refLink)
        showPopup({
           title: t('common.success'),
           message: t('leaderboard.linkCopied'),
           buttons: [{ type: 'ok' }]
        })
      }
    } finally {
      setShareLoading(false)
    }
  }
  
  const handleCopyLink = async () => {
    const refLink = `https://t.me/pvndora_ai_bot?start=ref_${user?.id}`
    try {
        await navigator.clipboard.writeText(refLink)
        // Show toast/notification (using popup for now)
         showPopup({
           title: t('common.success'),
           message: t('leaderboard.linkCopied'),
           buttons: [{ type: 'ok' }]
        })
    } catch (e) {
        console.error('Copy failed', e)
    }
  }
  
  const getRankIcon = (rank) => {
    if (rank === 1) return <Trophy className="h-6 w-6 text-yellow-500 fill-yellow-500/20" />
    if (rank === 2) return <Medal className="h-6 w-6 text-gray-400 fill-gray-400/20" />
    if (rank === 3) return <Award className="h-6 w-6 text-amber-700 fill-amber-700/20" />
    return <span className="font-bold text-muted-foreground w-6 text-center">#{rank}</span>
  }
  
  const getRankStyles = (rank) => {
    if (rank === 1) return 'bg-gradient-to-r from-yellow-500/10 to-transparent border-yellow-500/20'
    if (rank === 2) return 'bg-gradient-to-r from-gray-400/10 to-transparent border-gray-400/20'
    if (rank === 3) return 'bg-gradient-to-r from-amber-700/10 to-transparent border-amber-700/20'
    return 'bg-card/50'
  }
  
  return (
    <div className="pb-24">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-background/80 backdrop-blur-md border-b border-border/50 p-4 flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={onBack} className="h-8 w-8 rounded-full">
          <ArrowLeft className="h-5 w-5" />
        </Button>
        <div>
          <h1 className="text-lg font-bold">{t('leaderboard.title')}</h1>
          <p className="text-xs text-muted-foreground">{t('leaderboard.subtitle')}</p>
        </div>
      </div>
      
      <div className="p-4 space-y-6">
        {/* User Stats */}
        {userRank && (
          <Card className="bg-primary/5 border-primary/20 stagger-enter">
            <CardContent className="p-6 flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="p-3 rounded-full bg-primary/10 text-primary">
                  <TrendingUp className="h-6 w-6" />
                </div>
                <div>
                  <p className="text-sm text-muted-foreground mb-0.5">{t('leaderboard.yourRank')}</p>
                  <p className="text-2xl font-bold">#{userRank}</p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-sm text-muted-foreground mb-0.5">{t('leaderboard.yourSavings')}</p>
                <p className="text-xl font-bold text-primary">{formatPrice(userSaved)}</p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Invite Friends Action */}
        <div className="grid grid-cols-2 gap-3 stagger-enter" style={{ animationDelay: '0.1s' }}>
           <Button 
              className="w-full gap-2 bg-[#0088cc] hover:bg-[#0077b5] text-white" 
              onClick={handleShare}
              disabled={shareLoading}
           >
              <Share2 className="h-4 w-4" />
              {shareLoading ? t('common.loading') : t('leaderboard.inviteFriend')}
           </Button>
           
           <Button variant="outline" className="w-full gap-2" onClick={handleCopyLink}>
              <Copy className="h-4 w-4" />
              {t('leaderboard.copyLink')}
           </Button>
        </div>
        
        {/* Leaderboard List */}
        <div className="space-y-3">
          {loading ? (
            Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-16 w-full rounded-xl" />
            ))
          ) : error ? (
            <div className="text-center py-8 text-destructive">
              <p>{error}</p>
              <Button onClick={loadLeaderboard} variant="outline" className="mt-4">
                {t('common.retry')}
              </Button>
            </div>
          ) : leaderboard.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-12 text-center space-y-4">
              <div className="p-4 rounded-full bg-secondary text-muted-foreground">
                <Trophy className="h-12 w-12 opacity-50" />
              </div>
              <div>
                <h3 className="font-semibold text-lg">{t('leaderboard.empty')}</h3>
                <p className="text-sm text-muted-foreground">{t('leaderboard.emptyHint')}</p>
              </div>
            </div>
          ) : (
            leaderboard.map((entry, index) => {
              const isCurrentUser = user && entry.telegram_id === user.id
              
              return (
                <Card 
                  key={entry.rank}
                  className={`stagger-enter transition-all border-border/50 ${getRankStyles(entry.rank)} ${isCurrentUser ? 'ring-2 ring-primary ring-offset-2 ring-offset-background' : ''}`}
                  style={{ animationDelay: `${index * 0.05 + 0.2}s` }}
                >
                  <CardContent className="p-4 flex items-center gap-4">
                    <div className="shrink-0 w-8 flex justify-center">
                      {getRankIcon(entry.rank)}
                    </div>
                    
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={`font-semibold truncate ${isCurrentUser ? 'text-primary' : ''}`}>
                          {entry.name}
                        </span>
                        {isCurrentUser && (
                          <Badge variant="secondary" className="text-[10px] px-1.5 h-5">
                            {t('leaderboard.you')}
                          </Badge>
                        )}
                      </div>
                      
                    </div>
                    
                    <div className="text-right">
                      <span className="font-bold text-green-500">
                        {formatPrice(entry.total_saved)}
                      </span>
                      <p className="text-[10px] text-muted-foreground uppercase tracking-wider">
                        {t('leaderboard.saved')}
                      </p>
                    </div>
                  </CardContent>
                </Card>
              )
            })
          )}
        </div>
        
        {/* Info Card */}
        <Card className="bg-secondary/30 border-none stagger-enter mt-8">
          <CardContent className="p-4 flex gap-3">
            <Info className="h-5 w-5 text-muted-foreground shrink-0 mt-0.5" />
            <div className="text-sm text-muted-foreground leading-relaxed">
              <p className="font-medium text-foreground mb-1">{t('leaderboard.howItWorks')}</p>
              {t('leaderboard.explanation')}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
