import React from 'react'
import { CreditCard } from 'lucide-react'
import { METHOD_ICONS, MIN_BY_METHOD_FALLBACK } from './payment-method-icons.jsx'

export function PaymentMethodList({ methods, selectedMethod, onSelect, total }) {
  return (
    <div className="space-y-2 mb-6">
      {methods.map((method) => {
        const methodId = typeof method === 'string' ? method : method.system_group
        const methodName = typeof method === 'string' ? method.toUpperCase() : method.name
        const IconComponent = METHOD_ICONS[methodId] || CreditCard
        const isSelected = selectedMethod === methodId
        
        // Check if method is enabled from API (defaults to true if not specified)
        const isEnabled = typeof method === 'object' ? (method.enabled !== false) : true
        
        // Min amount from API or fallback
        const minAmount = typeof method === 'object' && method.min_amount 
          ? method.min_amount 
          : MIN_BY_METHOD_FALLBACK[methodId] || 0
        
        // Method is disabled if: explicitly disabled by API OR total is below min
        const disabledByApi = !isEnabled
        const disabledByMin = total < minAmount
        const disabled = disabledByApi || disabledByMin
        
        return (
          <button
            key={methodId}
            className={`w-full flex items-center gap-3 p-3 rounded-xl border transition-all text-left ${
              isSelected 
                ? 'border-primary bg-primary/10 shadow-sm' 
                : 'border-border bg-muted/40 hover:border-primary/60'
            } ${
              disabled ? 'opacity-60 cursor-not-allowed' : ''
            }`}
            onClick={() => !disabled && onSelect(methodId)}
            disabled={disabled}
          >
            <div className="shrink-0">
              <IconComponent />
            </div>
            <div className="flex-1">
              <div className="font-semibold text-sm">{methodName}</div>
              <div className="text-xs text-muted-foreground">
                {disabledByMin 
                  ? `Минимум ${minAmount}` 
                  : (disabledByApi ? 'Недоступно' : 'Доступно')}
              </div>
            </div>
            <div className={`w-4 h-4 rounded-full border ${isSelected ? 'border-primary bg-primary' : 'border-muted-foreground/40'}`} />
          </button>
        )
      })}
    </div>
  )
}

