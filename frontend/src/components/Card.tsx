// Double-bezel kart sarmalayıcı (shell > core > eyebrow). Jinja .shell/.core yapısının karşılığı.
// .grid'in DOĞRUDAN çocuğu olmalı (nth-child rise animasyon gecikmeleri için).
import type { ReactNode } from 'react'

interface CardProps {
  eyebrow: string
  /** data-role="period": Amir görünümünde gizlenen kartlar (Trend, Veri-kalite). */
  period?: boolean
  className?: string
  children: ReactNode
}

export default function Card({ eyebrow, period, className, children }: CardProps) {
  return (
    <section className={`shell${className ? ` ${className}` : ''}`} data-role={period ? 'period' : undefined}>
      <div className="core">
        <span className="eyebrow">{eyebrow}</span>
        {children}
      </div>
    </section>
  )
}
