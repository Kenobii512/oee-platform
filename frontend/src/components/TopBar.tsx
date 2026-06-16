// Üst bar: marka, Müdür/Amir sekmeleri, senaryo seçici, tarih filtreleri (from/to), Uygula.
// Tarih girişleri yerel taslak state; Uygula'da parent'a iletilir (mevcut qs() mantığı).
import { useState } from 'react'

import type { Range } from '../api/types'
import ScenarioPicker from './ScenarioPicker'

export type View = 'manager' | 'supervisor'

interface Props {
  view: View
  onViewChange: (v: View) => void
  onApply: (range: Range) => void
  onActivateScenario: (id: string) => void
}

export default function TopBar({ view, onViewChange, onApply, onActivateScenario }: Props) {
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')

  return (
    <header className="topbar">
      <div className="brand">
        <span className="eyebrow">Üretim Verimliliği</span>
        <h1>OEE Panosu</h1>
      </div>
      <div className="controls">
        <div className="tabs">
          <button
            className={`tab${view === 'manager' ? ' active' : ''}`}
            onClick={() => onViewChange('manager')}
          >
            Müdür
          </button>
          <button
            className={`tab${view === 'supervisor' ? ' active' : ''}`}
            onClick={() => onViewChange('supervisor')}
          >
            Amir
          </button>
        </div>
        <ScenarioPicker onActivate={onActivateScenario} />
        <label>
          Başlangıç
          <input type="datetime-local" value={from} onChange={(e) => setFrom(e.target.value)} />
        </label>
        <label>
          Bitiş
          <input type="datetime-local" value={to} onChange={(e) => setTo(e.target.value)} />
        </label>
        <button onClick={() => onApply({ from: from || undefined, to: to || undefined })}>
          Uygula
        </button>
      </div>
    </header>
  )
}
