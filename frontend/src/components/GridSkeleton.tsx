// Yükleme iskeleti: pano/replay ızgarasının ve kart şekillerinin shimmer karşılığı
// (jenerik spinner değil — taste ilkesi). İlk veri yüklenirken gösterilir.
// kpis: KPI şeridindeki sütun sayısı, cards: altta gösterilecek grafik-kartı sayısı.
interface Props {
  kpis?: number
  cards?: number
  label?: string
}

export default function GridSkeleton({ kpis = 5, cards = 4, label = 'Yükleniyor' }: Props) {
  return (
    <main className="grid" aria-busy="true" aria-label={label}>
      <section className="shell kpis">
        <div className="core sk-kpis">
          {Array.from({ length: kpis }).map((_, i) => (
            <div className="sk-kpi" key={i}>
              <span className="sk-ph sk-sm" />
              <span className="sk-ph sk-lg" />
            </div>
          ))}
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
