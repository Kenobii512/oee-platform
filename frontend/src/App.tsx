import { useState } from 'react'

import Dashboard from './views/Dashboard'
import Replay from './views/Replay'

type Mode = 'dashboard' | 'replay'

export default function App() {
  const [mode, setMode] = useState<Mode>('dashboard')
  return (
    <>
      <div className="blueprint" aria-hidden="true" />
      <div className="aurora" aria-hidden="true" />
      {/* Birleşik header — üst satır: tek marka + mod sekmeleri + CANLI.
          Görünüme özel kontrol satırı (filtreler) alttan view içinden gelir. */}
      <header className="apphead-top">
        <span className="brand-logo" aria-label="OEE Panosu">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M3 17 A9 9 0 0 1 21 17" stroke="#cdd4dc" strokeWidth="2.5" strokeLinecap="round" />
            <path d="M3 17 A9 9 0 0 1 15.5 8.8" stroke="#1f5da6" strokeWidth="2.5" strokeLinecap="round" />
            <line x1="12" y1="17" x2="15.5" y2="10.5" stroke="#16202b" strokeWidth="2" strokeLinecap="round" />
            <circle cx="12" cy="17" r="1.7" fill="#16202b" />
          </svg>
          <span className="wm">OEE Panosu</span>
        </span>
        <div className="modetabs" role="tablist" aria-label="Mod">
          <button
            role="tab"
            aria-selected={mode === 'dashboard'}
            className={`modetab${mode === 'dashboard' ? ' active' : ''}`}
            onClick={() => setMode('dashboard')}
          >
            Pano
          </button>
          <button
            role="tab"
            aria-selected={mode === 'replay'}
            className={`modetab${mode === 'replay' ? ' active' : ''}`}
            onClick={() => setMode('replay')}
          >
            Canlı Replay
          </button>
        </div>
        <span className="viewnav-status" aria-hidden="true">
          <span className={`led${mode === 'replay' ? ' live' : ''}`} />
          {mode === 'replay' ? 'CANLI' : 'HAZIR'}
        </span>
      </header>
      {mode === 'dashboard' ? <Dashboard /> : <Replay />}
    </>
  )
}
