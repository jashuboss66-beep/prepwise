const API_URL = import.meta.env.VITE_API_URL || ''

export async function api(path, options = {}) {
  let response
  try {
    response = await fetch(`${API_URL}${path}`, {
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...options.headers },
      ...options,
    })
  } catch {
    throw new Error('Cannot reach the Flask API. Start the local app with "npm run dev" from the frontend folder.')
  }
  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    if (response.status >= 500 && !body.error) {
      throw new Error('The Flask API is unavailable. Restart the app with "npm run dev" from the frontend folder.')
    }
    throw new Error(body.error || 'Something went wrong. Please try again.')
  }
  return body
}
