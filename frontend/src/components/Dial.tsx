// Paylaşılan OEE gauge kadranı (yarım daire yay + HEDEF 85 tiki + mavi dolum + okuma).
// Pure: verilen 0–1 değeri çizer. Pano (GaugeHero) count-up değeri geçer; Replay `live`
// ile anlık değeri geçer (CSS geçişiyle yay sinematik kayar).
import { num1, pct } from '../styles/theme'

export const ARC = Math.PI * 84 // yarım daire yay uzunluğu (r=84)
export const TARGET = 0.85 // OEE hedefi

// Yay üzerinde HEDEF (85%) noktasının radyal tiki: θ = π(1−f), merkez (100,110).
const tθ = Math.PI * (1 - TARGET)
const TICK = {
  x1: 100 + 76 * Math.cos(tθ),
  y1: 110 - 76 * Math.sin(tθ),
  x2: 100 + 94 * Math.cos(tθ),
  y2: 110 - 94 * Math.sin(tθ),
}

export default function Dial({ value, live }: { value: number; live?: boolean }) {
  const v = Math.max(0, Math.min(1, value))
  const offset = ARC * (1 - v)
  return (
    <div className={`dial${live ? ' live' : ''}`}>
      <svg width="200" height="118" viewBox="0 0 200 118" role="img" aria-label={`OEE ${pct(value)}`}>
        <path d="M16 110 A84 84 0 0 1 184 110" fill="none" stroke="#e7ebf0" strokeWidth="16" strokeLinecap="round" />
        <path d="M16 110 A84 84 0 0 1 184 110" fill="none" stroke="url(#gz)" strokeWidth="4" strokeLinecap="round" opacity="0.7" />
        <path
          d="M16 110 A84 84 0 0 1 184 110"
          fill="none"
          stroke="#1f5da6"
          strokeWidth="16"
          strokeLinecap="round"
          strokeDasharray={ARC}
          strokeDashoffset={offset}
        />
        {/* HEDEF 85 tiki */}
        <line x1={TICK.x1} y1={TICK.y1} x2={TICK.x2} y2={TICK.y2} stroke="#16202b" strokeWidth="2" />
        <defs>
          <linearGradient id="gz" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0" stopColor="#a8443a" />
            <stop offset="0.5" stopColor="#b5832f" />
            <stop offset="1" stopColor="#237a5c" />
          </linearGradient>
        </defs>
      </svg>
      <div className="read">
        <span className="n">{num1(v * 100)}</span>
        <span className="u">% OEE</span>
      </div>
    </div>
  )
}
