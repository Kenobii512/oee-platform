import { useState } from 'react'

import Dashboard from './views/Dashboard'
import Replay from './views/Replay'

type View = 'dashboard' | 'replay'

export default function App() {
  const [view, setView] = useState<View>('dashboard')
  return (
    <>
      <div className="blueprint" aria-hidden="true" />
      <nav className="viewnav">
        <span className="brand-logo" aria-label="OEE">
          <svg width="22" height="22" viewBox="0 0 24 24" fill="none" aria-hidden="true">
            <path d="M3 17 A9 9 0 0 1 21 17" stroke="#cdd4dc" strokeWidth="2.5" strokeLinecap="round" />
            <path d="M3 17 A9 9 0 0 1 15.5 8.8" stroke="#1f5da6" strokeWidth="2.5" strokeLinecap="round" />
            <line x1="12" y1="17" x2="15.5" y2="10.5" stroke="#16202b" strokeWidth="2" strokeLinecap="round" />
            <circle cx="12" cy="17" r="1.7" fill="#16202b" />
          </svg>
          <span className="wm">OEE</span>
        </span>
        <div className="seg" role="tablist" aria-label="Görünüm">
          <button
            role="tab"
            aria-selected={view === 'dashboard'}
            className={view === 'dashboard' ? 'active' : ''}
            onClick={() => setView('dashboard')}
          >
            Pano
          </button>
          <button
            role="tab"
            aria-selected={view === 'replay'}
            className={view === 'replay' ? 'active' : ''}
            onClick={() => setView('replay')}
          >
            Canlı Replay
          </button>
        </div>
        <span className="viewnav-status" aria-hidden="true">
          <span className="led" />
          CANLI
        </span>
      </nav>
      {view === 'dashboard' ? <Dashboard /> : <Replay />}
    </>
  )
}
