import { Link, useLocation } from 'react-router-dom'
import type { ReactNode } from 'react'
import { RuntimeLoader } from './RuntimeLoader'
import { useEffect, useState } from 'react'


function OculisMark({ size = 40 }: { size?: number }) {
  return (
    <span className="oculis-mark" style={{ width: size, height: size }} aria-hidden="true">
      <span className="oculis-mark__orbit oculis-mark__orbit--one" />
      <span className="oculis-mark__orbit oculis-mark__orbit--two" />
      <span className="oculis-mark__core" />
      <span className="oculis-mark__spark" />
    </span>
  )
}

export function Layout({ children }: { children: ReactNode }) {
  const location = useLocation()
  const [scrollProgress, setScrollProgress] = useState(0)

  useEffect(() => {
    const update = () => {
      const max = document.documentElement.scrollHeight - window.innerHeight
      setScrollProgress(max > 0 ? window.scrollY / max : 0)
    }
    update()
    window.addEventListener('scroll', update, { passive: true })
    window.addEventListener('resize', update)
    return () => {
      window.removeEventListener('scroll', update)
      window.removeEventListener('resize', update)
    }
  }, [location.pathname])

  useEffect(() => window.scrollTo({ top: 0, behavior: 'instant' as ScrollBehavior }), [location.pathname])

  const analysisRoute = location.pathname.startsWith('/analysis/')

  return (
    <div className="app-shell">
      <RuntimeLoader />
      <div className="app-atmosphere" aria-hidden="true">
        <div className="app-atmosphere__halo" />
        <div className="app-atmosphere__mesh" />
        <div className="app-atmosphere__dust" />
        <div
          className="app-atmosphere__beam"
          style={{ transform: `translate3d(0, ${scrollProgress * 70}vh, 0)` }}
        />
      </div>

      <div className="app-scrollbar" aria-hidden="true">
        <span style={{ transform: `scaleY(${Math.max(scrollProgress, 0.015)})` }} />
      </div>

      <header className="site-header">
        <div className="site-header__inner">
          <Link to="/" className="brand" data-testid="link-home">
            <OculisMark size={42} />
            <div className="brand__copy">
              <span className="brand__word">OCULIS</span>
              <span className="brand__sub">remote web inspection</span>
            </div>
          </Link>

          <div className="site-header__right">
            <div className="header-trust">
              <span className="status-led" />
              <span>isolated runtime</span>
            </div>
            {analysisRoute && (
              <Link to="/" className="header-action">
                new inspection
              </Link>
            )}
          </div>
        </div>
      </header>

      <main className="site-main">{children}</main>

      <footer className="site-footer">
        <span>OCULIS / evidence before exposure</span>
        <span>zero local navigation · transient analysis surface</span>
        <nav className="footer-links">
  <Link to="/about">About</Link>
  <Link to="/privacy">Privacy</Link>
  <Link to="/faq">FAQ</Link>
</nav>
      </footer>

      <style>{`
        .reveal{opacity:0;transform:translate3d(0,28px,0);transition:opacity .75s cubic-bezier(.2,.7,.2,1),transform .75s cubic-bezier(.2,.7,.2,1)}
        .reveal.is-visible{opacity:1;transform:none}
        .reveal[data-delay="1"]{transition-delay:.08s}.reveal[data-delay="2"]{transition-delay:.16s}.reveal[data-delay="3"]{transition-delay:.24s}.reveal[data-delay="4"]{transition-delay:.32s}
      `}</style>
    </div>
  )
}
