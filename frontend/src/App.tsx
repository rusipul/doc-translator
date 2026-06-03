import { useState } from 'react'
import Login from './pages/Login'
import Translate from './pages/Translate'
import Settings from './pages/Settings'
import Logo from './components/Logo'

type Page = 'login' | 'translate' | 'settings'

export default function App() {
  const [page, setPage] = useState<Page>('login')

  if (page === 'login') return <Login onSuccess={() => setPage('translate')} />

  return (
    <div style={{ maxWidth: 720, margin: '0 auto', padding: '0 24px 40px' }}>
      {/* Header */}
      <nav style={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: '16px 0',
        marginBottom: 32,
        borderBottom: '1px solid #222',
      }}>
        <Logo size="sm" />
        <div style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
          <NavButton label="번역" active={page === 'translate'} onClick={() => setPage('translate')} />
          <NavButton label="설정" active={page === 'settings'} onClick={() => setPage('settings')} />
        </div>
      </nav>

      {page === 'translate' && <Translate />}
      {page === 'settings' && <Settings />}
    </div>
  )
}

function NavButton({ label, active, onClick }: { label: string; active: boolean; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '6px 14px',
        borderRadius: 6,
        border: 'none',
        background: active ? '#E31E24' : 'transparent',
        color: active ? '#fff' : '#888',
        cursor: 'pointer',
        fontSize: 13,
        fontWeight: active ? 600 : 400,
        transition: 'all 0.15s',
      }}
    >
      {label}
    </button>
  )
}
