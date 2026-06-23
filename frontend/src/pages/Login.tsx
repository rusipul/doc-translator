import { useState, useEffect, useRef } from 'react'
import { api } from '../api'
import Logo from '../components/Logo'

const BASE = import.meta.env.VITE_API_BASE_URL ?? ''

export default function Login({ onSuccess }: { onSuccess: () => void }) {
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [slowLoading, setSlowLoading] = useState(false)
  const slowTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Warmup ping: wake Render out of sleep while user types password
  useEffect(() => {
    fetch(`${BASE}/health`).catch(() => {})
  }, [])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setSlowLoading(false)
    setError('')
    slowTimer.current = setTimeout(() => setSlowLoading(true), 5000)
    const res = await api.login(password)
    if (slowTimer.current) clearTimeout(slowTimer.current)
    setLoading(false)
    setSlowLoading(false)
    if (res.ok) {
      onSuccess()
    } else {
      setError('비밀번호가 틀렸습니다')
    }
  }

  return (
    <div style={{
      display: 'flex',
      justifyContent: 'center',
      alignItems: 'center',
      minHeight: '100vh',
      background: '#0f0f0f',
    }}>
      <form onSubmit={handleSubmit} style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 16,
        width: 320,
        padding: '40px 32px',
        background: '#1a1a1a',
        borderRadius: 12,
        border: '1px solid #2a2a2a',
        boxShadow: '0 8px 32px rgba(0,0,0,0.4)',
      }}>
        {/* Logo */}
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 4 }}>
          <Logo size="lg" />
        </div>

        {/* Service name */}
        <div style={{ textAlign: 'center' }}>
          <p style={{ color: '#aaa', fontSize: 13, margin: 0 }}>문서 번역 서비스</p>
        </div>

        <div style={{ height: 1, background: '#2a2a2a', margin: '4px 0' }} />

        <input
          type="password"
          placeholder="비밀번호 입력..."
          value={password}
          onChange={e => setPassword(e.target.value)}
          style={{
            padding: '11px 14px',
            borderRadius: 6,
            border: '1px solid #333',
            background: '#111',
            color: '#fff',
            fontSize: 14,
            outline: 'none',
          }}
        />
        {error && <p style={{ color: '#E31E24', fontSize: 12, margin: 0 }}>{error}</p>}
        <button
          type="submit"
          disabled={loading || !password}
          style={{
            padding: 11,
            borderRadius: 6,
            background: loading || !password ? '#333' : '#E31E24',
            color: '#fff',
            border: 'none',
            cursor: loading || !password ? 'not-allowed' : 'pointer',
            fontWeight: 600,
            fontSize: 14,
            transition: 'background 0.15s',
          }}
        >
          {loading ? (slowLoading ? '서버 기동 중... (잠시 기다려 주세요)' : '확인 중...') : '로그인'}
        </button>
      </form>
    </div>
  )
}
