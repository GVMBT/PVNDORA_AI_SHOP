import React from 'react'

export default function LoadingScreen() {
  return (
    <div className="min-h-screen bg-gradient-animated flex items-center justify-center">
      <div className="text-center">
        <div className="relative w-20 h-20 mx-auto mb-6">
          {/* Outer ring */}
          <div className="absolute inset-0 border-4 border-[var(--color-border)] rounded-full" />
          {/* Spinning arc */}
          <div className="absolute inset-0 border-4 border-transparent border-t-[var(--color-primary)] rounded-full animate-spin" />
          {/* Inner glow */}
          <div className="absolute inset-3 bg-[var(--color-primary)]/10 rounded-full animate-pulse" />
        </div>
        
        <h2 className="text-xl font-semibold text-[var(--color-text)] mb-2">
          PVNDORA
        </h2>
        <p className="text-[var(--color-text-muted)] text-sm">
          Loading...
        </p>
      </div>
    </div>
  )
}




