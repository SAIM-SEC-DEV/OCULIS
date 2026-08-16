let activeRequests = 0

const REQUEST_TIMEOUT = 12000

function emit(extra: Record<string, unknown> = {}) {
  window.dispatchEvent(
    new CustomEvent('oculis:runtime:requests', {
      detail: {
        active: activeRequests,
        ...extra,
      },
    }),
  )
}

export async function monitoredFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  activeRequests++
  emit({ delayed: false })

  const controller = new AbortController()

  const externalSignal = init?.signal

  if (externalSignal) {
    if (externalSignal.aborted) {
      controller.abort()
    } else {
      externalSignal.addEventListener(
        'abort',
        () => controller.abort(),
        { once: true },
      )
    }
  }

  const timer = window.setTimeout(() => {
    emit({ delayed: true })
  }, REQUEST_TIMEOUT)

  try {
    return await fetch(input, {
      ...init,
      signal: controller.signal,
    })
  } finally {
    window.clearTimeout(timer)
    activeRequests = Math.max(0, activeRequests - 1)

    emit({
      delayed: false,
    })
  }
}
