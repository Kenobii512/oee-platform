// What-if paneli: kayıp azaltım slider'ları → önce/sonra A/P/Q/OEE + TL kazanç aralığı.
// Hesap BACKEND'te (/whatif — tek doğruluk kaynağı); burada yalnız kontrol + sunum.
// Dürüstlük dili panoyla aynı: kalemler bağımsız kabul edilir, kazanç üst sınırdır.
import { useQuery } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { api } from '../api/client'
import type { Range, Recommendations, WhatIfReductions } from '../api/types'
import { catLabel, num1, pct, tl } from '../styles/theme'
import Info from './Info'

const ZERO: WhatIfReductions = {
  downtime: 0,
  microstop: 0,
  speed_loss: 0,
  quality_redo: 0,
  fill_loss: 0,
}

const SLIDERS: Array<{ key: keyof WhatIfReductions; cat: string }> = [
  { key: 'downtime', cat: 'DOWNTIME' },
  { key: 'microstop', cat: 'MICROSTOP' },
  { key: 'speed_loss', cat: 'SPEED_LOSS' },
  { key: 'quality_redo', cat: 'QUALITY_REDO' },
  { key: 'fill_loss', cat: 'FILL_LOSS' },
]

/** 300ms debounce: slider sürüklenirken istek fırtınası olmasın. */
function useDebounced<T>(value: T, ms = 300): T {
  const [v, setV] = useState(value)
  useEffect(() => {
    const t = setTimeout(() => setV(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return v
}

interface Props {
  range: Range
  /** "Önerilen değerler" için öneri motorunun geri-kazanım oranları. */
  rec?: Recommendations
}

export default function WhatIf({ range, rec }: Props) {
  const [red, setRed] = useState<WhatIfReductions>(ZERO)
  const debounced = useDebounced(red)
  const active = Object.values(debounced).some((v) => v > 0)

  const q = useQuery({
    queryKey: ['whatif', debounced, range],
    queryFn: () => api.whatif(debounced, range),
    enabled: active,
    placeholderData: (prev) => prev, // slider oynarken eski sonuç titremesin
  })

  const set = (key: keyof WhatIfReductions, v: number) =>
    setRed((r) => ({ ...r, [key]: v }))

  /** Öneri motorunun varsayımlarını slider'lara taşı (tutarlılık: aynı oranlar). */
  const applyRecommended = () => {
    if (!rec) return
    const next = { ...ZERO }
    for (const r of rec.recommendations) {
      const s = SLIDERS.find((x) => x.cat === r.category)
      if (s) next[s.key] = Math.round(r.recovery_ratio * 100) / 100
    }
    setRed(next)
  }

  const base = q.data?.baseline
  const adj = q.data?.adjusted
  const gain = q.data?.gain

  return (
    <section className="shell whatif">
      <div className="core">
        <div className="card-head">
          <span className="eyebrow">
            What-if · Kaybı Azaltsam Ne Olur?{' '}
            <Info text="Analitik tahmin: kalemler bağımsız kabul edilir, örtüşebilir; kazançlar üst sınırdır. Hesap sunucuda, pano metrikleriyle aynı mantıkla yapılır." />
          </span>
          <span className="wi-actions">
            <button type="button" className="wi-btn" onClick={applyRecommended} disabled={!rec}>
              Önerilen değerler
            </button>
            <button
              type="button"
              className="wi-btn ghost"
              onClick={() => setRed(ZERO)}
              disabled={!active}
            >
              Sıfırla
            </button>
          </span>
        </div>

        <div className="wi-grid">
          <div className="wi-sliders">
            {SLIDERS.map(({ key, cat }) => (
              <label key={key} className="wi-slider">
                <span className="wi-cap">
                  {catLabel(cat)}
                  <strong>−{Math.round(red[key] * 100)}%</strong>
                </span>
                <input
                  type="range"
                  min={0}
                  max={50}
                  step={5}
                  value={Math.round(red[key] * 100)}
                  aria-label={`${catLabel(cat)} azaltım yüzdesi`}
                  onChange={(e) => set(key, Number(e.target.value) / 100)}
                />
              </label>
            ))}
          </div>

          <div className="wi-result" aria-live="polite">
            {!active ? (
              <p className="wi-hint">
                Soldaki kaydırıcılarla bir kaybı azaltın; OEE ve ₺ etkisi burada belirir.
              </p>
            ) : q.isError ? (
              <p className="wi-hint">What-if alınamadı — sunucu loglarına bakın.</p>
            ) : base && adj && gain ? (
              <>
                <table className="wi-table">
                  <thead>
                    <tr>
                      <th></th>
                      <th>Şimdi</th>
                      <th>What-if</th>
                      <th>Δ</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(
                      [
                        ['Kullanılabilirlik', base.availability, adj.availability],
                        ['Performans', base.performance, adj.performance],
                        ['Kalite (ilk-geçiş)', base.quality, adj.quality],
                        ['OEE', base.oee, adj.oee],
                      ] as Array<[string, number, number]>
                    ).map(([label, b, a]) => (
                      <tr key={label} className={label === 'OEE' ? 'wi-oee' : undefined}>
                        <td>{label}</td>
                        <td>{pct(b)}</td>
                        <td>{pct(a)}</td>
                        <td className={a > b + 1e-9 ? 'up' : ''}>
                          {a > b + 1e-9 ? `+${num1((a - b) * 100)} p` : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="wi-gain">
                  Tahmini kazanç{' '}
                  <strong>
                    {tl(gain.total_tl_low)} – {tl(gain.total_tl_high)} ₺
                  </strong>
                  <span className="wi-note">üst sınır; kalemler örtüşebilir</span>
                </div>
              </>
            ) : (
              <p className="wi-hint">Hesaplanıyor…</p>
            )}
          </div>
        </div>
      </div>
    </section>
  )
}
