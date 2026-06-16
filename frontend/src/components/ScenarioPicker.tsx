// G8 senaryo seçici: /scenarios kataloğunu doldurur; değişimde onActivate(id) çağırır.
// Katalog yoksa (404) seçici gizli kalır (mevcut Jinja davranışı).
import { useQuery } from '@tanstack/react-query'

import { api } from '../api/client'

export default function ScenarioPicker({ onActivate }: { onActivate: (id: string) => void }) {
  const { data, isError } = useQuery({
    queryKey: ['scenarios'],
    queryFn: api.scenarios,
  })

  if (isError || !data) return null

  return (
    <label>
      Senaryo
      <select onChange={(e) => onActivate(e.target.value)} defaultValue="">
        {data.scenarios.map((s) => (
          <option key={s.id} value={s.id} title={s.description}>
            {s.title}
          </option>
        ))}
      </select>
    </label>
  )
}
