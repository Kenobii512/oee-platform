// Birleşik header'ın kontrol satırı (markasız): Görünüm Özet/Detay + senaryo + tarih + Uygula.
// Tarih girişleri yerel taslak state; Uygula'da parent'a iletilir.
import { useState } from 'react'

import type { Range } from '../api/types'
import ScenarioDropdown from './ScenarioDropdown'

export type View = 'ozet' | 'detay'

interface Props {
  view: View
  onViewChange: (v: View) => void
  onApply: (range: Range) => void
  onActivateScenario: (id: string) => void
  activeScenario?: string
}

export default function TopBar({ view, onViewChange, onApply, onActivateScenario, activeScenario }: Props) {
  const [from, setFrom] = useState('')
  const [to, setTo] = useState('')

  return (
    <header className="apphead-controls">
      <div className="viewtoggle">
        <span className="viewtoggle-cap">Görünüm</span>
        <div className="vt-seg" role="tablist" aria-label="Görünüm">
          <button
            role="tab"
            aria-selected={view === 'ozet'}
            className={`vt${view === 'ozet' ? ' active' : ''}`}
            onClick={() => onViewChange('ozet')}
          >
            Özet
          </button>
          <button
            role="tab"
            aria-selected={view === 'detay'}
            className={`vt${view === 'detay' ? ' active' : ''}`}
            onClick={() => onViewChange('detay')}
          >
            Detay
          </button>
        </div>
      </div>
      <div className="controls">
        <ScenarioDropdown onSelect={onActivateScenario} value={activeScenario} />
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
