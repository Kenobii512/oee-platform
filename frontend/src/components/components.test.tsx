import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { DataQuality, Oee, Recommendations as RecData } from '../api/types'
import GaugeHero from './GaugeHero'
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
  it('öneri başlığını, kazanç aralığını ve TL kaybını gösterir', () => {
    render(<Recommendations rec={REC} />)
    expect(screen.getByText('Duruşları azalt')).toBeInTheDocument()
    expect(screen.getByText('~1.732–3.464 TL/dönem')).toBeInTheDocument()
    expect(screen.getByText(/11\.546 TL/)).toBeInTheDocument()
  })
})
