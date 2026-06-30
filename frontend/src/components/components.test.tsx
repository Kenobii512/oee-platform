import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { DataQuality, LossCat, Oee, Recommendations as RecData } from '../api/types'
import { catLabel } from '../styles/theme'
import GaugeHero from './GaugeHero'
import LossTreeChart from './LossTreeChart'
import Recommendations from './Recommendations'

const OEE: Oee = { oee: 0.62, availability: 0.86, performance: 0.81, quality: 0.88, final_yield: 1.0 }
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

  it('utilization verildiğinde "Takvim kullanımı" gösterir (H8)', () => {
    render(<GaugeHero oee={{ ...OEE, utilization: 0.92 }} dq={DQ} />)
    expect(screen.getByText(/Takvim kullanımı/)).toBeInTheDocument()
  })

  it('utilization yoksa takvim satırını gizler', () => {
    const { container } = render(<GaugeHero oee={OEE} dq={DQ} />)
    expect(container.querySelector('.cs-util')).toBeNull()
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

  it('düşük güvenli (low_confidence) kalemde "düşük güven" rozetini gösterir', () => {
    const rec: RecData = {
      ...REC,
      recommendations: [{ ...REC.recommendations[0], kind: 'inferred', low_confidence: true }],
    }
    const { container } = render(<Recommendations rec={rec} />)
    const badge = container.querySelector('.rec-badge')
    expect(badge).not.toBeNull()
    expect(badge?.textContent).toMatch(/düşük güven/i)
  })

  it('güveni yüksek kalemde rozet göstermez', () => {
    const { container } = render(<Recommendations rec={REC} />)
    expect(container.querySelector('.rec-badge')).toBeNull()
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
