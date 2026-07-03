# Vardiya Künyesi Kartı (Tasarım/Spec)

**Tarih:** 2026-07-03 · **Durum:** onaylandı (PR #4'ün yeniden doğuşu; içerik: "yalın" varyant onaylı)

## Context

PR #4 (22 Haziran, "hesaplanan bağlam metriklerini yüzeye çıkar") bayat kaldı: main
79 commit ilerledi (Foundry Gauge redesign, H8 `calendar_min`, G12 kalite semantiği).
Tier 1 (utilization + planlı duruş) main'de zaten yüzeye çıktı ("Takvim kullanımı",
hero'da "· N redo" notu). Kalan tek boşluk: **parça sayıları ve gözlem penceresi**
hâlâ `/oee` yanıtında yok ve panoda görünmüyor. PR #4 kapatıldı; bu spec aynı fikri
güncel koda uygun, yalın biçimde yeniden tanımlar.

## Goal

Pano **Detay** görünümüne "Vardiya Künyesi" kartı: vardiyanın kimlik bilgisi —
gözlem penceresi süresi + Yüklenen / İyi (ilk geçiş) / Redo parça sayıları.
Tek doğruluk kaynağı `/oee` yanıtıdır; frontend formül çoğaltmaz (ilk-geçiş farkı hariç, aşağıda).

## Sabit kararlar

- **İçerik "yalın" varyant (onaylı):** Gözlem penceresi + 3 parça satırı.
  Kullanım oranı karta KONMAZ (hero'da "Takvim kullanımı" zaten var; tekrar yok).
  Planlı/plansız duruş dökümü de KONMAZ (kayıp ağacı dakika ekseni bunu zaten anlatıyor).
- **Backend:** `OeeResult`'a default'lu 4 alan: `loaded_qty: float = 0.0`,
  `good_count: float = 0.0`, `redo_count: float = 0.0`, `span_min: float = 0.0`.
  `compute_oee` zaten hesapladığı toplamları (`loaded`, `good`, `redo`) ve
  `_availability`'den gelen `span_min`'i geçirir. `/oee` `asdict` ile otomatik döndürür.
  Trend/Replay kendi dict'lerini kurduğundan **etkilenmez**.
- **"İyi (ilk geçiş)" = `loaded_qty − redo_count`** (frontend'te hesaplanır; G12:
  Q = first_pass = (loaded−redo)/loaded ile aynı pay). `good_count` (nihai iyi)
  kartta GÖSTERİLMEZ — no-scrap dünyasında ≈ yüklenen olduğundan kafa karıştırır;
  yine de yanıtta bulunur (şeffaflık/ileri kullanım).
- **Görünürlük kuralı:** alanlar yoksa (eski yanıt) veya `loaded_qty <= 0` ise kart
  hiç render edilmez (null döner). Özet görünümünde hiç görünmez; yalnız Detay.
- **Yerleşim:** Durum bölgesi, TrendChart'tan sonra (`{detay && ...}`).
- **Biçim:** Foundry Gauge dili — eyebrow başlık ("Vardiya Künyesi"), hairline
  ayırıcı satırlar, sağa yaslı tabular-nums değerler. Süre biçimi: ≥90 dk ise
  "X s YY dk", altında "N dk". Parça sayıları `Intl.NumberFormat('tr-TR')` tam sayı.

## Kapsam dışı (YAGNI)

- Ayrı `GET /shift-summary` ucu yok.
- Kullanım/duruş dökümü satırları yok (yukarıdaki gerekçeler).
- `downtime_union_min` yanıta EKLENMEZ (yalın içerik kullanmıyor; ihtiyaç olursa
  ayrı iş).

## Testler / doğrulama

- **Backend:** `test_oee_endpoint` yeni 4 alanı doğrular + tutarlılık:
  `quality ≈ (loaded_qty − redo_count) / loaded_qty` (loaded>0 iken).
- **Frontend (vitest):** (1) kart verili durumda render olur, ilk-geçiş =
  loaded−redo doğru; (2) `loaded_qty` yok/0 iken render olmaz; (3) süre biçimi
  (480 → "8 s 00 dk").
- **Zincir:** `tsc -b` · eslint · vitest · `vite build` + `make frontend-sync`;
  backend pytest tam süit; Docker uçtan uca göz kontrolü (Özet'te yok, Detay'da var).
