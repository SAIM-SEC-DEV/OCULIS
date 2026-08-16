import { useEffect, useRef } from 'react'

export function OrbitalVisual() {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    const node = ref.current
    if (!node) return
    const update = () => {
      const rect = node.getBoundingClientRect()
      const center = rect.top + rect.height / 2
      const progress = Math.max(-1, Math.min(1, (window.innerHeight / 2 - center) / window.innerHeight))
      node.style.setProperty('--tilt-x', `${progress * 10}deg`)
      node.style.setProperty('--tilt-y', `${progress * -16}deg`)
    }
    update()
    window.addEventListener('scroll', update, { passive: true })
    window.addEventListener('resize', update)
    return () => {
      window.removeEventListener('scroll', update)
      window.removeEventListener('resize', update)
    }
  }, [])

  return (
    <div className="orbital-stage" ref={ref} aria-hidden="true">
      <div className="orbital-stage__depth" />
      <div className="orbital-stage__ring orbital-stage__ring--a" />
      <div className="orbital-stage__ring orbital-stage__ring--b" />
      <div className="orbital-stage__ring orbital-stage__ring--c" />
      <div className="orbital-stage__lens">
        <div className="orbital-stage__iris" />
        <div className="orbital-stage__glint" />
      </div>
      <div className="orbital-stage__axis orbital-stage__axis--h" />
      <div className="orbital-stage__axis orbital-stage__axis--v" />
      <div className="orbital-stage__label orbital-stage__label--one">remote boundary</div>
      <div className="orbital-stage__label orbital-stage__label--two">telemetry live</div>
    </div>
  )
}
