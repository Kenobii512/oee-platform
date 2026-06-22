import { useState } from 'react'

import Dashboard from './views/Dashboard'
import Replay from './views/Replay'

type View = 'dashboard' | 'replay'

export default function App() {
  const [view, setView] = useState<View>('dashboard')
  return (
    <>
      <nav className="viewnav">
        <span className="viewnav-brand" aria-hidden="true">OEE</span>
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
