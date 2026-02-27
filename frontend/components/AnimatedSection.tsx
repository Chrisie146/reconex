'use client'

import { useEffect, useRef, useState } from 'react'

interface AnimatedSectionProps {
  children: React.ReactNode
  className?: string
  /** Extra bottom-to-top offset in px for the rise effect (default 20) */
  yOffset?: number
  /** Delay before animation starts, e.g. '100ms', '200ms' */
  delay?: string
}

/**
 * Wraps children in a div that fades in + rises up when it first enters
 * the viewport (IntersectionObserver). Completely invisible until near the
 * viewport so there's no layout flash.
 */
export default function AnimatedSection({
  children,
  className = '',
  yOffset = 20,
  delay = '0ms',
}: AnimatedSectionProps) {
  const ref = useRef<HTMLDivElement>(null)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const el = ref.current
    if (!el) return

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setVisible(true)
          observer.disconnect()
        }
      },
      { threshold: 0.08 }
    )
    observer.observe(el)
    return () => observer.disconnect()
  }, [])

  return (
    <div
      ref={ref}
      className={className}
      style={{
        opacity: visible ? 1 : 0,
        transform: visible ? 'translateY(0)' : `translateY(${yOffset}px)`,
        transition: `opacity 0.55s ease-out ${delay}, transform 0.55s ease-out ${delay}`,
        willChange: 'opacity, transform',
      }}
    >
      {children}
    </div>
  )
}
