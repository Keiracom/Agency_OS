"use client"

import { useEffect, useRef, useState } from "react"
import { cn } from "@/lib/utils"

interface NumberTickerProps {
  value: number
  delay?: number
  className?: string
  decimalPlaces?: number
}

export function NumberTicker({
  value,
  delay = 0,
  className,
  decimalPlaces = 0,
}: NumberTickerProps) {
  const [displayValue, setDisplayValue] = useState(0)
  const ref = useRef<HTMLSpanElement>(null)
  const hasAnimated = useRef(false)

  useEffect(() => {
    if (hasAnimated.current) return
    
    const timeout = setTimeout(() => {
      hasAnimated.current = true
      const duration = 1500
      const start = performance.now()
      
      const animate = (currentTime: number) => {
        const elapsed = currentTime - start
        const progress = Math.min(elapsed / duration, 1)
        
        // Ease out cubic
        const easeOut = 1 - Math.pow(1 - progress, 3)
        const current = easeOut * value
        
        setDisplayValue(current)
        
        if (progress < 1) {
          requestAnimationFrame(animate)
        }
      }
      
      requestAnimationFrame(animate)
    }, delay * 1000)
    
    return () => clearTimeout(timeout)
  }, [value, delay])

  return (
    <span
      ref={ref}
      className={cn("tabular-nums tracking-tight", className)}
    >
      {decimalPlaces > 0
        ? displayValue.toFixed(decimalPlaces)
        : Math.round(displayValue)}
    </span>
  )
}
