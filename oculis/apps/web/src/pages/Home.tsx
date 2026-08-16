import { useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import { createAnalysis } from '../lib/api'
import { OrbitalVisual } from '../components/OrbitalVisual'
import { Reveal } from '../components/Reveal'

const checks = [
  ['01', 'Resolve safely', 'DNS, TLS, redirects and host signals are observed from the analysis boundary.'],
  ['02', 'Trace behavior', 'The remote browser captures page structure, requests and visible behavior without local exposure.'],
  ['03', 'Explain the call', 'A verdict is supported by findings, confidence and raw evidence instead of a black-box number.'],
]

export function Home() {
  const [url, setUrl] = useState('')
  const navigate = useNavigate()
  const mutation = useMutation({
    mutationFn: (value: string) => createAnalysis(value),
    onSuccess: (data) => navigate(`/analysis/${data.id}`),
  })

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (url.trim()) mutation.mutate(url.trim())
  }

  return (
    <div>
      <section className="hero">
        <div className="hero-copy">
          <Reveal>
            <div className="eyebrow">OCULIS / FIELD CONSOLE 01</div>
            <h1 className="hero__title">Inspect the link.<br /><span>Not your device.</span></h1>
            <p className="hero__lede">
              A remote web-threat inspection platform for the links that make you hesitate. Submit once.
              OCULIS resolves, renders and traces the destination inside an isolated environment, then gives you an evidence trail you can audit.
            </p>
            <div className="hero__meta">
              <span className="meta-chip">SSRF-safe boundary</span>
              <span className="meta-chip">isolated browser</span>
              <span className="meta-chip">evidence-first</span>
              <span className="meta-chip">no local visit</span>
            </div>
          </Reveal>

          <Reveal delay={1}>
            <section className="scan-console">
              <div className="scan-console__bar">
                <span className="panel-label">Target URL / remote inspection</span>
                <span className="panel-label panel-state">boundary ready</span>
              </div>
              <form onSubmit={handleSubmit}>
                <div className="scan-form">
                  <label className="url-wrap" htmlFor="url">
                    <span className="url-prefix">›</span>
                    <input
                      id="url"
                      data-testid="input-url"
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                      placeholder="https://suspicious.example/login"
                      className="url-input"
                      spellCheck={false}
                      autoFocus
                    />
                  </label>
                  <button data-testid="button-submit-analysis" type="submit" disabled={mutation.isPending || !url.trim()} className="primary-btn">
                    {mutation.isPending ? 'Queueing…' : 'Inspect URL'}
                  </button>
                </div>
                {mutation.isError && <p data-testid="status-submit-error" className="form-error">{(mutation.error as Error).message || 'Unable to queue this target.'}</p>}
              </form>
              <div className="scan-console__foot">
                <span>browser exposure <strong>none</strong></span>
                <span>analysis runtime <strong>remote</strong></span>
              </div>
            </section>
          </Reveal>
        </div>

        <div className="hero-visual">
          <OrbitalVisual />
        </div>
      </section>

      <div className="feature-strip">
        {checks.map(([number, title, text], index) => (
          <Reveal key={number} delay={index + 1}>
            <article className="feature-card">
              <div className="feature-card__num">{number === '01' ? 'Safety model' : number}</div>
              <h3>{title}</h3>
              <p>{text}</p>
            </article>
          </Reveal>
        ))}
      </div>
    </div>
  )
}
