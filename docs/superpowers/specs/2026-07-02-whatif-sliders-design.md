# What-if Slider'ları (Tasarım/Spec)

**Tarih:** 2026-07-02 · **Durum:** onaylandı (portföy yol haritası ③; fikir turu A2)

## Context

Pilot kiti kapandı; portföy/satış güçlendirme sırasının 3. adımı. Satış demosunun
kapanış anı: alıcı "duruşu %30 azaltsam ne olur?" sorusunun cevabını **kendi eliyle
kaydırarak** görür. `GainEstimator` arayüzü (G9) ve TL bantları (H3) hazır kanca.

## Goal

Pano Detay görünümüne **What-if** bölümü: 5 kayıp kategorisi için azaltım slider'ları
(0–%50) → OEE bileşenlerinin (A/P/Q) ve TL kazancının **canlı** önce→sonra karşılaştırması.

## Sabit kararlar

- **Hesap backend'te** (`GET /whatif`): "tek doğruluk kaynağı — metrik mantığı
  platformda" ilkesi. Frontend yalnız slider + görselleştirme; formül çoğaltılmaz.
- **Analitik yaklaşım** (simülatör koşulmaz; şeffaf formüller):
  - `A' = clamp((span − union')/span)`, `union' = clamp(union − DT·p_dt − MS·p_ms, 0, union)`
  - `P' = clamp(ideal / max(ideal, actual − SPEED·p_speed))` (actual = Σ PROCESS)
  - `Q' = clamp((loaded − redo·(1−p_redo)) / loaded)`
  - `OEE' = A'·P'·Q'`; FILL yalnız TL kazancına katkı (G12: fill Q'da değil)
  - TL kazanç: kategori başına `tl·p` + bant `tl_low·p – tl_high·p` (H3 bantları)
- **Dürüstlük dili panoyla aynı:** "yaklaşık; kalemler bağımsız kabul edilir,
  örtüşebilir; üst sınır" çekincesi görünür.
- **"Önerilen değerler" butonu:** slider'ları `config/recommend.yaml` geri-kazanım
  oranlarına (DOWNTIME 0.30, MICROSTOP 0.20, ...) getirir — öneri motoru ile
  what-if aynı varsayımı paylaşır (tutarlılık).
- Azaltımlar 0–1 aralığında doğrulanır (aksi 400); UI 0–%50 sunar.

## API

```
GET /whatif?downtime=0.3&microstop=0&speed_loss=0&quality_redo=0&fill_loss=0[&from&to]
-> {
  "baseline": {availability, performance, quality, oee},
  "adjusted": {availability, performance, quality, oee},
  "gain": {total_tl, total_tl_low, total_tl_high,
           per_category: [{category, reduction, gain_tl, gain_tl_low, gain_tl_high, kind}]}
}
```

Boş veri → tüm değerler 0 (çökme yok). Firewall/katmanlama aynen (ground_truth yok).

## Kapsam dışı (YAGNI)

Simülatör koşarak what-if (gerçek pilot verisi tetikleyicisi — bu analitik sürüm
onun zeminini bozmaz); senaryolar arası karşılaştırma (B2, ayrı iş); slider durumunun
URL'de paylaşımı.

## Doğrulama

Sıfır azaltım = baseline birebir; tek kategori azaltımı yalnız ilgili bileşeni
oynatır; %100 duruş azaltımı A'yı yükseltir ama 1'i aşamaz; TL kazanç = Σ tl·p;
boş veri zarif. UI: vitest + Playwright görsel tur.
