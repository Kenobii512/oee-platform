# Duyarlılık Analizi — Parametre → OEE Etkisi

Her senaryo parametresi gerçekçi düşük→yüksek aralığında oynatıldı; OEE deltası (3 seed ortalaması) ölçüldü. Azalan etkiye göre sıralı.

| Sıra | Parametre | Aralık (düşük→yüksek) | OEE Δ | Yön |
|------|-----------|------------------------|-------|-----|
| 1 | `speed_loss.factor_mean` | 1.0 → 1.5 | -0.625 | down |
| 2 | `failures.mtbf_min` | 4000.0 → 500.0 | -0.089 | down |
| 3 | `microstops.mean_interval_min` | 120.0 → 15.0 | -0.057 | down |
| 4 | `fill_loss.mean` | 0.7 → 1.0 | -0.001 | down |

**Okuma:** En üstteki parametreler OEE'yi en çok oynatır → iyileştirme ve what-if önceliği oraya. `fill_loss.mean` = askı doluluk oranı (yüksek = az kayıp); `speed_loss.factor_mean` = süre çarpanı (yüksek = yavaş).

_Üretim: `python -m tools.sensitivity --report ...` (simülatör venv'i)._
