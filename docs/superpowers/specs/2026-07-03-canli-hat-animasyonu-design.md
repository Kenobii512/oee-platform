# Canlı Hat Animasyonu (Tasarım/Spec)

**Tarih:** 2026-07-03 · **Durum:** onaylandı (portföy yol haritası ④; sim planı v2'nin
"satışın ana aracı" dediği, sessizce düşmüş özellik). Kararlar: **yalnız Replay
görünümünde** + **B varyantı: tam akış** (askılar hareket eder). Kullanıcı vurgusu:
**görsel olarak gerçekten güzel olacak** — aşağıda ayrı çıta bölümü var.

## Context

Replay (G7) SSE ile 60 kesitlik agregat snapshot yayınlar (`/replay/stream`;
`Replay.tsx` EventSource, hız 1/2/5). Snapshot'lar istasyon/olay detayı taşımaz.
Olay verisi animasyon için gereken her şeyi zaten içerir: `LOAD → MOVE(HOIST) →
PROCESS(tank) → … → QC → UNLOAD` askı güzergâhı; `STRIP` = redo (söküm + yeniden
kaplama, askı geri döner); `DOWNTIME` istasyon bazlı + `reason_code` (carrier boş);
`MICROSTOP`, `OVER_RESIDENCE` (tankta bekleme). Hat tanımı `config/line_default.yaml`:
7 sıralı tank (kapasite 1) + tek vinç (move 0,5 dk). Baseline ~1.580 olay → tek
seferde frontend'e vermek ucuz. Eş-zamanlı aktif askı ≤ ~9.

## Goal

Replay görünümüne, SSE sanal saatine senkron **canlı hat şeridi**: tanklar banyo
kabı olarak, askılar carrier numaralı çipler olarak tanklarda oturur, vinç rayında
taşınır; duruşta tank/vinç kırmızı (neden etiketli), redo'da askı kesikli yayla
geri döner. İzleyen kişi hattı "çalışırken" görür — satış demosunun ana sahnesi.

## Sabit kararlar

### Veri beslemesi: yeni hafif uç (SSE'ye dokunulmaz)
- **`GET /replay/timeline?scenario=`** → tek JSON:
  `{"line": [{"id","name"}…] (YAML sırasında), "events": [{"timestamp","carrier_id",
  "station_id","event_type","duration","reason_code"}…] (zaman sıralı)}`.
- İş kuralı YOK: ham döküm. `/replay/stream` ile aynı senaryo çözümü ve izolasyon
  (paylaşılan repo'yu değiştirmez, ground_truth ALMAZ — FIREWALL korunur).
- Hat tanımı uçtan gelir; tank adları/sırası frontend'e GÖMÜLMEZ ("yeni hat = yeni
  YAML; kod değişmez" ilkesi).
- SSE snapshot şeması DEĞİŞMEZ.

### Frontend durum-indirgeyici: `frontend/src/replay/replayLine.ts` (saf, UI'sız)
- Olaylar bir kez askıya/istasyona indekslenir; `lineStateAt(t)` sanal an t için döndürür:
  - `carriers[]`: `{tankta: station}` | `{tasiniyor: from→to, progress 0–1}` (MOVE
    penceresi; from/to aynı askının komşu olaylarından) | `{bekliyor: station}`
    (PROCESS bitti vinç gelmedi / OVER_RESIDENCE) | `{cikti}`. STRIP sonrası askı
    `redo: true` işaretli ve hedefe GERİ hareket eder.
  - `tanks[]`: durum — öncelik **DOWNTIME > MICROSTOP > OVER_RESIDENCE(bekliyor) >
    PROCESS(işliyor) > boş**; duruşta `reason_code`. Tank duruşu askıdan bağımsız
    (DOWNTIME satırlarında carrier boş).
  - `hoist`: `{tasiyor?: carrier, progress}` | `{durus: reason}` | boş. HOIST
    duruşunda vinç kırmızı, tüm çipler oldukları yerde donar.
  - Sayaçlar (kümülatif, t'ye kadar): yüklenen (LOAD), çıkan (UNLOAD), redo (STRIP).
- t pencere dışıysa (ilk olaydan önce / son olaydan sonra) uç durumlar boş/final döner.

### Sanal saat senkronu
- Her SSE snapshot'ı geldiğinde saat hedefi = `snapshot.to`; aradaki gerçek sürede
  saat hedefe **lineer** akar (hız değişimi otomatik uyum). Replay durunca şerit
  son anda donar; EventSource düşerse şerit gri "beklemede" durumuna geçer.
- rAF döngüsü yalnız Replay görünümü aktifken çalışır (unmount'ta temizlenir).

### Görsel: `frontend/src/components/LineStrip.tsx` (SVG, tam genişlik)
- Replay kontrol barının hemen altında; Foundry Gauge dili (DESIGN.md token'ları):
  keskin köşe, hairline (`--line`), tabular-nums, GLOW YOK.
- Tanklar banyo kabı silüeti (kap + sıvı dolgu imâsı, `--surface-inset`/`--steel`);
  eyebrow tipografisiyle tank adı; kapasite 1 → kapta tek çip oturur.
- Üstte vinç rayı; MOVE sırasında troley + asılı çip rayda süzülür (progress'e göre).
- Çip = carrier no'lu küçük kare (tabular mono, ör. "0042"); redo çipi kesikli
  yayla geriye taşınır ve dönüş boyunca `quality-loss` (#a8443a) vurgulu.
- Duruş: tank/vinç kırmızı dolgu + `reason_code` etiketi. Mikro-duruş: kısa flaş.
  Bekleyen: `threshold-amber` kenar. Duruş etiketleri ham kod değil Türkçe
  (`hoist_ariza` → "Vinç arızası" — eşleme `theme.ts` CATEGORY_LABEL desenine uygun
  yeni REASON_LABEL sözlüğü; bilinmeyen kodda ham koda düşer).
- Uç kapaklar: solda "Yükleme →" (çip belirir), sağda "→ QC / Çıkış" (çip QC'de
  kısa durur, söner). Sağ blok: sanal saat (rozet) + sayaçlar (Yüklenen/Çıkan/Redo).
- Hareket dili: CSS transition/rAF karışımı — çip konumları rAF ile (sanal saat
  sürüklü), durum renkleri kısa CSS geçişiyle (~150ms); yaylanma/bounce YOK
  (endüstriyel ciddiyet).

### Görsel kalite çıtası (kullanıcı vurgusu)
- İlk implementasyondan sonra **ayrı bir görsel cila turu zorunlu**: Playwright
  ekran görüntüleriyle (oynarken en az 3 an: normal akış, duruş anı, redo dönüşü)
  hiza/boşluk/renk denetimi; önceki redesign turlarındaki gibi ekran görüntüsü
  üzerinden düzeltme döngüsü.
- Kabul ölçütleri: şerit 1280px'te tek satırda okunur; tank adları kısaltılmadan
  sığar; çip hareketi 60fps'te akıcı (baseline veri); duruş kırmızısı ile kalite
  mercanı ayırt edilir; mobilde (≤768px) şerit yatay kaydırmalı, sayfa gövdesi taşmaz.
- Demo GIF güncellemesi bu spec'in kapsamı DIŞINDA (istenirse ayrı iş).

## Kapsam dışı (YAGNI)

- Pano/landing'de animasyon yok (yalnız Replay).
- SSE şema değişikliği yok; backend'de istasyon-durum hesabı yok.
- Çoklu hat/çoklu vinç desteği yok (YAML tek hat; kapasite>1 gelirse çipler yan
  yana dizilir — tasarım buna esner ama test edilmez).
- Zaman çubuğunda geri sarma/scrubbing yok (Replay'in mevcut akış modeli korunur).

## Testler / doğrulama

- **Backend:** `/replay/timeline` testi — alan seti, zaman sıralı olaylar, line
  YAML sırası, senaryo izolasyonu (`/replay/stream` test desenine paralel).
- **Frontend (vitest):**
  - İndirgeyici: crafted olay listesiyle PROCESS penceresi, MOVE ortasında
    progress≈0,5, durum önceliği (DOWNTIME > MICROSTOP > OVER_RESIDENCE), STRIP
    sonrası geri hareket + redo sayacı, HOIST duruşunda çip donması, pencere dışı t.
  - LineStrip: duruşta kırmızı hücre + Türkçe neden etiketi; sayaç değerleri;
    boş veri → şerit "beklemede".
  - Sanal saat: snapshot hedefine lineer yaklaşım.
- **Zincir:** `make ci` · vitest · `tsc`/eslint/`vite build`; yerel native run ile
  göz + Playwright ekran görüntüleri (cila turu girdisi).
