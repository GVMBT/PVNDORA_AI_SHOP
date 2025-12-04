import * as React from "react"
import { cn } from "../../lib/utils"

/**
 * Simple CSS-based Tooltip without radix dependency
 * Uses hover state on the wrapper to show/hide tooltip
 */

const TooltipProvider = ({ children }) => <>{children}</>

const Tooltip = ({ children }) => (
  <div className="relative inline-flex group/tooltip">
    {children}
  </div>
)

const TooltipTrigger = React.forwardRef(({ asChild, children, ...props }, ref) => {
  // Just render children directly - the wrapper handles grouping
  if (asChild && React.isValidElement(children)) {
    return React.cloneElement(children, { ref, ...props })
  }
  return <span ref={ref} {...props}>{children}</span>
})
TooltipTrigger.displayName = "TooltipTrigger"

const TooltipContent = React.forwardRef(({ className, side = "top", children, ...props }, ref) => {
  const positionClasses = {
    top: "bottom-full left-1/2 -translate-x-1/2 mb-2",
    bottom: "top-full left-1/2 -translate-x-1/2 mt-2",
    left: "right-full top-1/2 -translate-y-1/2 mr-2",
    right: "left-full top-1/2 -translate-y-1/2 ml-2"
  }
  
  return (
    <div
      ref={ref}
      className={cn(
        "absolute z-50 pointer-events-none",
        "opacity-0 group-hover/tooltip:opacity-100 transition-opacity duration-150",
        positionClasses[side] || positionClasses.top,
        "px-3 py-1.5 text-xs rounded-md whitespace-nowrap",
        "bg-popover text-popover-foreground border shadow-md",
        className
      )}
      {...props}
    >
      {children}
    </div>
  )
})
TooltipContent.displayName = "TooltipContent"

export { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider }

