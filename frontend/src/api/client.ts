/**
 * Typed fetch wrapper for backend API calls.
 * Prepends /api to all paths, sets JSON headers, throws on error responses.
 */
export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const url = `/api${path}`

  const response = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
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
    throw new Error(message)
  }

  return response.json() as Promise<T>
}
