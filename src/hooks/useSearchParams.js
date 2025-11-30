import { useMemo } from 'react'

/**
 * Hook to parse URL search params and Telegram startapp
 */
export function useSearchParams() {
  return useMemo(() => {
    const params = new URLSearchParams(window.location.search)
    
    // Also check hash for Telegram Mini App params
    if (window.location.hash) {
      const hashParams = new URLSearchParams(window.location.hash.slice(1))
      hashParams.forEach((value, key) => {
        if (!params.has(key)) {
          params.set(key, value)
        }
      })
    }
    
    // Decode Base64url startapp if present
    const startapp = params.get('tgWebAppStartParam') || params.get('startapp')
    if (startapp && startapp.includes('_')) {
      // Already decoded format like "product_uuid_ref_123"
      params.set('startapp', startapp)
    } else if (startapp) {
      try {
        // Try Base64url decode
        const decoded = atob(startapp.replace(/-/g, '+').replace(/_/g, '/'))
        params.set('startapp', decoded)
      } catch {
        // Keep original if not Base64
        params.set('startapp', startapp)
      }
    }
    
    return params
  }, [])
}

export default useSearchParams


