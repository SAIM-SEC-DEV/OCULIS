export type AnalysisStatus =
  | 'queued'
  | 'validating'
  | 'static_analysis'
  | 'network_analysis'
  | 'browser_analysis'
  | 'threat_analysis'
  | 'scoring'
  | 'completed'
  | 'failed'
  | 'timeout'
  | 'blocked'

export interface AnalysisResult {
  id: string
  submitted_url: string
  status: AnalysisStatus
  created_at: string
  completed_at?: string | null
  risk_score: number | null
  verdict: string | null
  normalized_url?: string | null
  final_url?: string | null
  findings?: Finding[] | null
  redirects?: RedirectHop[] | null
  signals?: Signals | null
  error?: string | null
  browser?: { error?: string | null; title?: string | null; forms?: { action?: string; method?: string }[]; password_inputs?: number; email_inputs?: number; iframes?: string[]; script_urls?: string[]; external_links?: string[]; console_errors?: string[] } | null
  screenshot_url?: string | null
  network_requests?: { url: string; method: string; resource_type?: string | null; blocked?: boolean; reason?: string | null }[] | null
}

export interface Finding {
  id?: string
  severity?: string | null
  title?: string | null
  detail?: string | null
  evidence?: string | null
  category?: string | null
}

export interface RedirectHop {
  hop?: number | null
  url?: string | null
  status_code?: number | null
  location?: string | null
}

export interface Signals {
  scheme?: string | null
  hostname?: string | null
  port?: number | null
  resolved_ips?: string[] | null
  final_url?: string | null
  status_code?: number | null
  content_type?: string | null
  response_size?: number | null
  tls_version?: string | null
  server?: string | null
  elapsed_ms?: number | null
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api/v1${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(`${res.status} ${res.statusText}: ${body}`)
  }
  return res.json() as Promise<T>
}

export function createAnalysis(url: string) {
  return request<{ id: string; status: AnalysisStatus }>('/analyses', {
    method: 'POST',
    body: JSON.stringify({ url }),
  })
}

export function getAnalysis(id: string) {
  return request<AnalysisResult>(`/analyses/${id}`)
}
