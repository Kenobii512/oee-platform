import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { ReplayTimeline } from '../api/types'
import LineStrip from './LineStrip'

const LINE = [
  { id: 'tankA', name: 'Tank A' },
  { id: 'tankB', name: 'Tank B' },
]
const TL: ReplayTimeline = {
  line: LINE,
  events: [
    { timestamp: '2026-01-05 06:00:00.000', carrier_id: 'CAR-0001', station_id: null, event_type: 'LOAD', duration: 0, reason_code: null },
    { timestamp: '2026-01-05 06:00:00.000', carrier_id: 'CAR-0001', station_id: 'HOIST', event_type: 'MOVE', duration: 0.5, reason_code: null },
    { timestamp: '2026-01-05 06:00:30.000', carrier_id: 'CAR-0001', station_id: 'tankA', event_type: 'PROCESS', duration: 5, reason_code: null },
    { timestamp: '2026-01-05 06:01:00.000', carrier_id: null, station_id: 'tankB', event_type: 'DOWNTIME', duration: 10, reason_code: 'rectifier_ariza' },
  ],
}

describe('LineStrip', () => {
  it('timeline yokken bekleme metni gösterir', () => {
    render(<LineStrip timeline={null} targetTo={null} tickMs={200} running={false} />)
    expect(screen.getByText(/Oynat/)).toBeInTheDocument()
  })

  it('duruştaki tank kırmızı sınıf + Türkçe neden etiketi alır', () => {
    render(
      <LineStrip timeline={TL} targetTo="2026-01-05 06:02:00.000" tickMs={200} running={true} />,
    )
    expect(screen.getByText('Redresör arızası')).toBeInTheDocument()
    expect(document.querySelector('.ls-tank-durus')).not.toBeNull()
    // Tank adları uçtan gelir, gömülü değil:
    expect(screen.getByText('Tank A')).toBeInTheDocument()
  })

  it('sayaçları gösterir (yüklenen/çıkan/redo)', () => {
    render(
      <LineStrip timeline={TL} targetTo="2026-01-05 06:02:00.000" tickMs={200} running={true} />,
    )
    expect(screen.getByText('Yüklenen')).toBeInTheDocument()
    expect(screen.getByText('Redo')).toBeInTheDocument()
  })
})
