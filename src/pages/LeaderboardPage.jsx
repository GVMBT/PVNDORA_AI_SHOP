import React, { useState, useEffect } from 'react'
import { useLeaderboard } from '../hooks/useApi'
import { useLocale } from '../hooks/useLocale'
import { useTelegram } from '../hooks/useTelegram'

export default function LeaderboardPage({ onBack }) {
  const { getLeaderboard, loading, error } = useLeaderboard()
  const { t, formatPrice } = useLocale()
  const { setBackButton, user } = useTelegram()
  
  const [leaderboard, setLeaderboard] = useState([])
  const [userRank, setUserRank] = useState(null)
  const [userSaved, setUserSaved] = useState(0)
  
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
  
  const getRankEmoji = (rank) => {
    if (rank === 1) return '🥇'
    if (rank === 2) return '🥈'
    if (rank === 3) return '🥉'
    return `#${rank}`
  }
  
  const getRankStyle = (rank) => {
    if (rank === 1) return 'bg-gradient-to-r from-yellow-500/20 to-yellow-600/20 border-yellow-500/50'
    if (rank === 2) return 'bg-gradient-to-r from-gray-400/20 to-gray-500/20 border-gray-400/50'
    if (rank === 3) return 'bg-gradient-to-r from-amber-600/20 to-amber-700/20 border-amber-600/50'
    return ''
  }
  
  return (
    <div className="p-4">
      {/* Header */}
      <header className="mb-6 stagger-enter">
        <h1 className="text-2xl font-bold text-[var(--color-text)]">
          🏆 {t('leaderboard.title')}
        </h1>
        <p className="text-[var(--color-text-muted)]">
          {t('leaderboard.subtitle')}
        </p>
      </header>
      
      {/* User's position */}
      {userRank && (
        <div className="card mb-6 bg-[var(--color-primary)]/10 border-[var(--color-primary)]/30 stagger-enter">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-2xl">{getRankEmoji(userRank)}</span>
              <div>
                <span className="text-[var(--color-text-muted)] text-sm">
                  {t('leaderboard.yourRank')}
                </span>
                <div className="font-bold text-[var(--color-text)]">
                  #{userRank}
                </div>
              </div>
            </div>
            <div className="text-right">
              <span className="text-[var(--color-text-muted)] text-sm">
                {t('leaderboard.yourSavings')}
              </span>
              <div className="font-bold text-[var(--color-primary)]">
                {formatPrice(userSaved)}
              </div>
            </div>
          </div>
        </div>
      )}
      
      {/* Leaderboard list */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="card h-16 skeleton" />
          ))}
        </div>
      ) : error ? (
        <div className="card text-center py-8">
          <p className="text-[var(--color-error)] mb-4">{error}</p>
          <button onClick={loadLeaderboard} className="btn btn-secondary">
            {t('common.retry')}
          </button>
        </div>
      ) : leaderboard.length === 0 ? (
        <div className="card text-center py-12 stagger-enter">
          <span className="text-5xl mb-4 block">🏆</span>
          <h3 className="text-lg font-semibold text-[var(--color-text)] mb-2">
            {t('leaderboard.empty')}
          </h3>
          <p className="text-[var(--color-text-muted)]">
            {t('leaderboard.emptyHint')}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {leaderboard.map((entry, index) => {
            const isCurrentUser = user && entry.user_id === user.id
            
            return (
              <div
                key={entry.user_id}
                className={`card flex items-center gap-4 stagger-enter ${getRankStyle(entry.rank)} ${
                  isCurrentUser ? 'ring-2 ring-[var(--color-primary)]' : ''
                }`}
                style={{ animationDelay: `${index * 0.05}s` }}
              >
                {/* Rank */}
                <div className="w-12 text-center">
                  <span className={`text-xl ${entry.rank <= 3 ? '' : 'text-[var(--color-text-muted)]'}`}>
                    {getRankEmoji(entry.rank)}
                  </span>
                </div>
                
                {/* User info */}
                <div className="flex-1 min-w-0">
                  <div className="font-semibold text-[var(--color-text)] truncate">
                    {entry.first_name}
                    {isCurrentUser && (
                      <span className="text-[var(--color-primary)] ml-1 text-sm">
                        ({t('leaderboard.you')})
                      </span>
                    )}
                  </div>
                  {entry.username && (
                    <span className="text-[var(--color-text-muted)] text-sm">
                      @{entry.username}
                    </span>
                  )}
                </div>
                
                {/* Savings */}
                <div className="text-right">
                  <div className="font-bold text-[var(--color-success)]">
                    {formatPrice(entry.total_saved)}
                  </div>
                  <span className="text-[var(--color-text-muted)] text-xs">
                    {t('leaderboard.saved')}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      )}
      
      {/* Info card */}
      <div className="card mt-6 bg-[var(--color-bg-elevated)] stagger-enter">
        <h3 className="font-semibold text-[var(--color-text)] mb-2">
          💡 {t('leaderboard.howItWorks')}
        </h3>
        <p className="text-[var(--color-text-muted)] text-sm">
          {t('leaderboard.explanation')}
        </p>
      </div>
    </div>
  )
}

