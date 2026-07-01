# Pilot Kiti — Alt-proje C: Showcase (Tasarım/Spec)

**Tarih:** 2026-07-02 · **Durum:** onaylandı, plana hazır

## Context

Pilot Kiti A (doküman paketi) ve B (pilot doctor CLI) main'de. A→C devir sözleşmesi
(`2026-06-30-pilot-kiti-A-dokuman-paketi-design.md` "Alt-proje sınırları"): **Faz 3
"pilot raporu" tanımı, C'nin üreteceği örnek rapor artefaktının içeriğini belirler** —
OEE + en büyük kayıplar + TL fırsatı + güven notu. README vaadi: "tablo, grafik, TL
özeti üretecek şablon/araç". Spec A ayrıca C'yi "örnek pilot raporu **+ landing**"
diye anar; landing bu spec'te somutlanır.

## Goal

Üç teslim:
1. **Rapor aracı** `backend/tools/pilot_report.py` — pilot verisinden tek dosyalık,
   kendine-yeten HTML pilot raporu üretir (Faz 3 toplantısının artefaktı).
2. **Örnek showcase raporu** — aynı araçla `breakdown_storm` senaryo fixture'ından
   üretilip `docs/showcase/ornek-pilot-raporu.html` olarak commit'lenir (satış eseri).
3. **Landing** — `docs/showcase/landing.html` (tek sayfa tanıtım, Foundry Gauge light
   kimliği) + FastAPI **`GET /tanitim`** public rotası.

## Sabit kararlar (brainstorming çıktısı)

- **Girdi = veri dizini, doctor deseni:** in-process + geçici DuckDB;
  `python -m tools.pilot_report <veri-dizini> [--adapter <profil>] [--line PATH]
  [--from --to] [-o rapor.html]`. Sunucu gerekmez. **HTTP modu (canlı sunucudan
  çekme) İLERİDE** — gerçek ihtiyaç doğunca ayrı iş.
- **Format = tek dosya HTML + satır içi SVG:** gömülü CSS, harici bağımlılık/istek
  YOK; e-postalanabilir; tarayıcıdan yazdır → PDF (spec A'nın PDF-erteleme kararına
  uygun — PDF kütüphanesi yok).
- **Doctor'dan farkı:** doctor *karar verir* (exit 0/1), report *belgeler* — her
  zaman rapor üretir; eşik ihlallerini ✗ ile gösterir, exit'i düşürmez.
- **Landing kapsamı = tek sayfa öz:** 01-deger-onermesi.md'nin görselleştirilmişi;
  ekran görüntüsü YOK (UI değişince bayatlar) — SVG mini-görseller.
- **Landing yaşam yeri:** statik dosya commit'li **VE** `/tanitim` public rotası
  (auth istisnası, `/health` gibi) — Render deploy'unda paylaşılabilir URL.

## Rapor içeriği (Faz 3 sözleşmesi, sırayla)

1. **Künye:** hat adı, rapor penceresi (from–to ya da verinin span'i), üretilme
   zamanı, veri kapsamı (event sayısı, span_min, H3 yeterlilik skoru, red oranı).
2. **OEE bloğu:** A / P / Q(ilk-geçiş) / OEE + utilization + final_yield
   (`compute_oee`; H8 calendar varsa utilization takvim-doğru).
3. **En büyük kayıplar (TL Pareto):** SVG yatay çubuklar TL azalan; her kalemde
   `tl_low–tl_high` aralığı, **görünür/çıkarımsal** rozetleri, düşük-güven işareti
   (`to_tl` çıktısı birebir).
4. **TL fırsatı (öneriler):** tablo — başlık/aksiyon/varsayım + kazanç aralığı
   `low–high`; toplam satırı "üst sınır; kalemler örtüşebilir" çekincesiyle
   (`generate_recommendations`).
5. **Trend:** günlük/haftalık OEE çizgisi SVG (`bucket_oee_series`; <3 nokta →
   "yeterli geçmiş yok" notu, pano ile aynı dil).
6. **Güven notu:** H3 yeterlilik + red oranı + görünür/çıkarımsal ayrımı;
   01-deger-onermesi'nin "abartı yok" dili birebir.
7. **3 başarı kriteri tablosu** (05-basari-kriterleri şablonuyla birebir):
   - **Otomatik doldurulur:** K1 = en TL'li `kind=="inferred"` kalem Pareto üst
     ⅓'te mi + TL ≥ toplamın %15'i; K2 = `total_estimated_gain_tl > 0` + ≥1 öğede
     low/high dolu (`low > 0`); K3 = red oranı ≤ %5 + H3 ≥ 0.6 + güven bandı dolu.
   - **Elle doldurulur (boş bırakılır):** K1 "ekip takip etmiyorduk" onayı, K3
     "<2 sn" saha gözlemi, genel karar ☐ GO ☐ İyileştir ☐ Durdur + gerekçe,
     pilot süresi/değerlendiren. Rapor bu alanları görünür biçimde boş basar.

## Landing içeriği (tek sayfa, Türkçe)

Problem (Excel/manuel takip; kayıplar görünmez) → çözüm tek-bakış tablosu (OEE% ·
en büyük kayıp · TL karşılığı · öneri) → güven mimarisi (görünür/çıkarımsal ayrımı,
güven bandı, "abartı yok" anti-iddiaları) → örnek rapora link
(`ornek-pilot-raporu.html`) → pilot CTA (2 haftalık akış: kickoff → smoke →
toplama → rapor). Görsel dil: **Foundry Gauge light** (üst dizindeki `DESIGN.md`
token'ları — renk/tipografi/Control Strip estetiği — landing dosyasına gömülür;
landing kendine yeten kalır).

## Mimari

- **Katmanlama:** `tools/pilot_report.py` yalnız `app.config`, `app.config_validate`,
  `app.ingest.*`, `app.store.duckdb_repo`, `app.analytics.*` import eder — ASLA
  `app.api`/`app.main`. pilot_doctor ile aynı kurallar (ASCII konsol; HTML içeriği
  UTF-8 — dosyaya yazılır, konsola basılmaz).
- **İki katman:** (1) `build_report_data(...) -> dict` — saf veri boru hattı
  (ingest→OEE→kayıp/TL→öneri→trend→yeterlilik→kriter değerlendirme), HTML bilmez;
  (2) `render_html(data) -> str` — SVG üreteçleri + şablon, veri kaynağını bilmez.
  JSON çıktısı istenirse `build_report_data` dict'i hazır (bugün bayrak yok — YAGNI).
- **Ortak altyapı yeniden kullanımı:** temp-DuckDB + adaptör akışı pilot_doctor'ın
  birebir deseni (`resolve_profile_path`, `adapt_dir_to_contract`,
  `line_definition_from_dict`); metrik fonksiyonları yeniden uygulanMAZ.
- **`/tanitim`:** `docs/showcase/landing.html`'i `FileResponse` ile sunar; auth
  middleware istisna listesine eklenir (`/health` deseni). Dosya yoksa 404.
- **Determinizm:** örnek rapor seed-42 fixture'ından üretilir; üretilme zamanı
  gömülü olacağı için örnek raporda sabit görünmez alan kalmamalı — künyede zaman
  `--generated-at` bayrağıyla ezilebilir (örnek üretiminde sabit verilir; testte
  determinism böyle doğrulanır).

## Kapsam dışı (YAGNI)

- HTTP/canlı-sunucu veri modu (`--url`) — ileride, ihtiyaç doğunca.
- PDF kütüphanesi / ekran görüntüsü otomasyonu / harici grafik kütüphanesi.
- Çok dilli içerik (yalnız Türkçe), çok-hatlı rapor, e-posta gönderimi.
- Landing için ayrı JS/framework — düz HTML+CSS(+minimal SVG).

## Doğrulama

1. Golden e2e: `breakdown_storm` → HTML'de beklenen OEE değeri, en büyük kayıp
   kalemi (DOWNTIME), TL aralıkları, K1/K2/K3 otomatik işaretleri.
2. Kendine-yeterlik: üretilen HTML'de `http://`/`https://` kaynak referansı YOK
   (link hariç `src=`/`href=` stylesheet'i yok); tek dosya.
3. Kenarlar: boş/eksik veri → rapor yine üretilir, ilgili bölümlerde "veri yok"
   notu (çökme yok); kirli veri → red oranı ve K3 ✗ görünür.
4. Determinism: aynı fixture + sabit `--generated-at` → bayt-eş HTML.
5. `/tanitim`: 200 + `text/html`; `OEE_AUTH_PASS` tanımlıyken de public.
6. Örnek rapor + landing tarayıcıda elle/Playwright ile gözden geçirilir.

## Sırada

Spec onaylanınca → uygulama planı
(`docs/superpowers/plans/2026-07-02-pilot-kiti-C-showcase.md`). C ile Pilot Kiti
(A+B+C) tamamlanır; sonrası pilot sahası / Render deploy / what-if.
