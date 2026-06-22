import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { DataQuality, LossCat, Oee, Recommendations as RecData } from '../api/types'
import { catLabel, hm, int } from '../styles/theme'
import GaugeHero from './GaugeHero'
import LossTreeChart from './LossTreeChart'
import Recommendations from './Recommendations'
import ShiftSummary from './ShiftSummary'

const OEE: Oee = {
  oee: 0.62, availability: 0.86, performance: 0.81, quality: 0.88, final_yield: 1.0,
  utilization: 0.55, planned_downtime_min: 120, downtime_union_min: 47,
  span_min: 480, loaded_qty: 24090, good_count: 23940, redo_count: 150,
}
const DQ: DataQuality = { microstop_entry_coverage: 0.2 }

describe('GaugeHero', () => {
  it('OEE gauge okumasını ve A/P/Q metre değerlerini gösterir', () => {
    render(<GaugeHero oee={OEE} dq={DQ} />)
    // Gauge sayıyı %'siz, "% OEE" etiketiyle; hücreler sayıyı ayrı <small>% ile.
    expect(screen.getByText('62,0')).toBeInTheDocument()
    expect(screen.getByText('86,0')).toBeInTheDocument()
    expect(screen.getByText('81,0')).toBeInTheDocument()
    expect(screen.getByText('88,0')).toBeInTheDocument()
  })

  it('Kullanılabilirlik alt-bilgisinde planlı/plansız duruşu gösterir', () => {
    render(<GaugeHero oee={OEE} dq={DQ} />)
    expect(screen.getByText('120 dk')).toBeInTheDocument()
    expect(screen.getByText('47 dk')).toBeInTheDocument()
  })
})

const REC: RecData = {
  total_estimated_gain_tl: 3464,
  recommendations: [
    {
      category: 'DOWNTIME',
      axis: 'minutes',
      value: 231,
      kind: 'visible',
      tl: 11546,
      estimated_gain_tl: 3464,
      estimated_gain_tl_low: 1732,
      estimated_gain_tl_high: 3464,
      recovery_ratio: 0.3,
      title: 'Duruşları azalt',
      action: 'En sık duruş nedeni ariza_pompa.',
      assumption: 'Duruş TL’sinin ~%30 geri kazanılabilir.',
    },
  ],
}

describe('Recommendations', () => {
  it('öneri başlığını, kazanç aralığını ve ₺ kaybını gösterir', () => {
    render(<Recommendations rec={REC} />)
    expect(screen.getByText('Duruşları azalt')).toBeInTheDocument()
    expect(screen.getByText('~1.732–3.464 ₺/dönem')).toBeInTheDocument()
    expect(screen.getByText(/11\.546 ₺/)).toBeInTheDocument()
  })

  it('aksiyon metnindeki `kod` token\'ını <code> olarak render eder (ham backtick değil)', () => {
    const rec: RecData = {
      ...REC,
      recommendations: [{ ...REC.recommendations[0], action: 'En sık neden `ariza_pompa`.' }],
    }
    const { container } = render(<Recommendations rec={rec} />)
    const code = container.querySelector('.rec-action code')
    expect(code).not.toBeNull()
    expect(code?.textContent).toBe('ariza_pompa')
    // Ham backtick metinde kalmamalı.
    expect(container.querySelector('.rec-action')?.textContent).not.toContain('`')
  })
})

describe('catLabel', () => {
  it('kategori kodunu Türkçe isme çevirir, bilinmeyende ham koda düşer', () => {
    expect(catLabel('DOWNTIME')).toBe('Duruş')
    expect(catLabel('MICROSTOP')).toBe('Mikro duruş')
    expect(catLabel('SPEED_LOSS')).toBe('Hız kaybı')
    expect(catLabel('BILINMEYEN_KOD')).toBe('BILINMEYEN_KOD')
  })
})

describe('LossTreeChart', () => {
  const cats: LossCat[] = [
    { category: 'DOWNTIME', axis: 'minutes', value: 200, kind: 'visible' },
    { category: 'SPEED_LOSS', axis: 'minutes', value: 100, kind: 'inferred' },
  ]
  it('ham kod yerine Türkçe etiket gösterir', () => {
    render(<LossTreeChart eyebrow="Kayıp" cats={cats} />)
    expect(screen.getByText('Duruş')).toBeInTheDocument()
    expect(screen.queryByText('DOWNTIME')).toBeNull()
  })
  it('legend={false} ile alt hatch notunu gizler', () => {
    const { container } = render(<LossTreeChart eyebrow="Kayıp" cats={cats} legend={false} />)
    expect(container.querySelector('.prop-note')).toBeNull()
  })
})

describe('ShiftSummary', () => {
  it('kullanım, gözlem penceresi ve ham parça sayılarını gösterir', () => {
    render(<ShiftSummary oee={OEE} />)
    expect(screen.getByText('55,0%')).toBeInTheDocument() // utilization
    expect(screen.getByText('8 sa 0 dk')).toBeInTheDocument() // span_min=480
    expect(screen.getByText('24.090')).toBeInTheDocument() // loaded
    expect(screen.getByText('23.940')).toBeInTheDocument() // good
    expect(screen.getByText('150')).toBeInTheDocument() // redo
  })
})

describe('formatters', () => {
  it('int: Türkçe binlik ayraç', () => {
    expect(int(24090)).toBe('24.090')
    expect(int(150)).toBe('150')
  })
  it('hm: dakika → "sa dk"', () => {
    expect(hm(480)).toBe('8 sa 0 dk')
    expect(hm(95)).toBe('1 sa 35 dk')
    expect(hm(0)).toBe('0 sa 0 dk')
  })
})
