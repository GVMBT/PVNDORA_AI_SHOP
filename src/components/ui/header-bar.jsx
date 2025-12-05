import React from "react"
import { ArrowLeft } from "lucide-react"
import { Button } from "./button"
import { cn } from "../../lib/utils"

/**
 * Унифицированная шапка экрана для мобильных страниц.
 * Поддерживает кнопку "назад", заголовок и правый слот для действий.
 */
export function HeaderBar({ title, subtitle, onBack, rightSlot, className }) {
  return (
    <div
      className={cn(
        "sticky top-0 z-30 flex items-center gap-3 px-4 py-3 h-14",
        "backdrop-blur-xl bg-background/85 border-b border-white/10 shadow-[0_8px_24px_rgba(0,0,0,0.25)]",
        className
      )}
    >
      {onBack && (
        <Button
          variant="ghost"
          size="icon"
          onClick={onBack}
          className="h-10 w-10 rounded-full"
        >
          <ArrowLeft className="h-5 w-5" />
        </Button>
      )}

      <div className="min-w-0 flex-1">
        {title && (
          <h1 className="text-lg font-bold leading-tight truncate">{title}</h1>
        )}
        {subtitle && (
          <p className="text-xs text-muted-foreground font-medium truncate">
            {subtitle}
          </p>
        )}
      </div>

      {rightSlot ? (
        <div className="ml-auto flex items-center gap-2">{rightSlot}</div>
      ) : null}
    </div>
  )
}
