// Yükleme iskeleti: yeni Control Strip hero şekline benzer (gauge + 3 kanal + alt şerit),
// ardından grafik kartları. Layout-shift'i azaltır (jenerik spinner değil — taste ilkesi).
// cards: altta gösterilecek grafik-kartı sayısı.
interface Props {
  cards?: number
  label?: string
}

export default function GridSkeleton({ cards = 4, label = 'Yükleniyor' }: Props) {
  return (
    <main className="grid" aria-busy="true" aria-label={label}>
      <section className="shell fhero">
        <div className="core">
          <div className="cstrip">
            <div className="cs-gauge">
              <span className="sk-ph sk-sm" />
              <span className="sk-ph sk-gauge" />
              <span className="sk-ph sk-sm" style={{ width: 130 }} />
            </div>
            <div className="cs-cascade">
              <div className="sk-hero-ch">
                {Array.from({ length: 3 }).map((_, i) => (
                  <div className="ctile" key={i}>
                    <span className="sk-ph sk-sm" />
                    <span className="sk-ph sk-lg" style={{ margin: '10px 0' }} />
                    <span className="sk-ph" style={{ height: 8, width: '100%' }} />
                  </div>
                ))}
              </div>
              <div className="cs-cost">
                <span className="sk-ph" style={{ width: 160, height: 22 }} />
              </div>
            </div>
          </div>
        </div>
      </section>
      {Array.from({ length: cards }).map((_, i) => (
        <section className="shell" key={i}>
          <div className="core">
            <span className="sk-ph sk-eyebrow" />
            <div className="sk-ph sk-chart" />
          </div>
        </section>
      ))}
    </main>
  )
}
