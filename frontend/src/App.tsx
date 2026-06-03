import { useState } from 'react'
import Login from './pages/Login'
import Translate from './pages/Translate'
import Settings from './pages/Settings'

type Page = 'login' | 'translate' | 'settings'

export default function App() {
  const [page, setPage] = useState<Page>('login')

  if (page === 'login') return <Login onSuccess={() => setPage('translate')} />

  return (
    <div style={{ maxWidth: 680, margin: '0 auto', padding: 24 }}>
      <nav style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 32 }}>
        <span style={{ fontWeight: 'bold', fontSize: 18 }}>📄 Doc Translator</span>
        <div style={{ display: 'flex', gap: 16, fontSize: 14 }}>
          <button onClick={() => setPage('translate')} style={{ background: 'none', border: 'none', color: page === 'translate' ? '#74c0fc' : '#888', cursor: 'pointer' }}>번역</button>
          <button onClick={() => setPage('settings')} style={{ background: 'none', border: 'none', color: page === 'settings' ? '#74c0fc' : '#888', cursor: 'pointer' }}>설정</button>
        </div>
      </nav>
      {page === 'translate' && <Translate />}
      {page === 'settings' && <Settings />}
    </div>
  )
}
