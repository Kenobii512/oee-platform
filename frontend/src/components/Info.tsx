// Erişilebilir küçük bilgi işareti: teknik/varsayım detayını native tooltip ile gösterir
// (kullanıcı yüzünde jargon yerine sade metin; detay ⓘ üstünde). Klavye erişilebilir.
export default function Info({ text }: { text: string }) {
  return (
    <span className="info" tabIndex={0} role="img" aria-label={text} title={text}>
      ⓘ
    </span>
  )
}
