import { useState, useEffect } from 'react'

/**
 * Hook to parse URL search params and Telegram startapp
 */
export function useSearchParams() {
  const [params, setParams] = useState(() => {
    const p = new URLSearchParams(window.location.search)
    
    // Also check hash for Telegram Mini App params
    if (window.location.hash) {
      const hashParams = new URLSearchParams(window.location.hash.slice(1))
      hashParams.forEach((value, key) => {
        if (!p.has(key)) {
          p.set(key, value)
        }
      })
    }
    
    return p
  })
  
  useEffect(() => {
    const p = new URLSearchParams(window.location.search)
    
    // Also check hash for Telegram Mini App params
    if (window.location.hash) {
      const hashParams = new URLSearchParams(window.location.hash.slice(1))
      hashParams.forEach((value, key) => {
        if (!p.has(key)) {
          p.set(key, value)
        }
      })
    }
    
    // Decode Base64url startapp if present
    const telegramStartapp = p.get('tgWebAppStartParam')
    const urlStartapp = p.get('startapp')
    const startapp = telegramStartapp || urlStartapp
    
    console.log('DEBUG: useSearchParams - telegramStartapp:', telegramStartapp)
    console.log('DEBUG: useSearchParams - urlStartapp:', urlStartapp)
    console.log('DEBUG: useSearchParams - final startapp:', startapp)
    console.log('DEBUG: useSearchParams - window.location:', window.location.href)
    
    if (startapp) {
      // If already in our format (pay_ or product_), don't decode
      if (startapp.startsWith('pay_') || startapp.startsWith('product_')) {
        console.log('DEBUG: useSearchParams - already in format, keeping:', startapp)
        p.set('startapp', startapp)
      } else if (startapp.includes('_') && !startapp.startsWith('pay_') && !startapp.startsWith('product_')) {
        // Already decoded format like "checkout" or other formats with underscores (but not our pay_/product_ format)
        console.log('DEBUG: useSearchParams - format with _, keeping:', startapp)
        p.set('startapp', startapp)
      } else {
        // Try Base64url decode only if it doesn't look like our format
        try {
          const decoded = atob(startapp.replace(/-/g, '+').replace(/_/g, '/'))
          console.log('DEBUG: useSearchParams - decoded from Base64:', decoded)
          // Check if decoded result looks like our format
          if (decoded.startsWith('pay_') || decoded.startsWith('product_') || decoded.startsWith('checkout')) {
            console.log('DEBUG: useSearchParams - decoded matches our format, using:', decoded)
            p.set('startapp', decoded)
          } else {
            // Not our format, keep original
            console.log('DEBUG: useSearchParams - decoded does not match, keeping original:', startapp)
            p.set('startapp', startapp)
          }
        } catch (e) {
          // Keep original if not Base64
          console.log('DEBUG: useSearchParams - Base64 decode failed, keeping original:', startapp, e)
          p.set('startapp', startapp)
        }
      }
    } else {
      console.log('DEBUG: useSearchParams - no startapp found')
    }
    
    setParams(p)
  }, [])
  
  return params
}

export default useSearchParams
