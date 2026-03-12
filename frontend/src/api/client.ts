/**
 * Typed fetch wrapper for backend API calls.
 * Prepends /api to all paths, sets JSON headers, throws on error responses.
 * Automatically includes the JWT Bearer token if one is stored.
 */
export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `/api${path}`

  // Read token from Zustand-persisted storage
  let authHeader: Record<string, string> = {}
  try {
    const raw = localStorage.getItem('roost-auth')
    if (raw) {
      const stored = JSON.parse(raw) as { state?: { token?: string } }
      const token = stored?.state?.token
      if (token) authHeader = { Authorization: `Bearer ${token}` }
    }
  } catch {
    // ignore storage errors
  }

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...authHeader,
      ...options.headers,
    },
  })

  if (!response.ok) {
    let message = `HTTP ${response.status}: ${response.statusText}`
    try {
      const errorBody = (await response.json()) as { detail?: string }
      if (errorBody.detail) {
        message =
          typeof errorBody.detail === 'string'
            ? errorBody.detail
            : JSON.stringify(errorBody.detail)
      }
    } catch {
      // Body was not JSON — use HTTP status text
    }
    const err = new Error(message) as Error & { status: number }
    err.status = response.status
    throw err
  }

  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}
