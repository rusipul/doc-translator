import { useState, useRef } from 'react'
import { api } from '../api'

const LANGUAGES = [
  { code: 'en', name: '영어' }, { code: 'ja', name: '일본어' },
  { code: 'zh', name: '중국어(간체)' }, { code: 'ko', name: '한국어' },
  { code: 'fr', name: '프랑스어' }, { code: 'de', name: '독일어' },
  { code: 'es', name: '스페인어' }, { code: 'vi', name: '베트남어' },
]

type State = 'idle' | 'translating' | 'done' | 'error'

export default function Translate() {
  const [file, setFile] = useState<File | null>(null)
  const [targetLang, setTargetLang] = useState('en')
  const [state, setState] = useState<State>('idle')
  const [errorMsg, setErrorMsg] = useState('')
  const [downloadUrl, setDownloadUrl] = useState('')
  const [downloadName, setDownloadName] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    const f = e.dataTransfer.files[0]
    if (f) setFile(f)
  }

  const handleTranslate = async () => {
    if (!file) return
    if (file.size > 20 * 1024 * 1024) {
      setErrorMsg('파일이 20MB를 초과합니다')
      return
    }
    setState('translating')
    setErrorMsg('')
    const res = await api.translate(file, targetLang)
    if (res.ok) {
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const disposition = res.headers.get('content-disposition') || ''
      const match = disposition.match(/filename="(.+)"/)
      setDownloadUrl(url)
      setDownloadName(match?.[1] ?? 'translated_file')
      setState('done')
    } else {
      const body = await res.json().catch(() => ({}))
      setErrorMsg(body.detail ?? '번역에 실패했습니다')
      setState('error')
    }
  }

  const reset = () => {
    setFile(null)
    setState('idle')
    setDownloadUrl('')
    setDownloadName('')
    setErrorMsg('')
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <h2>문서 번역</h2>

      {/* Upload zone */}
      <div
        onDrop={handleDrop}
        onDragOver={e => e.preventDefault()}
        onClick={() => inputRef.current?.click()}
        style={{ border: '2px dashed #3b5bdb', borderRadius: 12, padding: 40, textAlign: 'center', cursor: 'pointer', background: '#1a1a2e' }}
      >
        <input ref={inputRef} type="file" accept=".docx,.xlsx,.pptx" hidden onChange={e => setFile(e.target.files?.[0] ?? null)} />
        <p style={{ fontSize: 24 }}>📂</p>
        <p style={{ color: '#74c0fc', fontWeight: 'bold' }}>
          {file ? file.name : '파일을 드래그하거나 클릭해서 선택'}
        </p>
        <p style={{ color: '#888', fontSize: 12 }}>.docx · .xlsx · .pptx · 최대 20MB</p>
      </div>

      {/* Language select */}
      <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end' }}>
        <div style={{ flex: 1 }}>
          <label style={{ fontSize: 12, color: '#888', display: 'block', marginBottom: 4 }}>번역할 언어</label>
          <select value={targetLang} onChange={e => setTargetLang(e.target.value)}
            style={{ width: '100%', padding: '8px 12px', borderRadius: 6, border: '1px solid #444', background: '#1a1a1a', color: '#fff' }}>
            {LANGUAGES.map(l => <option key={l.code} value={l.code}>{l.name}</option>)}
          </select>
        </div>
      </div>

      {/* Action */}
      {state === 'idle' || state === 'error' ? (
        <>
          <button onClick={handleTranslate} disabled={!file}
            style={{ padding: 12, borderRadius: 8, background: file ? '#3b5bdb' : '#333', color: '#fff', border: 'none', cursor: file ? 'pointer' : 'not-allowed', fontSize: 15 }}>
            번역 시작
          </button>
          {errorMsg && <p style={{ color: '#e03131', fontSize: 13 }}>{errorMsg}</p>}
        </>
      ) : state === 'translating' ? (
        <div style={{ padding: 20, textAlign: 'center', color: '#74c0fc' }}>
          ⏳ 번역 중입니다. 잠시 기다려주세요...
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <a href={downloadUrl} download={downloadName}
            style={{ display: 'block', padding: 12, borderRadius: 8, background: '#2f9e44', color: '#fff', textAlign: 'center', textDecoration: 'none', fontSize: 15 }}>
            ⬇️ {downloadName} 다운로드
          </a>
          <button onClick={reset} style={{ padding: 8, background: 'none', border: '1px solid #444', borderRadius: 6, color: '#888', cursor: 'pointer' }}>
            다른 파일 번역하기
          </button>
        </div>
      )}
    </div>
  )
}
