# 05 — Başarı Kriterleri

Pilot (~2 hafta), aşağıdaki **üç kriter**den her birini karşıladığında "GO" olarak değerlendirilir.
Kriterler hem karar vericiler hem teknik ekip için ölçülebilir biçimde tanımlanmıştır.

---

## Kriter 1 — Bilinmeyen bir kaybı ortaya çıkardı

**Tanım:** Sistemin otomatik çıkarım (inferred) kanallarından en az biri — `FILL_LOSS` (doluluk
kaybı) ya da `SPEED_LOSS` (gizli hız kaybı) — pilot öncesinde takip edilmeyen **dominant** bir
kayıp olarak görünür.

**Neden önemli:** Bu iki kanal sensör ölçümüne değil matematiksel çıkarıma dayanır; nominal
doluluk/hız ile gerçekleşen arasındaki farkı otomatik hesaplar. Ekip bu kaybı manuel olarak takip
etmiyorsa, sistemin getirdiği bilgi doğrudan "görünmez para" anlamına gelir.

### Nasıl ölçülür

| Adım | Uç nokta / gösterge | Başarı eşiği |
|------|---------------------|--------------|
| 1 | `GET /loss-tree` → `items[*].kind == "inferred"` filtrele | `FILL_LOSS` veya `SPEED_LOSS` listede görünüyor |
| 2 | `GET /loss-tree/cost` → ilgili kalemin `tl` değeri | Toplam kayıp TL'nin **≥ 15 %**'ini oluşturuyor |
| 3 | Ekip onayı | "Bunu takip etmiyorduk" ifadesi kayıt altına alınıyor |

> **Not:** `/loss-tree` yanıtındaki `kind` alanı `"visible"` (gerçek sensör verisi) veya
> `"inferred"` (matematiksel çıkarım) değerini taşır. Başarı için `kind == "inferred"` olan bir
> kalem, kaybın büyüklük sıralamasında (Pareto) üst üçte birde yer almalıdır.

---

## Kriter 2 — TL tasarruf fırsatı niceledi

**Tanım:** Sistemin öneri motoru, pilot dönem için somut bir TL/dönem rakamı üretir; en az bir
iyileştirme kalemi için dar (güvenilir) bir kazanç aralığı sağlanır.

### Nasıl ölçülür

| Adım | Uç nokta / alan | Başarı eşiği |
|------|-----------------|--------------|
| 1 | `GET /recommendations` → `total_estimated_gain_tl` | > 0 TL; raporda üst 1–2 kalem açıkça listelenmiş |
| 2 | Her öneri öğesi → `estimated_gain_tl_low` / `estimated_gain_tl_high` | Her iki alan dolu; `low > 0` |
| 3 | Karar vericiye sunum | "X TL – Y TL arasında tasarruf" şeklinde somut bir aralık sunulabildi |

> **Alanlar:** `estimated_gain_tl` nokta tahmin (iyimser üst sınır); `estimated_gain_tl_low` ve
> `estimated_gain_tl_high` yapılandırma katsayılarıyla üretilen güven bandıdır. Tüm alanlar
> `GET /recommendations` yanıtının `recommendations[]` dizisinde her öğede bulunur;
> `total_estimated_gain_tl` ise yanıtın üst düzeyinde toplam değeri verir.

---

## Kriter 3 — Veri uçtan uca güvenilir aktı

**Tanım:** Pilot süresince veri akışı kabul edilebilir kalite eşiğinin üzerinde kaldı ve dashboard
uçları performans SLA'sını karşıladı.

### Nasıl ölçülür

| Adım | Uç nokta / gösterge | Başarı eşiği |
|------|---------------------|--------------|
| 1 | `POST /ingest` → `rejected_count` | `rejected_count / total_count ≤ 0.05` (≤ %5 red oranı) |
| 2 | H3 veri-yeterlilik skoru (`data_sufficiency`) | ≥ 0.6 (sistemin kendi öz-teşhis çıkışı) |
| 3 | Dashboard uçları yanıt süresi (H9) | `GET /loss-tree`, `/loss-tree/cost`, `/recommendations` her biri **< 2 sn** |
| 4 | `/loss-tree/cost` → `tl_low` / `tl_high` / `confidence` | Tüm çıkarım kalemleri için alanlar dolu; `confidence` sayısal |

> **Güven bantları:** `/loss-tree/cost` yanıtındaki her `"inferred"` kalem için `tl_low`,
> `tl_high` ve `confidence` alanları otomatik hesaplanır. Bu alanların varlığı, sistemin kendi
> belirsizliğini gizlemediğinin kanıtıdır. Boş ya da `null` gelen bir alan veri yetersizliğine
> işaret eder ve kriterden düşme gerekçesi sayılır.

---

## Değerlendirme Şablonu

Pilot sonunda aşağıdaki tabloyu doldurun. Her kriter için "✓" (karşılandı) ya da "✗"
(karşılanmadı) işaretleyin ve kısa not ekleyin.

| Kriter | Ölçüm (hangi uç / gösterge) | Sonuç (✓ / ✗) | Not |
|--------|------------------------------|----------------|-----|
| 1 — Bilinmeyen kayıp | `GET /loss-tree` → `kind == "inferred"` kalemi Pareto üst 1/3'te + ekip "bunu takip etmiyorduk" dedi | | |
| 2 — TL tasarruf fırsatı | `GET /recommendations` → `total_estimated_gain_tl` > 0; en az 1 öğede `estimated_gain_tl_low` / `_high` dolu | | |
| 3 — Güvenilir veri akışı | `POST /ingest` red oranı ≤ %5; H3 skoru ≥ 0.6; uç yanıt < 2 sn; `/loss-tree/cost` güven bandı dolu | | |

**Pilot süresi:** __________ – __________

**Değerlendiren:** __________

---

**Genel karar:**

> **GO** — Tüm kriterler karşılandı; tam üretime geçiş planlanabilir.
>
> **İyileştir** — 1 veya 2 kriter kısmen karşılandı; belirlenen iyileştirmelerle 2. pilot turu önerilebilir.
>
> **Durdur** — Hiçbir kriter ya da yalnız 1 kriter karşılandı; ekonomik gerekçe yok.

Karar: ☐ GO &nbsp;&nbsp; ☐ İyileştir &nbsp;&nbsp; ☐ Durdur

Gerekçe: ___________________________________________________________________________
