import { useState, useEffect, useCallback } from 'react'

/**
 * Hook for Telegram WebApp SDK integration
 */
export function useTelegram() {
  const [isReady, setIsReady] = useState(false)
  const [initData, setInitData] = useState('')
  const [user, setUser] = useState(null)
  const [colorScheme, setColorScheme] = useState('dark')
  
  useEffect(() => {
    const tg = window.Telegram?.WebApp
    
    if (tg) {
      // Mark as ready
      tg.ready()
      tg.expand()
      
      // Get init data
      setInitData(tg.initData)
      setUser(tg.initDataUnsafe?.user || null)
      setColorScheme(tg.colorScheme || 'dark')
      
      // Theme changed listener
      tg.onEvent('themeChanged', () => {
        setColorScheme(tg.colorScheme)
      })
      
      setIsReady(true)
    } else {
      // Development mode without Telegram
      setInitData('')
      setUser({
        id: 123456789,
        first_name: 'Test',
        last_name: 'User',
        username: 'testuser',
        language_code: 'en'
      })
      setIsReady(true)
    }
  }, [])
  
  const showConfirm = useCallback((message) => {
    const tg = window.Telegram?.WebApp
    if (tg?.showConfirm) {
      return new Promise((resolve) => {
        tg.showConfirm(message, resolve)
      })
    }
    return Promise.resolve(window.confirm(message))
  }, [])
  
  const showAlert = useCallback((message) => {
    const tg = window.Telegram?.WebApp
    if (tg?.showAlert) {
      return new Promise((resolve) => {
        tg.showAlert(message, resolve)
      })
    }
    window.alert(message)
    return Promise.resolve()
  }, [])
  
  const hapticFeedback = useCallback((type = 'impact', style = 'medium') => {
    const tg = window.Telegram?.WebApp?.HapticFeedback
    if (tg) {
      if (type === 'impact') {
        tg.impactOccurred(style)
      } else if (type === 'notification') {
        tg.notificationOccurred(style)
      } else if (type === 'selection') {
        tg.selectionChanged()
      }
    }
  }, [])
  
  const close = useCallback(() => {
    window.Telegram?.WebApp?.close()
  }, [])
  
  const openLink = useCallback((url) => {
    window.Telegram?.WebApp?.openLink(url)
  }, [])
  
  const openTelegramLink = useCallback((url) => {
    window.Telegram?.WebApp?.openTelegramLink(url)
  }, [])
  
  const sendData = useCallback((data) => {
    window.Telegram?.WebApp?.sendData(JSON.stringify(data))
  }, [])
  
  const setMainButton = useCallback((config) => {
    const btn = window.Telegram?.WebApp?.MainButton
    if (btn) {
      if (config.text) btn.setText(config.text)
      if (config.color) btn.setParams({ color: config.color })
      if (config.textColor) btn.setParams({ text_color: config.textColor })
      if (config.onClick) btn.onClick(config.onClick)
      if (config.isVisible !== undefined) {
        config.isVisible ? btn.show() : btn.hide()
      }
      if (config.isLoading !== undefined) {
        config.isLoading ? btn.showProgress() : btn.hideProgress()
      }
    }
  }, [])
  
  const setBackButton = useCallback((config) => {
    const btn = window.Telegram?.WebApp?.BackButton
    if (btn) {
      if (config.onClick) btn.onClick(config.onClick)
      if (config.isVisible !== undefined) {
        config.isVisible ? btn.show() : btn.hide()
      }
    }
  }, [])
  
  return {
    isReady,
    initData,
    user,
    colorScheme,
    showConfirm,
    showAlert,
    hapticFeedback,
    close,
    openLink,
    openTelegramLink,
    sendData,
    setMainButton,
    setBackButton
  }
}

export default useTelegram


