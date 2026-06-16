import { useState } from 'react'

import Dashboard from './views/Dashboard'
import Replay from './views/Replay'

type View = 'dashboard' | 'replay'

export default function App() {
  const [view, setView] = useState<View>('dashboard')
  return (
    <>
      <nav className="viewnav">
        <button
          className={view === 'dashboard' ? 'active' : ''}
          onClick={() => setView('dashboard')}
        >
          Pano
        </button>
        <button
          className={view === 'replay' ? 'active' : ''}
          onClick={() => setView('replay')}
        >
          Canlı Replay
        </button>
      </nav>
      {view === 'dashboard' ? <Dashboard /> : <Replay />}
    </>
  )
}
