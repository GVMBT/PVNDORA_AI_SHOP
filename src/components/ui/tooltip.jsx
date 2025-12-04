import * as React from "react"
import { cn } from "../../lib/utils"

/**
 * Simple CSS-based Tooltip without radix dependency
 */

const TooltipProvider = ({ children }) => <>{children}</>

const Tooltip = ({ children }) => (
  <div className="relative inline-block group">
    {children}
  </div>
)

const TooltipTrigger = React.forwardRef(({ asChild, children, ...props }, ref) => {
  if (asChild && React.isValidElement(children)) {
    return React.cloneElement(children, { ref, ...props })
  }
  return <span ref={ref} {...props}>{children}</span>
})
TooltipTrigger.displayName = "TooltipTrigger"

const TooltipContent = React.forwardRef(({ className, children, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "absolute z-50 hidden group-hover:block bottom-full left-1/2 -translate-x-1/2 mb-2",
      "px-3 py-1.5 text-xs rounded-md",
      "bg-popover text-popover-foreground border shadow-md",
      "animate-in fade-in-0 zoom-in-95",
      className
    )}
    {...props}
  >
    {children}
  </div>
))
TooltipContent.displayName = "TooltipContent"

export { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider }

