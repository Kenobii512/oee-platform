# Pilot Kiti — Alt-proje A: Doküman Paketi (Tasarım/Spec)

**Tarih:** 2026-06-30 · **Durum:** onaylandı, plana hazır

## Context

OEE platformu (G1–G12 + Hazırlık H1–H9) tamamlandı ve tümü simülatöre karşı doğrulandı; gerçek müşteri/saha verisi henüz yok. Hazırlık dalgalarının (kirli-veri dayanıklılığı H1, ingest adaptörü H2, belirsizlik/güven H3, demo anlatısı H6, hat-tanımı doğrulayıcı H7, deploy H9) tek amacı **pilotu önceden derisk etmekti**. Şimdi bu yetenekleri sahaya taşıyacak **pilot kiti** gerekiyor.

Pilot kiti üç bağımsız alt-projeye bölündü: **A — Doküman paketi** (bu spec), **B — Pilot doctor CLI** (veri klasörünü denetleyen araç), **C — Satış showcase** (örnek pilot raporu + landing). A önce gelir çünkü pilotun şeklini, sözleşmesini ve başarı kriterlerini tanımlar; B ve C buna dayanır.

**Hedef (esnek):** platform hem güçlü portföy/demo eseri hem ileride gerçek ticarileşme. A bu iki kullanımı tek pakette birleştirir.

## Goal

Soğuk bir prospect'i pilota ikna etmeye **ve** gerçek bir kaplama hattında ~2 haftalık pilotu sürtünmesiz kurup değerlendirmeye yetecek, mevcut H1–H9 yeteneklerini birbirine bağlayan tutarlı bir Markdown doküman demeti üretmek. Yeni ürün kodu YOK; var olan dokümanlara (deployment.md, line-definition-guide.md, sensitivity_report.md) link verir, kopyalamaz.

## Sabit kararlar (brainstorming çıktısı)

- **İki kitle, iç içe:** *karar verici* (amir/müdür) ve *saha teknik* (PLC/SCADA/IT).
- **Başarı kriterleri (3):** (1) ekibin önceden nicelleştiremediği **bilinmeyen bir kaybı ortaya çıkardı**; (2) en büyük kayıpları paraya çevirip **TL tasarruf fırsatı niceledi**; (3) sahanın dağınık verisi **uçtan uca güvenilir aktı** (H2 adaptör/H1 kirli-veri sorunsuz, pano <2sn, H3 güven katmanı şeffaf). Niteliksel "kullanırdım" kabulü kapsam dışı (objektif kanıt öncelikli).
- **Pilot şekli:** ~2 hafta, hızlı. Kickoff (1 gün) → ~2 hafta veri toplama → gözden geçirme.
- **Veri devri:** **ham export + H2 adaptör** (saha gerçeği; en az sürtünme). Müşteri PLC/SCADA/MES'ten ne çıkarabiliyorsa onu verir; adaptör profiliyle sözleşmeye çevrilir.
- **Format/yer:** `docs/pilot-kit/` altında Markdown (mevcut `docs/*.md` deseni).

## Mimari & yapı

`docs/pilot-kit/` demeti, bir indeks `README.md` ve beş içerik dosyası. Her dosya tek bir amaca hizmet eder ve diğerlerinden bağımsız okunabilir; ortak referanslar (sözleşme şeması, deploy, hat kılavuzu) link ile paylaşılır (DRY — kopyalama yok).

## Doküman envanteri

| Dosya | Kitle | Amaç / kilit içerik |
|------|-------|---------------------|
| `README.md` | her ikisi | Kit indeksi; "pilot 3 cümlede"; hangi dosyayı kim okur; nasıl kullanılır (satış görüşmesi vs kurulum). |
| `01-deger-onermesi.md` | karar verici | Problem (Excel/manuel takip; kayıplar görünmez) → çözüm (bir bakışta en büyük kayıp + TL + öneri) → neden güvenilir (H3 güven aralığı, görünür/çıkarımsal ayrımı, "abartı yok" anti-iddiaları). Tek sayfa. |
| `02-demo-senaryosu.md` | satış / portföy | Rehberli demo betiği: senaryo seç → canlı replay → en büyük kayıp → TL'li öneri. 6 senaryonun bir-cümle anlatısı (H6 `narrative`/`highlight`) + her ekranda "neye bak". Yerel/Render demo URL'i nasıl açılır. |
| `03-veri-onboarding.md` | saha teknik | Sözleşme şeması sade dille (events/production/orders ne demek, hangi kolon ne); "ham export'unu nasıl verirsin" → **H2 adaptör profili** oluşturma (`config/adapters/generic_plant.yaml` örneği, kolon/zaman/birim/reason eşleme); → **H7 hat tanımı** + `POST /line/validate`; → **H1 kirli-veri** güvencesi (eksik/bozuk satır reddedilir, sağlam yüklenir). `deployment.md` + `line-definition-guide.md`'ye link. |
| `04-pilot-runbook.md` | her ikisi | 2 haftalık akış (aşağıdaki fazlar) + go/no-go kapıları + roller (bizden / müşteriden kim) + zaman çizelgesi şablonu. |
| `05-basari-kriterleri.md` | her ikisi | 3 başarı kriterinin operasyonel tanımı + nasıl ölçülür (hangi pano/uç) + pilot-sonu değerlendirme şablonu (doldurulabilir tablo). |

## Runbook akışı (2 hafta) + go/no-go kapıları

- **Faz 0 — Hazırlık (kickoff, ~1 gün):** hattı `line_default.yaml` benzeri tanımla → `POST /line/validate` yeşil (H7); müşteriden **bir örnek ham export** al; ona uygun **adaptör profili** kur (H2); platformu deploy et (H9, Render/Docker).
- **Faz 1 — Smoke (~1–2 gün · GO/NO-GO KAPISI):** örnek veriyi `POST /ingest?adapter=<profil>` ile yükle → pano açılıyor, `/oee` makul değer, **veri-yeterlilik skoru (H3 `data_sufficiency`) eşik üstü**, kirli-satır oranı kabul edilebilir. NO-GO ise: adaptör/veri düzelt, tekrar. (Bu kapı **B — pilot doctor** ile otomatikleşecek.)
- **Faz 2 — Toplama (~2 hafta):** periyodik ingest (manuel veya zamanlanmış export); pano izlenir; trend birikir.
- **Faz 3 — Gözden geçirme (review toplantısı):** 3 başarı kriterine karşı değerlendir; çıktı = **"pilot raporu"** (OEE + en büyük kayıplar + TL fırsatı + güven notu). Bu rapor **C — showcase** alt-projesinin ürettiği şablonu kullanır.

## Alt-proje sınırları (devir noktaları)

- **A → B:** Runbook Faz 0–1 kontrol listesi, B'nin (pilot doctor CLI) otomatikleyeceği denetimlerin sözleşmesidir (hat validator + adaptör + kirli-veri raporu + yeterlilik skoru → tek "hazır mı" raporu).
- **A → C:** Faz 3 "pilot raporu" tanımı, C'nin (showcase) üreteceği örnek rapor artefaktının içeriğini belirler.
- A bu spec'te yalnız **dokümanları** üretir; B ve C'nin kodu ayrı spec/plan döngülerindedir.

## Kapsam dışı (YAGNI)

- Otomatik veri bağlantısı (canlı MQTT/OPC-UA) — gerçek pilot tetiğiyle, sonra.
- Çoklu hat / çok-kiracılık.
- B (pilot doctor CLI) ve C (showcase) kodu — ayrı alt-projeler.
- Basılı/PDF üretimi — Markdown iyi render olur; gerekirse sonra.

## Doğrulama (kit işe yarıyor mu?)

Kit, "soğuk → çalışır" yolculuğunu kapsadığında başarılıdır:
1. **İçsel tutarlılık:** her dosya var olan yetenek/dokümana doğru link verir; ölü link yok; sözleşme şeması backend `app/models/contract.py` ile tutarlı.
2. **Uçtan uca izlenebilirlik:** `03-veri-onboarding.md`'deki adımlar gerçekten `tests/fixtures/raw/` örneği + `generic_plant.yaml` ile çalışır (H2 e2e testiyle aynı yol); runbook Faz 1 kapısı gerçek uçlara (`/ingest`, `/oee`, H3 yeterlilik) bağlanır.
3. **Kitle testi:** karar verici dosyaları teknik jargon olmadan okunur; teknik dosyalar kolon/komut düzeyinde somut.

## Sırada

A spec'i onaylanınca → `writing-plans` ile uygulama planı (Markdown dosyalarını TDD-dışı ama bölüm-bölüm, her dosya bir teslim). Sonra B ve C kendi brainstorming→spec→plan döngülerinde.
