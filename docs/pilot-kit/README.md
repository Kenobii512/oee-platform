# Pilot Kiti — İndeks

## Pilot 3 Cümlede

Bu kit, bir kaplama hattında yaklaşık 2 haftalık OEE pilot sürecini yürütmek için gereken tüm belgeleri bir araya getirir. Süreç üç aşamadan oluşur: tesisin verisini platforma bağla, pano üzerinden kayıp kategorilerini ve TL karşılıklarını gör, ardından başarı kriterleri değerlendirmesine dayalı bir ilerleme kararı al. Pilot sonunda hangi kaybın ne kadar para yaktığını sayısal olarak belgeleyen, karar vericiye somut bir veri sunabilen bir ekip elde edilir.

---

## Hangi Dosyayı Kim Okur

| Dosya | İçerik | Hedef Kitle |
|-------|--------|-------------|
| [01-deger-onermesi.md](01-deger-onermesi.md) | Platform değer önermesi, güven mimarisi, pilot kazanımları | Karar verici (vardiya amiri, üretim müdürü) |
| [02-demo-senaryosu.md](02-demo-senaryosu.md) | 6 demo senaryosu ile rehberli walk-through | Demo veren / satış ekibi |
| [03-veri-onboarding.md](03-veri-onboarding.md) | CSV sözleşmesi, adaptör profili, ingest API, hat tanımı | Saha teknik sorumlusu (PLC/SCADA/MES / IT) |
| [04-pilot-runbook.md](04-pilot-runbook.md) | 2 haftalık oyun kitabı (Faz 0–3, GO/NO-GO kapısı, roller) | Tedarikçi ekibi + müşteri ekibi |
| [05-basari-kriterleri.md](05-basari-kriterleri.md) | 3 ölçülebilir başarı kriteri ve değerlendirme şablonu | Tedarikçi ekibi + müşteri ekibi |

---

## Nasıl Kullanılır

### (a) Satış Görüşmesi / Demo

1. **[01-deger-onermesi.md](01-deger-onermesi.md)** — karar vericiye problem + çözüm + güven mimarisini anlat.
2. **[02-demo-senaryosu.md](02-demo-senaryosu.md)** — 6 senaryodan birini seç, rehberli walk-through yap.

### (b) Gerçek Kurulum / Saha Pilotu

1. **[03-veri-onboarding.md](03-veri-onboarding.md)** — tesisin ham verisini platforma bağla (adaptör profili, ingest, hat tanımı).
2. **[04-pilot-runbook.md](04-pilot-runbook.md)** — kickoff → smoke testi → 2 hafta veri toplama → gözden geçirme toplantısı.
3. **[05-basari-kriterleri.md](05-basari-kriterleri.md)** — toplantıda 3 kriteri değerlendir, GO / İyileştir / Durdur kararını kayıt altına al.

---

## Alt-Projeler Notu

Bu, **Alt Proje A — Doküman Paketi**'dir (`docs/pilot-kit/`, 6 dosya).

Yakında gelecekler:

- **B — Pilot Doctor CLI:** Faz 0–1 kontrollerini (hat doğrulama, smoke ingest, H3 skoru, red oranı) otomatik çalıştıran komut satırı aracı.
- **C — Showcase:** Pilot sonu rapor artefaktını (tablo, grafik, TL özeti) üretecek şablon/araç.
