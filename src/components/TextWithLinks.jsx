import React from 'react'

/**
 * Component to render text with clickable @gvmbt158 links
 */
export function TextWithLinks({ text, className = '' }) {
  if (!text) return null
  
  // Replace @gvmbt158 with clickable link
  const parts = text.split(/(@gvmbt158)/g)
  
  return (
    <span className={className}>
      {parts.map((part, index) => {
        if (part === '@gvmbt158') {
          return (
            <a
              key={index}
              href="https://t.me/gvmbt158"
              target="_blank"
              rel="noopener noreferrer"
              className="text-primary hover:underline font-medium"
            >
              @gvmbt158
            </a>
          )
        }
        return <span key={index}>{part}</span>
      })}
    </span>
  )
}
