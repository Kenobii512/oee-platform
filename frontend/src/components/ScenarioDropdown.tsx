// Zengin senaryo dropdown'u (native select yerine): her seçenek başlık + açıklama +
// "beklenen baş kayıp" gösterir (ScenarioInfo). Erişilebilir: aria-haspopup/expanded,
// role=listbox/option, Esc + dışarı tıkla kapat. Katalog yoksa (404) gizli.
import { useQuery } from '@tanstack/react-query'
import { useEffect, useRef, useState } from 'react'

import { api } from '../api/client'

interface Props {
  onSelect: (id: string) => void
  /** Başlangıç/kontrollü seçili senaryo id'si. */
  value?: string
  disabled?: boolean
}

export default function ScenarioDropdown({ onSelect, value, disabled }: Props) {
  const { data, isError } = useQuery({ queryKey: ['scenarios'], queryFn: api.scenarios })
  const [open, setOpen] = useState(false)
  const [sel, setSel] = useState<string | undefined>(value)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onDoc = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onDoc)
    document.addEventListener('keydown', onKey)
    return () => {
      document.removeEventListener('mousedown', onDoc)
      document.removeEventListener('keydown', onKey)
    }
  }, [open])

  if (isError || !data) return null

  const selected = data.scenarios.find((s) => s.id === sel)

  return (
    <div className="dd" ref={ref}>
      <span className="dd-cap">Senaryo</span>
      <button
        type="button"
        className="dd-trigger"
        aria-haspopup="listbox"
        aria-expanded={open}
        disabled={disabled}
        onClick={() => setOpen((o) => !o)}
      >
        <span className="dd-val">{selected ? selected.title : 'Senaryo seç'}</span>
        <svg className="dd-chev" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
          <path
            d="M2.5 4.5 6 8l3.5-3.5"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      </button>
      {open && (
        <ul className="dd-menu" role="listbox" aria-label="Senaryo seç">
          {data.scenarios.map((s) => (
            <li key={s.id} role="option" aria-selected={s.id === sel}>
              <button
                type="button"
                className={`dd-opt${s.id === sel ? ' sel' : ''}`}
                onClick={() => {
                  setSel(s.id)
                  onSelect(s.id)
                  setOpen(false)
                }}
              >
                <span className="dd-opt-title">{s.title}</span>
                <span className="dd-opt-desc">{s.description}</span>
                <span className="dd-opt-loss">Beklenen baş kayıp: {s.expected_top_loss}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
