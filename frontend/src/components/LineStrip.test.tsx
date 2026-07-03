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

  it('sayaç etiketlerini VE değerlerini gösterir (yüklenen/çıkan/redo)', () => {
    render(
      <LineStrip timeline={TL} targetTo="2026-01-05 06:02:00.000" tickMs={200} running={true} />,
    )
    expect(screen.getByText('Yüklenen')).toBeInTheDocument()
    expect(screen.getByText('Çıkan')).toBeInTheDocument()
    expect(screen.getByText('Redo')).toBeInTheDocument()
    // Kurgu: 1 LOAD, 0 UNLOAD, 0 STRIP → değerler indirgeyiciden birebir akar.
    const values = Array.from(document.querySelectorAll('.ls-counters strong')).map(
      (el) => el.textContent,
    )
    expect(values).toEqual(['1', '0', '0'])
  })

  it('error verildiğinde hata metni gösterir (bekleme metniyle karışmaz)', () => {
    render(<LineStrip timeline={null} targetTo={null} tickMs={200} running={false} error />)
    expect(screen.getByText(/yüklenemedi/)).toBeInTheDocument()
    expect(screen.queryByText(/Oynat'a basın/)).toBeNull()
  })

  it('hat tanımında olmayan istasyondaki askı çizilmez (kirli veri)', () => {
    const dirty: ReplayTimeline = {
      line: LINE,
      events: [
        ...TL.events,
        { timestamp: '2026-01-05 06:00:30.000', carrier_id: 'CAR-0002', station_id: null, event_type: 'LOAD', duration: 0, reason_code: null },
        { timestamp: '2026-01-05 06:00:40.000', carrier_id: 'CAR-0002', station_id: 'hayalet_tank', event_type: 'PROCESS', duration: 5, reason_code: null },
      ],
    }
    render(
      <LineStrip timeline={dirty} targetTo="2026-01-05 06:02:00.000" tickMs={200} running={true} />,
    )
    // CAR-0001 tankA'da çizilir; hayalet istasyondaki CAR-0002 sessizce atlanır.
    expect(document.querySelectorAll('.ls-chip').length).toBe(1)
  })
})
