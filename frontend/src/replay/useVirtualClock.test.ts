import { describe, expect, it } from 'vitest'

import { interpolate } from './useVirtualClock'

describe('interpolate — sanal saat lineer yaklaşım', () => {
  it('elapsed=0 → prev; elapsed≥tick → target; yarıda → orta', () => {
    expect(interpolate(100, 200, 0, 200)).toBe(100)
    expect(interpolate(100, 200, 200, 200)).toBe(200)
    expect(interpolate(100, 200, 300, 200)).toBe(200) // taşma kıskacı
    expect(interpolate(100, 200, 100, 200)).toBe(150)
  })

  it('tickMs=0 → doğrudan hedef (bölme koruması)', () => {
    expect(interpolate(100, 200, 50, 0)).toBe(200)
  })
})
