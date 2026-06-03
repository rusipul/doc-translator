import { useState, useEffect } from 'react'
import { api } from '../api'

export default function Settings() {
  const [apiKeySet, setApiKeySet] = useState<boolean | null>(null)
  const [newKey, setNewKey] = useState('')
  const [saved, setSaved] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    api.getSettings()
      .then(r => r.json())
      .then(d => setApiKeySet(d.api_key_set))
  }, [])

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSaved(false)
    const res = await api.updateApiKey(newKey)
    if (res.ok) {
      setSaved(true)
      setApiKeySet(true)
      setNewKey('')
    } else {
      setError('저장에 실패했습니다')
    }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <h2>설정</h2>
      <div style={{ padding: 16, border: '1px solid #333', borderRadius: 8 }}>
        <p style={{ margin: '0 0 8px', fontSize: 13, color: '#888' }}>Google Translate API 키</p>
        <p style={{ margin: '0 0 16px', fontWeight: 'bold', color: apiKeySet ? '#4caf50' : '#e03131' }}>
          {apiKeySet === null ? '확인 중...' : apiKeySet ? '✅ 설정됨' : '❌ 미설정'}
        </p>
        <form onSubmit={handleSave} style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <input
            type="password"
            placeholder="새 API 키 입력..."
            value={newKey}
            onChange={e => setNewKey(e.target.value)}
            style={{ padding: '8px 12px', borderRadius: 6, border: '1px solid #444', background: '#1a1a1a', color: '#fff' }}
          />
          {saved && <p style={{ color: '#4caf50', fontSize: 12, margin: 0 }}>✅ 저장됐습니다</p>}
          {error && <p style={{ color: '#e03131', fontSize: 12, margin: 0 }}>{error}</p>}
          <button type="submit" disabled={!newKey} style={{ padding: '8px 16px', borderRadius: 6, background: '#3b5bdb', color: '#fff', border: 'none', cursor: 'pointer', alignSelf: 'flex-start' }}>
            저장
          </button>
        </form>
      </div>
    </div>
  )
}
