# Veri Onboarding Kılavuzu

Hedef kitle: tesis PLC/SCADA/MES teknik sorumlusu ve IT.
Bu kılavuz, tesisin verisini platforma nasıl bağlayacağını adım adım açıklar.

---

## 1. Sözleşme nedir

Platform, tesisin veriyi **nereden ürettiğini bilmez** — PLC logundan, SCADA export'undan veya MES API'sinden fark etmez. Önemli olan, aşağıdaki üç CSV dosyasının **sütun adlarının ve veri kurallarının** sözleşmeye uyması.

> **Güvenlik sınırı (firewall):** `ground_truth` ile başlayan dosyalar (`ground_truth_events.csv` vb.) yükleyici tarafından **açılmadan atlanır**. Bu dosyalar hiçbir zaman gönderilmez.

### 1.1 `events.csv`

Hat üzerinde gerçekleşen her olayın kayıtlarını içerir.

| Sütun | Tür | Açıklama |
|-------|-----|----------|
| `timestamp` | ISO 8601 datetime | Olayın başlangıç zamanı |
| `line_id` | string | Hattın benzersiz kimliği (`line.id` ile eşleşmeli) |
| `carrier_id` | string (boş olabilir) | Askı kimliği. Hat-seviyesi olaylarda (`DOWNTIME`, `MICROSTOP`) **boş bırakılır** |
| `station_id` | string (boş olabilir) | Tank/istasyon kimliği |
| `event_type` | enum | Aşağıdaki değerlerden biri |
| `duration` | float (dakika) | Olay süresi — **negatif olamaz** |
| `reason_code` | string (boş olabilir) | Standart duruş/red kodu |
| `operator_entered_reason` | string (boş olabilir) | Operatörün serbest metin açıklaması |
| `operator_entry_ts` | datetime (boş olabilir) | Operatörün açıklamayı girdiği zaman |

**`event_type` geçerli değerleri:**

```
LOAD | PROCESS | MOVE | UNLOAD | QC | OVER_RESIDENCE | DOWNTIME | MICROSTOP | STRIP
```

- `DOWNTIME` ve `MICROSTOP`: hat seviyesi olaylar — `carrier_id` **boş** olmalı.
- `duration`: **dakika** cinsinden, sıfır veya pozitif tamsayı/ondalık.

### 1.2 `production.csv`

Her askının kalite/miktar özetini içerir.

| Sütun | Tür | Açıklama |
|-------|-----|----------|
| `carrier_id` | string | Askı kimliği |
| `order_id` | string | Bağlı iş emri |
| `loaded_qty` | int | Askıya yüklenen toplam parça sayısı |
| `good_count` | int | İlk geçişte iyi olan parça sayısı |
| `redo_count` | int | Yeniden işleme giren **farklı** parça sayısı |
| `scrap_count` | int | Hurda olan parça sayısı |

**Değişmez kural:** `good_count + scrap_count == loaded_qty`

Hurdanın olmadığı (no-scrap) tesislerde `scrap_count = 0` ve `good_count = loaded_qty` gönderilir.
`redo_count`, yeniden işlemden geçen parça sayısıdır; Quality (ilk geçiş) paydasını etkiler ama `loaded_qty` denklemine dahil değildir.

### 1.3 `orders.csv`

İş emirleri / planlama verisi.

| Sütun | Tür | Açıklama |
|-------|-----|----------|
| `order_id` | string | İş emri kimliği |
| `product_id` | string | Ürün/tarif kimliği |
| `target_cycle` | float (dakika) | Nominal çevrim süresi (ürün başvurusu). Not: OEE Performance hesabı bu alanı değil, hat tanımındaki tank sürelerini (`time_min`/`time_max`) kullanır. |
| `planned_qty` | int | Planlanan toplam parça adedi |

---

## 2. Ham export'unu nasıl verirsin

Çoğu tesisin PLC/SCADA/MES export'u **farklı sütun adlarına, farklı zaman formatlarına ve farklı süre birimlerine** sahiptir. Platforma **ham dosyaları olduğu gibi** verebilirsiniz — köprü görevi, **H2 config-driven ingest adapter** yapar.

### 2.1 Adapter profili

Her tesis için bir YAML profili tanımlanır. Yeni bir tesis, yalnızca yeni bir YAML gerektirir — **kod değişmez.**

`config/adapters/generic_plant.yaml` (fabrika varsayılanı, tese göre kopyalanıp özelleştirilir):

```yaml
# H2 — örnek "saha dili" → sözleşme eşleme profili (jenerik bir fabrika CSV'si).
# Sözleşme sabittir; bu profil ham PLC/SCADA/MES olay logunu sözleşme events satırına çevirir.
# Yeni tesis = yeni YAML; kod değişmez.

# ham_kolon -> sözleşme_kolon
column_map:
  ts: timestamp
  machine: line_id
  carrier: carrier_id
  station: station_id
  evt: event_type
  dur_s: duration
  cause: reason_code

# strptime formatı (None/boş -> zaten ISO kabul edilir)
timestamp_format: "%d/%m/%Y %H:%M:%S"
# IANA saat dilimi (boş -> dönüşüm yok). Örn. "Europe/Istanbul"
timezone: null

# ham süre birimi; sözleşme birimi = DAKİKA. "s" -> /60, "min" -> aynen
duration_unit: s

# ham olay etiketi -> sözleşme EventType (eşlenemeyen değer açık hata)
event_type_rule:
  RUN: PROCESS
  STOP: MICROSTOP
  DOWN: DOWNTIME
  LOAD: LOAD
  UNLOAD: UNLOAD
  QC: QC

# ham neden etiketi -> standart reason_code (eşlenemeyen DOLU değer açık hata; boş -> boş)
reason_map:
  Sıkışma: jam
  Bakım: maintenance
  Ayar: setup
  Malzeme: material

# zorunlu ham kolonlar (eksik/boş -> açık hata)
required:
  - ts
  - machine
  - evt
  - dur_s

# eksik sözleşme alanları için varsayılan
defaults:
  station_id: ""
  operator_entered_reason: ""
  operator_entry_ts: ""
```

### 2.2 Profil anahtarları

| Anahtar | Açıklama |
|---------|----------|
| `column_map` | `ham_kolon: sözleşme_kolon` eşlemesi — burada listelenmeyen ham sütunlar atlanır |
| `timestamp_format` | Python `strptime` formatı; boş/`null` ise giriş zaten ISO 8601 varsayılır |
| `timezone` | IANA saat dilimi (ör. `"Europe/Istanbul"`); boş ise UTC dönüşümü yapılmaz |
| `duration_unit` | `s` → saniyeden dakikaya (`÷60`), `min` → doğrudan dakika olarak alınır |
| `event_type_rule` | Ham olay etiketi → sözleşme `EventType` dönüşüm tablosu; eşlenemeyen değer hata üretir |
| `reason_map` | Ham neden etiketi → standart `reason_code`; eşlenemeyen **dolu** değer hata üretir, boş → boş geçer |
| `required` | Zorunlu ham sütunlar; eksik/boş ise satır reddedilir |
| `defaults` | Eşlemede eksik kalan sözleşme sütunları için varsayılan değerler |

### 2.3 Ingest çağrısı

```bash
POST /ingest
Content-Type: application/json

{
  "path": "<ham_dizin>",
  "adapter": "generic_plant"
}
```

- `path`: Tesisin ham CSV dosyalarının bulunduğu dizin yolu.
- `adapter`: `config/adapters/` altındaki profil adı (`.yaml` uzantısı olmadan).

> **Motto:** Yeni tesis = yeni YAML, kod değil.

---

## 3. Hattı tanımla

Platformun OEE hesaplaması yapabilmesi için hattın tankları, süre aralıkları ve darboğaz banyosu `config/line_default.yaml` (veya `OEE_LINE_CONFIG` env değişkeni ile belirtilen dosya) üzerinden tanımlanır.

Yapı özeti:
- **`line.id`** — zorunlu, hattın benzersiz kimliği
- **`tanks[]`** — her tank `id`, `time_min`, `time_max`, `capacity`; tam 1 tank `bottleneck: true`
- **`orders[]`** — her iş emri `carrier_qty > 0` (kalite paydası için zorunlu)

Tam yapı ve sık hatalar için bkz. **[Hat Tanımı Yazım Kılavuzu](../line-definition-guide.md)**.

### Doğrulama

Tanımı göndermeden önce:

```bash
POST /line/validate
Content-Type: application/json

{ ... hat tanımı JSON ... }
```

Başarılı yanıt:

```json
{"valid": true, "errors": []}
```

Hata varsa `errors` listesi tam olarak neyi düzelteceğinizi gösterir (ör. `"bottleneck: tam 1 tank olmalı"`, `"tanks[2] (boyama): time_min > time_max"`).

Doğrulama kurallarının tamamı: tam 1 bottleneck, `time_min ≤ time_max`, `capacity > 0`, `carrier_qty > 0`, `line.id` dolu, `tanks` listesi boş değil.

---

## 4. Kirli veriye ne olur (H1 güvencesi)

Platform, bozuk/eksik/yanlış-tip satırlara **çökmez.** Hatalı satırlar `LoadReport` içinde raporlanır; geçerli satırlar normal şekilde yüklenir.

### Örnek `POST /ingest` yanıtı

```json
{
  "accepted": {
    "events": 142,
    "production": 12,
    "orders": 3
  },
  "rejected_count": 4,
  "skipped": ["ground_truth_events.csv"],
  "errors": [
    {"file": "events.csv", "row": 17, "error": "duration negatif olamaz: -5.0"},
    {"file": "events.csv", "row": 31, "error": "event_type gecersiz deger: 'RINSE'"},
    {"file": "production.csv", "row": 8, "error": "good_count + scrap_count (80+30) != loaded_qty (100)"},
    {"file": "events.csv", "row": 55, "error": "zorunlu alan eksik: 'ts'"}
  ]
}
```

- **`accepted`**: sözleşmeyi geçen ve veritabanına yazılan satır sayıları (dosya başına).
- **`rejected_count`**: toplam reddedilen satır adedi.
- **`skipped`**: `ground_truth*` gibi güvenlik sınırı kapsamındaki atlanmış dosyalar.
- **`errors`**: her hata için `file` (dosya adı), `row` (satır numarası) ve `error` (neden) alanlarını içeren nesne listesi.

Bir dosyada bozuk satırlar olsa bile diğer dosyalar ve aynı dosyanın geçerli satırları yüklenir. OEE hesaplaması kısmi veriyle de çalışır.

---

## 5. Deploy

Platform Render (bulut) veya Docker (yerelde) olarak çalışır. Ortam değişkenleri, `/health` endpoint'i ve adım adım kurulum talimatları için bkz. **[Deployment Kılavuzu](../deployment.md)**.
