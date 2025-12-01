import React from 'react'

export default function StarRating({ 
  rating, 
  size = 'md', 
  showValue = false,
  interactive = false,
  onChange 
}) {
  const sizes = {
    sm: 'text-sm',
    md: 'text-lg',
    lg: 'text-2xl'
  }
  
  const stars = []
  const fullStars = Math.floor(rating)
  const hasHalfStar = rating % 1 >= 0.5
  
  for (let i = 1; i <= 5; i++) {
    const isFilled = i <= fullStars
    const isHalf = i === fullStars + 1 && hasHalfStar
    
    stars.push(
      <button
        key={i}
        type="button"
        disabled={!interactive}
        onClick={() => interactive && onChange?.(i)}
        className={`${sizes[size]} transition-transform ${interactive ? 'hover:scale-125 cursor-pointer' : ''}`}
      >
        {isFilled ? (
          <span className="star-filled">★</span>
        ) : isHalf ? (
          <span className="star-filled">★</span> // Could use half-star SVG
        ) : (
          <span className="star-empty">☆</span>
        )}
      </button>
    )
  }
  
  return (
    <div className="flex items-center gap-0.5">
      {stars}
      {showValue && (
        <span className="ml-1 text-[var(--color-text-muted)] text-sm">
          {rating.toFixed(1)}
        </span>
      )}
    </div>
  )
}

// Variant for interactive rating input
export function RatingInput({ value = 0, onChange }) {
  return (
    <div className="flex items-center gap-2">
      {[1, 2, 3, 4, 5].map((star) => (
        <button
          key={star}
          type="button"
          onClick={() => onChange(star)}
          className={`text-3xl transition-all hover:scale-110 ${
            star <= value ? 'text-[var(--color-warning)]' : 'text-[var(--color-text-muted)]'
          }`}
        >
          {star <= value ? '★' : '☆'}
        </button>
      ))}
    </div>
  )
}




