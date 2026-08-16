import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { getAnalysis, type AnalysisStatus, type Finding, type RedirectHop } from '../lib/api'
import { Reveal } from '../components/Reveal'

const PIPELINE: { status: AnalysisStatus; label: string; note: string }[] = [
  { status: 'validating', label: 'Validate target', note: 'format + normalization' },
  { status: 'static_analysis', label: 'Inspect infrastructure', note: 'DNS + TLS + host signals' },
  { status: 'network_analysis', label: 'Trace redirects', note: 'hop-by-hop response chain' },
  { status: 'browser_analysis', label: 'Render remotely', note: 'isolated browser session' },
  { status: 'threat_analysis', label: 'Evaluate threats', note: 'content + behavior' },
  { status: 'scoring', label: 'Calculate verdict', note: 'evidence-weighted score' },
]
const TERMINAL: AnalysisStatus[] = ['completed', 'failed', 'timeout', 'blocked']

function pretty(value: unknown) {
  return value === null || value === undefined || value === '' ? '—' : String(value)
}

function stateFor(step: AnalysisStatus, current: AnalysisStatus) {
  if (TERMINAL.includes(current)) return current === 'completed' ? 'done' : 'stalled'
  const order = ['queued', ...PIPELINE.map((p) => p.status)]
  const active = order.indexOf(current)
  const target = order.indexOf(step)
  if (active > target) return 'done'
  if (active === target) return 'active'
  return 'pending'
}

function severityTone(severity?: string | null) {
  const s = (severity || '').toLowerCase()
  if (s.includes('critical') || s.includes('high')) return 'danger'
  if (s.includes('medium') || s.includes('suspicious')) return 'warn'
  return ''
}

function progressFor(status: AnalysisStatus) {
  if (status === 'queued') return 4
  const map: Record<string, number> = {
    validating: 17,
    static_analysis: 34,
    network_analysis: 51,
    browser_analysis: 69,
    threat_analysis: 85,
    scoring: 96,
    completed: 100,
  }
  return map[status] ?? 8
}

function errorPresentation(error?: string | null) {
  const raw = error || 'The remote analyzer could not complete this inspection.'
  const match = raw.match(/^\[([^\]]+)\]\s*(.*)$/s)
  const code = match?.[1] || 'UNKNOWN_ERROR'
  const detail = (match?.[2] || raw).replace(/^Detail:\s*/i, '')
  const titles: Record<string, string> = {
    RESPONSE_TOO_LARGE: 'Response too large', CONNECTION_TIMEOUT: 'Connection timed out', CONNECTION_FAILED: 'Connection failed',
    REMOTE_PROTOCOL_ERROR: 'Remote protocol error', RESPONSE_TIMEOUT: 'Response timed out', HTTP_FETCH_ERROR: 'HTTP fetch failed',
    SANDBOX_ERROR: 'Browser sandbox failed', ANALYSIS_TIMEOUT: 'Analysis timed out', UNKNOWN_ERROR: 'Inspection failed safely',
  }
  return { title: titles[code] || 'Inspection failed safely', detail, code }
}

export function Analysis() {
  const { id } = useParams<{ id: string }>()
  const { data, isLoading, isError, refetch } = useQuery({
    queryKey: ['analysis', id],
    queryFn: () => getAnalysis(id as string),
    enabled: Boolean(id),
    refetchInterval: (query) => query.state.data && TERMINAL.includes(query.state.data.status) ? false : 1600,
  })

  if (isLoading) return <Loading />
  if (isError || !data) {
    return (
      <div className="state-card danger" style={{ maxWidth: 700, margin: '80px auto' }}>
        <h2>Analysis unavailable</h2>
        <p>The inspection could not be loaded. The target may have expired or the reference is invalid.</p>
        <button data-testid="button-retry-analysis" onClick={() => refetch()} className="header-action" style={{ marginTop: 20 }}>retry request</button>
      </div>
    )
  }

  const terminal = TERMINAL.includes(data.status)
  const blocked = data.status === 'blocked'

  return (
    <div className="report-hero">
      <Reveal>
        <div className="report-head">
          <div>
            <Link to="/" data-testid="link-return-home" className="back-btn">← New inspection</Link>
            <div className="meta">INSPECTION / {data.id}</div>
            <div data-testid="text-submitted-url" className="report-head__title">{data.submitted_url || 'Target unavailable'}</div>
          </div>
          <span data-testid="status-analysis" className="report-head__status">{data.status.replaceAll('_', ' ')}</span>
        </div>
      </Reveal>

      {!terminal && <Reveal><Pipeline status={data.status} /></Reveal>}
      {terminal && blocked && <Reveal><StateCard title="Inspection blocked" detail={data.error || 'The analyzer stopped before visiting this target. No local request was made.'} tone="warning" /></Reveal>}
      {terminal && data.status === 'failed' && (() => { const error = errorPresentation(data.error); return <Reveal><StateCard title={error.title} detail={error.detail} tone="danger" code={error.code} /></Reveal> })()}
      {terminal && data.status === 'timeout' && <Reveal><StateCard title="Inspection timed out" detail={data.error || 'The target did not respond within the safe analysis window.'} tone="warning" /></Reveal>}
      {data.status === 'completed' && <Result data={data} />}
    </div>
  )
}

function Loading() {
  return (
    <div className="loading-stack">
      <div className="skeleton" style={{ width: 190, height: 11 }} />
      <div className="skeleton" style={{ width: '66%', height: 58, marginTop: 20 }} />
      <div className="skeleton" style={{ width: '100%', height: 340, marginTop: 32 }} />
    </div>
  )
}

function Pipeline({ status }: { status: AnalysisStatus }) {
  const progress = progressFor(status)
  return (
    <section className="pipeline">
      <div className="pipeline__head">
        <div><div className="eyebrow">REMOTE PROCESS</div><h1>Building your evidence trail</h1></div>
        <div className="pipeline__pct">{progress}%</div>
      </div>
      <div className="pipeline__bar"><span style={{ width: `${progress}%` }} /></div>
      <div className="pipeline__steps">
        {PIPELINE.map((step) => {
          const state = stateFor(step.status, status)
          return <div key={step.status} className={`pipeline-step ${state}`}>{state === 'done' ? '✓ ' : state === 'active' ? '● ' : '— '}{step.label}<br /><span style={{ opacity: .72 }}>{step.note}</span></div>
        })}
      </div>
    </section>
  )
}

function StateCard({ title, detail, tone, code }: { title: string; detail: string; tone: 'warning' | 'danger'; code?: string }) {
  return <div className={`state-card ${tone}`}><div style={{ display:'flex', justifyContent:'space-between', gap: 12, alignItems:'center' }}><h2>{title}</h2>{code && <code>{code}</code>}</div><p>{detail}</p></div>
}

function Result({ data }: { data: Awaited<ReturnType<typeof getAnalysis>> }) {
  const findings = data.findings || []
  const score = data.risk_score
  const danger = score !== null && score >= 70
  const warn = score !== null && score >= 35 && score < 70
  const tone = danger ? '#d77a7a' : warn ? '#d8b35f' : '#6fd49c'

  return (
    <div>
      <Reveal>
        <section className="report-score">
          <div>
            <div className="score-kicker">Evidence-backed verdict</div>
            <h1 data-testid="text-verdict" className="score-verdict" style={{ color: tone }}>{pretty(data.verdict) || 'Unscored'}</h1>
            <p className="score-summary">A remote assessment based on observed behavior, infrastructure and rendered evidence. The score is explainable: every contribution can be traced to a finding.</p>
          </div>
          <div className="score-orb" style={{ color: tone, borderColor: `${tone}55` }}>
            <div className="score-orb__number" data-testid="text-risk-score">{pretty(score)}<span style={{ color: 'var(--muted2)', fontSize: 14 }}> / 100</span></div>
            <div className="score-orb__label">risk score</div>
          </div>
        </section>
      </Reveal>

      <div className="report-layout">
        <Reveal>
          <section className="report-panel">
            <div className="report-panel__head"><div><div className="eyebrow">Threat findings</div><h2>What OCULIS observed</h2></div><span>{findings.length} recorded</span></div>
            <div className="report-panel__body">
              {findings.length ? findings.map((finding: Finding, index: number) => (
                <article key={finding.id || index} data-testid={`card-finding-${finding.id || index}`} className="finding-row">
                  <div className="finding-row__top"><span className={`severity-badge ${severityTone(finding.severity)}`}>{pretty(finding.severity)}</span><span className="finding-row__confidence">{pretty(finding.category)}</span></div>
                  <h3>{pretty(finding.title)}</h3>
                  <p>{pretty(finding.detail)}</p>
                  {finding.evidence && <pre className="evidence-block">{finding.evidence}</pre>}
                </article>
              )) : <div style={{ padding: '30px 0', color: 'var(--muted)', fontSize: 12 }}>No findings were returned for this inspection.</div>}
            </div>
          </section>
        </Reveal>

        <Reveal delay={1}>
          <section className="report-panel">
            <div className="report-panel__head"><div><div className="eyebrow">Analysis summary</div><h2>Observed surface</h2></div></div>
            <div className="metric-grid">
              <Metric label="Redirects" value={(data.redirects || []).length} />
              <Metric label="Requests" value={(data.network_requests || []).length} />
              <Metric label="Scripts" value={data.browser?.script_urls?.length} />
              <Metric label="Forms" value={data.browser?.forms?.length} />
              <Metric label="Passwords" value={data.browser?.password_inputs} />
              <Metric label="TLS" value={data.signals?.tls_version || '—'} />
              <Metric label="HTTP" value={data.signals?.status_code} />
              <Metric label="Elapsed" value={data.signals?.elapsed_ms ? `${data.signals.elapsed_ms}ms` : '—'} />
            </div>
          </section>
        </Reveal>
      </div>

      <Reveal>
        <section className="report-panel full-panel">
          <div className="report-panel__head"><div><div className="eyebrow">Redirect trace</div><h2>Remote navigation path</h2></div><span>{(data.redirects || []).length} hops</span></div>
          <RedirectTimeline redirects={data.redirects || []} />
        </section>
      </Reveal>

      <Reveal>
        <section className="report-panel full-panel">
          <div className="report-panel__head"><div><div className="eyebrow">Browser evidence</div><h2>Rendered remote surface</h2></div><span>{(data.network_requests || []).length} requests</span></div>
          <BrowserEvidence data={data} />
        </section>
      </Reveal>

      <Reveal>
        <section className="report-panel full-panel">
          <div className="report-panel__head"><div><div className="eyebrow">Infrastructure</div><h2>Host and protocol signals</h2></div></div>
          <Signals data={data} />
        </section>
      </Reveal>
    </div>
  )
}

function Metric({ label, value }: { label: string; value: unknown }) {
  return <div className="metric"><div className="metric__label">{label}</div><div className="metric__value">{pretty(value)}</div></div>
}

function RedirectTimeline({ redirects }: { redirects: RedirectHop[] }) {
  return <div className="redirect-list">{redirects.length ? redirects.map((redirect, index) => <article key={`${redirect.hop}-${redirect.url}-${index}`} className="redirect-item"><div className="redirect-meta"><span>Hop {pretty(redirect.hop)}</span><span>HTTP {pretty(redirect.status_code)}</span></div><div className="redirect-url">{pretty(redirect.url)}</div><div className="redirect-location">Location / {pretty(redirect.location)}</div></article>) : <div style={{ padding:'28px 0', color:'var(--muted)', fontSize:12 }}>No redirects observed. The target responded directly.</div>}</div>
}

function BrowserEvidence({ data }: { data: Awaited<ReturnType<typeof getAnalysis>> }) {
  const browser = data.browser
  const requests = data.network_requests || []
  const [imageLoaded, setImageLoaded] = useState(false)

  if (!browser && !data.screenshot_url && !requests.length) {
    return (
      <div className="browser-preview">
        <div className="browser-placeholder">
          <div className="browser-placeholder__inner">
            <span>no browser artifact</span>
            <p>The sandbox did not return a screenshot or browser telemetry for this target.</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="browser-preview">
      {data.screenshot_url ? (
        <div className={`browser-media ${imageLoaded ? 'is-loaded' : ''}`}>
          {!imageLoaded && (
            <div className="browser-skeleton" aria-label="Loading browser evidence">
              <div className="browser-skeleton__top" />
              <div className="browser-skeleton__body">
                <span />
                <span />
                <span />
                <span />
              </div>
            </div>
          )}

          <img
            src={data.screenshot_url}
            alt="Sandbox page screenshot"
            className="browser-image"
            onLoad={() => setImageLoaded(true)}
          />
        </div>
      ) : (
        <div className="browser-placeholder">
          <div className="browser-placeholder__inner">
            <span>remote render captured</span>
            <p>No screenshot artifact was returned, but the sandbox returned behavioral telemetry below.</p>
          </div>
        </div>
      )}

      <div className="metric-grid" style={{ margin: '14px 0 0' }}>
        <Metric label="Title" value={browser?.title} />
        <Metric label="Password inputs" value={browser?.password_inputs} />
        <Metric label="Email inputs" value={browser?.email_inputs} />
        <Metric label="Forms" value={browser?.forms?.length} />
        <Metric label="Iframes" value={browser?.iframes?.length} />
        <Metric label="Scripts" value={browser?.script_urls?.length} />
      </div>

      {browser?.error && (
        <div className="state-card warning" style={{ margin: '14px 0 0' }}>
          <h2>Sandbox note</h2>
          <p>{browser.error}</p>
        </div>
      )}

      {browser?.console_errors?.length ? (
        <div className="request-log" style={{ marginTop: 14 }}>
          <div className="panel-label" style={{ padding: 12 }}>Console errors</div>
          {browser.console_errors.map((error, index) => (
            <pre
              key={index}
              className="evidence-block"
              style={{
                margin: 0,
                borderBottom: '1px solid var(--line)',
                borderLeft: 0,
              }}
            >
              {error}
            </pre>
          ))}
        </div>
      ) : null}

      <div className="request-log" style={{ marginTop: 14 }}>
        {requests.length ? (
          requests.map((request, index) => (
            <div key={`${request.url}-${index}`} className="request-row">
              <span className="request-row__method">{request.method}</span>
              <span className="request-row__url">{request.url}</span>
              <span className={`request-row__state ${request.blocked ? 'blocked' : 'allowed'}`}>
                {request.blocked ? 'blocked' : 'allowed'}
              </span>
            </div>
          ))
        ) : (
          <div style={{ padding: 14, color: 'var(--muted)', fontSize: 11 }}>
            No browser requests were captured.
          </div>
        )}
      </div>
    </div>
  )
}

function Signals({ data }: { data: Awaited<ReturnType<typeof getAnalysis>> }) {
  const s = data.signals
  const entries = [['scheme', s?.scheme], ['hostname', s?.hostname], ['port', s?.port], ['HTTP status', s?.status_code], ['content type', s?.content_type], ['response size', s?.response_size], ['TLS', s?.tls_version], ['server', s?.server], ['resolved IPs', s?.resolved_ips?.join(', ')], ['final URL', s?.final_url || data.final_url]]
  return <div className="metric-grid" style={{ margin: 0, gridTemplateColumns: '1fr 1fr' }}>{entries.map(([label, value]) => <Metric key={String(label)} label={String(label)} value={value} />)}</div>
}
