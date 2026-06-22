// Paylaşılan OEE gauge kadranı: yarım daire yay + ölçek graduasyonu + HEDEF 85 tiki +
// mavi dolum + anlık-değer ibresi (rim pointer) + merkez okuma.
// Pure: 0–1 değeri çizer. Pano (GaugeHero) count-up değeri geçer; Replay `live` ile anlık
// değeri geçer → yay + ibre CSS geçişiyle sinematik kayar. Merkez sayıyla çakışma yok
// (ibre rim'de, graduasyon iç-rim'de; ikisi de büyük sayının dışında).
import { num1, pct } from '../styles/theme'

export const ARC = Math.PI * 84 // yarım daire yay uzunluğu (r=84)
export const TARGET = 0.85 // OEE hedefi

const CX = 100
const CY = 110

// Yay üzerinde HEDEF (85%) noktasının radyal tiki: θ = π(1−f).
const tθ = Math.PI * (1 - TARGET)
const TICK = {
  x1: CX + 76 * Math.cos(tθ),
  y1: CY - 76 * Math.sin(tθ),
  x2: CX + 94 * Math.cos(tθ),
  y2: CY - 94 * Math.sin(tθ),
}

// Ölçek graduasyonu: her %10'da bir iç-rim tiki (0/50/100 daha uzun) → enstrüman kadranı hissi.
const GRADS = Array.from({ length: 11 }, (_, i) => {
  const a = Math.PI * (1 - i / 10)
  const major = i % 5 === 0
  const r1 = major ? 61 : 65
  return {
    x1: CX + r1 * Math.cos(a),
    y1: CY - r1 * Math.sin(a),
    x2: CX + 72 * Math.cos(a),
    y2: CY - 72 * Math.sin(a),
    major,
  }
})

export default function Dial({ value, live }: { value: number; live?: boolean }) {
  const v = Math.max(0, Math.min(1, value))
  const offset = ARC * (1 - v)
  // Rim ibresi: değere göre döner. Taban (+x) yön, (100,110) etrafında deg = 180(v−1).
  const needleDeg = 180 * (v - 1)
  return (
    <div className={`dial${live ? ' live' : ''}`}>
      <svg width="200" height="118" viewBox="0 0 200 118" role="img" aria-label={`OEE ${pct(value)}`}>
        {/* yatak */}
        <path d="M16 110 A84 84 0 0 1 184 110" fill="none" stroke="#e7ebf0" strokeWidth="16" strokeLinecap="round" />
        {/* kırmızı→amber→yeşil hedef bandı (ince) */}
        <path d="M16 110 A84 84 0 0 1 184 110" fill="none" stroke="url(#gz)" strokeWidth="4" strokeLinecap="round" opacity="0.7" />
        {/* mavi dolum */}
        <path
          d="M16 110 A84 84 0 0 1 184 110"
          fill="none"
          stroke="#1f5da6"
          strokeWidth="16"
          strokeLinecap="round"
          strokeDasharray={ARC}
          strokeDashoffset={offset}
        />
        {/* ölçek graduasyonu (statik) */}
        {GRADS.map((g, i) => (
          <line
            key={i}
            x1={g.x1}
            y1={g.y1}
            x2={g.x2}
            y2={g.y2}
            stroke={g.major ? '#a9b2bd' : '#cdd4dc'}
            strokeWidth={g.major ? 1.5 : 1}
            strokeLinecap="round"
          />
        ))}
        {/* HEDEF 85 tiki */}
        <line x1={TICK.x1} y1={TICK.y1} x2={TICK.x2} y2={TICK.y2} stroke="#16202b" strokeWidth="2" />
        {/* anlık-değer ibresi (rim pointer) — live'da yumuşak döner */}
        <g
          className="needle"
          style={{ transform: `rotate(${needleDeg}deg)`, transformBox: 'view-box', transformOrigin: '100px 110px' }}
        >
          <line x1="162" y1="110" x2="192" y2="110" stroke="#16202b" strokeWidth="3.5" strokeLinecap="round" />
        </g>
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
