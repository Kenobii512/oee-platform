// SSE snapshot hedefine (to damgası) lineer yaklaşan sanal saat. Hedefler ~tickMs
// arayla gelir (200/speed ms); saat iki hedef arasında rAF ile akar → şerit 60fps,
// SSE şeması değişmez. rAF yalnız bu hook'u kullanan bileşeni yeniden çizer.
import { useEffect, useRef, useState } from 'react'

/** prev'den target'a, tickMs içinde lineer; elapsed kıskaçlı. Saf — testli. */
export const interpolate = (
  prev: number,
  target: number,
  elapsedMs: number,
  tickMs: number,
): number =>
  prev + (target - prev) * (tickMs > 0 ? Math.max(0, Math.min(1, elapsedMs / tickMs)) : 1)

export function useVirtualClock(targetMs: number | null, tickMs: number): number | null {
  const [clock, setClock] = useState<number | null>(null)
  const ref = useRef<{ prev: number; target: number; setAt: number } | null>(null)

  // Yeni hedef: mevcut saat konumundan yeni hedefe akmaya başla (sıçrama yok).
  useEffect(() => {
    if (targetMs == null) {
      ref.current = null
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setClock(null)
      return
    }
    const now = performance.now()
    const cur = ref.current
    const from = cur ? interpolate(cur.prev, cur.target, now - cur.setAt, tickMs) : targetMs
    ref.current = { prev: from, target: targetMs, setAt: now }
    setClock(from)
  }, [targetMs, tickMs])

  // rAF döngüsü: hedef varken her karede saat ilerler; unmount'ta temizlenir.
  const active = targetMs != null
  useEffect(() => {
    if (!active) return
    let raf = 0
    const loop = () => {
      const s = ref.current
      if (s) setClock(interpolate(s.prev, s.target, performance.now() - s.setAt, tickMs))
      raf = requestAnimationFrame(loop)
    }
    raf = requestAnimationFrame(loop)
    return () => cancelAnimationFrame(raf)
  }, [active, tickMs])

  return clock
}
