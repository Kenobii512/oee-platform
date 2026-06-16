import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import type { DataQuality, Oee, Recommendations as RecData } from '../api/types'
import KpiCards from './KpiCards'
import Recommendations from './Recommendations'

const OEE: Oee = { oee: 0.62, availability: 0.86, performance: 0.81, quality: 0.88 }
const DQ: DataQuality = { downtime_entry_coverage: 0.95, microstop_entry_coverage: 0.2 }

describe('KpiCards', () => {
  it('OEE ve bileşenlerini yüzde olarak gösterir', () => {
    render(<KpiCards oee={OEE} dq={DQ} />)
    expect(screen.getByText('62.0%')).toBeInTheDocument()
    expect(screen.getByText('86.0%')).toBeInTheDocument()
    expect(screen.getByText('81.0%')).toBeInTheDocument()
    expect(screen.getByText('88.0%')).toBeInTheDocument()
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
      recovery_ratio: 0.3,
      title: 'Duruşları azalt',
      action: 'En sık duruş nedeni ariza_pompa.',
      assumption: 'Duruş TL’sinin ~%30 geri kazanılabilir.',
    },
  ],
}

describe('Recommendations', () => {
  it('öneri başlığını, kazancı ve TL kaybını gösterir', () => {
    render(<Recommendations rec={REC} />)
    expect(screen.getByText('Duruşları azalt')).toBeInTheDocument()
    expect(screen.getByText('~3.464 TL/dönem')).toBeInTheDocument()
    expect(screen.getByText(/11\.546 TL/)).toBeInTheDocument()
  })
})
