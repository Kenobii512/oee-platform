# Hat Tanımı Yazım Kılavuzu (pilot kiti)

Yeni bir kaplama hattını platforma tanıtmak için tek dosya yeterlidir: bir **hat-tanımı YAML**'ı.
Kod değişmez — yeni hat = yeni YAML. Bu kılavuz, bir kişinin yardımsız doğru tanım yazmasına yeter.

Tanımı göndermeden önce **`POST /line/validate`** ile doğrulayın: dönen
`{"valid": true, "errors": []}` ise tanım hazırdır; değilse `errors` listesi tam olarak neyi
düzelteceğinizi söyler.

## Asgari yapı

```yaml
line:
  id: LINE-01                 # ZORUNLU — hattın benzersiz kimliği
  name: "Kaplama Hattı 1"     # opsiyonel görünen ad

start_datetime: "2026-01-05 06:00"   # simülasyon/raporlama başlangıcı (opsiyonel)

tanks:                        # ZORUNLU — en az bir tank; askı bu sırayla geçer
  - id: yagsizlandirma
    name: "Yağsızlandırma"
    time_min: 3.0             # ZORUNLU — kayıpsız işlem süresi alt sınırı (dk)
    time_max: 4.0             # ZORUNLU — üst sınır; time_min ≤ time_max olmalı
    capacity: 1              # > 0 (aynı anda tanktaki azami askı); varsayılan 1
    max_hold_min: 3.0         # işlem bitince vinç gelene kadar tolere edilen bekleme
  - id: kaplama
    name: "Kaplama Banyosu"
    time_min: 20.0
    time_max: 25.0
    capacity: 1
    bottleneck: true          # TAM 1 tank bottleneck olmalı (darboğaz banyosu)
    max_hold_min: 2.0
  # ... diğer tanklar (durulama, kurutma, vb.)

hoist:
  move_min: 0.5               # her transfer süresi (dk)

orders:                       # iş emirleri (Quality paydası için carrier_qty zorunlu)
  - order_id: ORD-0001
    product_id: PRD-A
    planned_qty: 4000
    target_cycle_min: 40.0
    carrier_qty: 100          # ZORUNLU, > 0 — askı başına nominal parça (kalite paydası)
```

## Doğrulama kuralları (`POST /line/validate`)

| Kural | Neden |
|------|-------|
| `line.id` zorunlu | Hattı tanımlayan kimlik |
| `tanks` boş olamaz | En az bir işlem adımı gerekir |
| Her tank `id`, `time_min`, `time_max` taşır | Süre aralığı (uniform örneklenir) |
| `time_min ≤ time_max` | Geçerli aralık |
| `capacity > 0` (tamsayı) | Tank doluluk/çekişme hesabı |
| **Tam 1 tank `bottleneck: true`** | Darboğaz = kapasite + kalite paydası referansı (simülatör guard'ıyla hizalı) |
| Her order `carrier_qty > 0` | Quality (ilk-geçiş) paydası; tanımsızsa kalite hesaplanamaz |

## Sık hatalar

- **Birden çok / hiç bottleneck:** Tam olarak bir tankı `bottleneck: true` işaretleyin (genelde kaplama banyosu).
- **`carrier_qty` eksik:** Kalite paydası buradan gelir; her order'a ekleyin.
- **`time_min > time_max`:** Alt/üst sınırı karıştırmayın.
- **`capacity: 0`:** En az 1 olmalı.

## Doğrulama akışı

```bash
# Tanımı JSON'a çevirip doğrula (geçersizse errors listesi gelir):
curl -X POST http://localhost:8000/line/validate \
     -H "Content-Type: application/json" \
     -d @line_definition.json
# -> {"valid": true, "errors": []}   (hazır)
# -> {"valid": false, "errors": ["tanks[4] (kaplama): time_min (99.0) > time_max (1.0)", ...]}
```

Geçerli tanım, `config/line_default.yaml` yerine konularak (veya `OEE_LINE_CONFIG` env'i ile)
platforma tanıtılır.
