import { useState, useEffect, useCallback } from 'react'

import { useApi } from './useApi'
import { useLocale } from './useLocale'
import { useTelegram } from './useTelegram'

/**
 * Инкапсулирует загрузку/операции профиля, рефералок и выводов.
 */
export function useProfileData({ onBack }) {
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

  const handleCopyLink = useCallback(async () => {
    const refLink = `https://t.me/pvndora_ai_bot?start=ref_${user?.id}`
    try {
      await navigator.clipboard.writeText(refLink)
      hapticFeedback('notification', 'success')
      showPopup({ title: '✅', message: t('profile.linkCopied'), buttons: [{ type: 'ok' }] })
    } catch (e) {
      console.error('Copy failed', e)
    }
  }, [hapticFeedback, showPopup, t, user?.id])

  const handleShare = useCallback(async () => {
    setShareLoading(true)
    hapticFeedback('impact', 'medium')
    try {
      const { prepared_message_id } = await post('/referral/share-link')
      if (window.Telegram?.WebApp?.shareMessage) {
        window.Telegram.WebApp.shareMessage(prepared_message_id, (success) => {
          if (success) console.log('Shared successfully')
        })
      } else if (window.Telegram?.WebApp?.switchInlineQuery) {
        window.Telegram.WebApp.switchInlineQuery('invite', ['users', 'groups', 'channels'])
      } else {
        await handleCopyLink()
      }
    } catch (err) {
      await handleCopyLink()
    } finally {
      setShareLoading(false)
    }
  }, [handleCopyLink, hapticFeedback, post])

  const handleWithdraw = useCallback(async () => {
    const amount = parseFloat(withdrawAmount)
    if (isNaN(amount) || amount < 500) {
      showPopup({ title: '❌', message: t('profile.minWithdrawal', { min: formatPrice(500, currency) }), buttons: [{ type: 'ok' }] })
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
  }, [currency, formatPrice, hapticFeedback, loadProfile, post, profile?.balance, showPopup, t, withdrawAmount, withdrawDetails, withdrawMethod])

  return {
    loading,
    profile,
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
  }
}

export default useProfileData
