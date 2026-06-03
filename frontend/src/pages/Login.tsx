import { useState } from 'react'
import { api } from '../api'

export default function Login({ onSuccess }: { onSuccess: () => void }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    const res = await api.login(password)
    setLoading(false)
    if (res.ok) {
      onSuccess()
    } else {
      setError('비밀번호가 틀렸습니다')
    }
  }

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: '100vh' }}>
      <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12, width: 300 }}>
        <h2 style={{ textAlign: 'center' }}>📄 Doc Translator</h2>
        <p style={{ textAlign: 'center', color: '#888', fontSize: 13 }}>팀 내부용 문서 번역 서비스</p>
        <input
          type="password"
          placeholder="비밀번호 입력..."
          value={password}
          onChange={e => setPassword(e.target.value)}
          style={{ padding: '10px 14px', borderRadius: 6, border: '1px solid #444', background: '#1a1a1a', color: '#fff' }}
        />
        {error && <p style={{ color: '#e03131', fontSize: 12, margin: 0 }}>{error}</p>}
        <button type="submit" disabled={loading || !password} style={{ padding: 10, borderRadius: 6, background: '#3b5bdb', color: '#fff', border: 'none', cursor: 'pointer' }}>
          {loading ? '확인 중...' : '입장하기'}
        </button>
      </form>
    </div>
  )
}
