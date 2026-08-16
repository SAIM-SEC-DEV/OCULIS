import type { ReactNode } from 'react'

export function SectionHeader({ eyebrow, title, children }: { eyebrow: string; title: string; children?: ReactNode }) {
  return (
    <div className="section-header">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h2>{title}</h2>
      </div>
      {children && <div className="section-header__aside">{children}</div>}
    </div>
  )
}
