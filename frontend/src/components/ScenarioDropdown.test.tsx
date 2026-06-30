// H6 — senaryo dropdown'u demo anlatısını gösterir.
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { describe, expect, it, vi } from 'vitest'

vi.mock('../api/client', () => ({
  api: {
    scenarios: () =>
      Promise.resolve({
        scenarios: [
          {
            id: 'baseline',
            title: 'Normal hafta',
            description: 'Tipik hafta',
            expected_top_loss: 'DOWNTIME',
            narrative: 'Sıradan bir vardiya hikâyesi',
            highlight: 'cost',
          },
        ],
      }),
  },
}))

import ScenarioDropdown from './ScenarioDropdown'

function withClient(ui: ReactNode) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(<QueryClientProvider client={qc}>{ui}</QueryClientProvider>)
}

describe('ScenarioDropdown', () => {
  it('seçenekte senaryo anlatısını gösterir', async () => {
    withClient(<ScenarioDropdown onSelect={() => {}} />)
    await waitFor(() => expect(screen.getByText('Senaryo seç')).toBeInTheDocument())
    fireEvent.click(screen.getByText('Senaryo seç'))
    expect(await screen.findByText('Sıradan bir vardiya hikâyesi')).toBeInTheDocument()
  })
})
