// QC: getJSON backend hata `detail`'ini yüzeye çıkarır (H9 400 mesajları).
import { afterEach, describe, expect, it, vi } from 'vitest'

import { getJSON } from './client'

afterEach(() => vi.unstubAllGlobals())

describe('getJSON', () => {
  it('400 detail mesajını hataya taşır', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => new Response(JSON.stringify({ detail: 'geçersiz tarih (from)' }), { status: 400 })),
    )
    await expect(getJSON('/oee?from=bozuk')).rejects.toThrow('geçersiz tarih (from)')
  })

  it('detail yoksa path -> status fallback verir', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response('nope', { status: 500 })))
    await expect(getJSON('/x')).rejects.toThrow('/x -> 500')
  })
})
