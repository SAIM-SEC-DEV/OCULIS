import { useEffect, useState } from 'react'

export function RuntimeLoader() {
  const [active, setActive] = useState(false)
  const [offline, setOffline] = useState(!navigator.onLine)

  useEffect(() => {
    const handleRequests = (event: Event) => {
      const custom = event as CustomEvent<{ active?: number }>
      setActive((custom.detail?.active ?? 0) > 0)
    }

    const handleOnline = () => setOffline(false)
    const handleOffline = () => setOffline(true)

    window.addEventListener('oculis:runtime:requests', handleRequests)
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)

    return () => {
      window.removeEventListener('oculis:runtime:requests', handleRequests)
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  if (!active && !offline) {
    return null
  }

  return (
    <div className="runtime-loader" role="status" aria-live="polite">
      <div className="runtime-loader__backdrop" />

      <div className="runtime-loader__panel">
        <div className="runtime-loader__brand">
          <span className="runtime-loader__orb" />
          <span>OCULIS</span>
        </div>

        <div className="runtime-loader__skeleton">
          <span className="runtime-loader__line runtime-loader__line--wide" />
          <span className="runtime-loader__line runtime-loader__line--medium" />
          <span className="runtime-loader__line runtime-loader__line--small" />
        </div>

        <div className="runtime-loader__status">
          <span className="runtime-loader__pulse" />
          <span>
            {offline
              ? 'NETWORK UNAVAILABLE / WAITING FOR CONNECTION'
              : 'CONTACTING ANALYSIS RUNTIME'}
          </span>
        </div>

        <div className="runtime-loader__hint">
          Waiting for the OCULIS runtime to respond.
        </div>
      </div>
    </div>
  )
}
