import { useState, useEffect } from 'react'
import { api } from '../api'

function ApiKeySection({
  label,
  keySet,
  onSave,
}: {
  label: string
  keySet: boolean | null
  onSave: (key: string) => Promise<boolean>
}) {
  const [newKey, setNewKey] = useState('')
  const [loading, setLoading] = useState(false)
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    if (loading || !newKey) return
    setError('')
    setSaved(false)
    setLoading(true)
    try {
      const ok = await onSave(newKey)
      if (ok) {
        setSaved(true)
        setNewKey('')
      } else {
        setError('저장에 실패했습니다')
      }
    } catch {
      setError('네트워크 오류가 발생했습니다')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ padding: 16, border: '1px solid #333', borderRadius: 8 }}>
      <p style={{ margin: '0 0 8px', fontSize: 13, color: '#888' }}>{label}</p>
      <p style={{ margin: '0 0 16px', fontWeight: 'bold', color: keySet ? '#4caf50' : '#e03131' }}>
        {keySet === null ? '확인 중...' : keySet ? '✅ 설정됨' : '❌ 미설정'}
      </p>
      <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
        <input
          type="password"
          placeholder="새 API 키 입력..."
          value={newKey}
          onChange={e => { setNewKey(e.target.value); setSaved(false) }}
          style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #444', background: '#1a1a1a', color: '#fff' }}
        />
        {saved && <p style={{ color: '#4caf50', fontSize: 12, margin: 0 }}>✅ 저장됐습니다</p>}
        {error && <p style={{ color: '#e03131', fontSize: 12, margin: 0 }}>{error}</p>}
        <button type="submit" disabled={!newKey || loading}
          style={{ padding: '8px 16px', borderRadius: 6, background: '#3b5bdb', color: '#fff', border: 'none', cursor: !newKey || loading ? 'not-allowed' : 'pointer', alignSelf: 'flex-start' }}>
          {loading ? '저장 중...' : '저장'}
        </button>
      </form>
    </div>
  )
}

export default function Settings() {
  const [openaiKeySet, setOpenaiKeySet] = useState<boolean | null>(null)
  const [googleKeySet, setGoogleKeySet] = useState<boolean | null>(null)

  useEffect(() => {
    api.getSettings()
      .then(r => r.json())
      .then(d => {
        setOpenaiKeySet(d.openai_key_set ?? false)
        setGoogleKeySet(d.google_key_set ?? false)
      })
      .catch(() => {
        setOpenaiKeySet(false)
        setGoogleKeySet(false)
      })
  }, [])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <h2>설정</h2>
      <ApiKeySection
        label="OpenAI API 키 (ChatGPT 번역)"
        keySet={openaiKeySet}
        onSave={async (key) => {
          const res = await api.updateApiKey(key)
          if (res.ok) setOpenaiKeySet(true)
          return res.ok
        }}
      />
      <ApiKeySection
        label="Google Translate API 키"
        keySet={googleKeySet}
        onSave={async (key) => {
          const res = await api.updateGoogleApiKey(key)
          if (res.ok) setGoogleKeySet(true)
          return res.ok
        }}
      />
    </div>
  )
}
