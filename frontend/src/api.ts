// In production, VITE_API_BASE_URL points to the Render backend URL
const BASE = import.meta.env.VITE_API_BASE_URL ?? ''

async function request(path: string, init?: RequestInit): Promise<Response> {
  const res = await fetch(`${BASE}${path}`, { credentials: 'include', ...init })
  if (res.status === 401) {
    window.location.href = '/'
  }
  return res
}

export const api = {
  login: (password: string) =>
    request('/auth/login', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ password }),
    }),

  logout: () => request('/auth/logout', { method: 'POST' }),

  getSettings: () => request('/settings'),

  updateApiKey: (api_key: string) =>
    request('/settings/api-key', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ api_key }),
    }),

  translate: (file: File, targetLang: string, sourceLang?: string) => {
    const form = new FormData()
    form.append('file', file)
    form.append('target_lang', targetLang)
    if (sourceLang) form.append('source_lang', sourceLang)
    return request('/translate', { method: 'POST', body: form })
  },
}
