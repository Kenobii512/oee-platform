# Pilot Kiti A — Doküman Paketi Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Kanonik kayıt:** bu plan zaten `oee-platform/docs/superpowers/plans/` altında.
> **Spec:** `docs/superpowers/specs/2026-06-30-pilot-kiti-A-dokuman-paketi-design.md`.

**Goal:** `docs/pilot-kit/` altında, H1–H9 yeteneklerini birbirine bağlayan, hem prospect ikna hem ~2 haftalık gerçek pilot kurulumuna yetecek 6 dosyalık Markdown doküman demeti üretmek. Yeni ürün kodu YOK.

**Architecture:** Altı bağımsız-okunur Markdown dosyası; ortak referanslar (sözleşme şeması, deploy, hat kılavuzu) mevcut dokümanlara LİNK ile paylaşılır (kopyalama yok). İki kitle iç içe: karar verici + saha teknik.

**Tech Stack:** Markdown (mevcut `docs/*.md` deseni). Doğrulama için mevcut backend + fixtures (`.venv` pytest, `POST /ingest?adapter=`, `POST /line/validate`).

## Global Constraints

- **Yeni ürün kodu YOK.** Yalnız `docs/pilot-kit/*.md` (+ opsiyonel küçük doğrulama komutları çalıştırma). Backend/frontend değişmez.
- **DRY:** var olan dokümanlara link ver, kopyalama; `deployment.md`, `line-definition-guide.md`, `sensitivity_report.md`, plan/spec dosyaları.
- **Doğruluk:** sözleşme şeması `backend/app/models/contract.py` ile birebir; komutlar/uçlar gerçek (aşağıda sabitler). Ölü link yok.
- **İki kitle:** karar verici dosyaları jargonsuz; teknik dosyalar kolon/komut düzeyinde somut.
- **Dil:** Türkçe içerik (mevcut doküman dili).
- **Başarı kriterleri (spec):** (1) bilinmeyen kaybı ortaya çıkardı, (2) TL fırsatı niceledi, (3) veri uçtan uca güvenilir aktı.
- **Pilot şekli:** ~2 hafta (kickoff → 2 hafta → review); veri devri = ham export + H2 adaptör.

### Sabitler (dokümanlarda kullanılacak GERÇEK değerler)

- **Sözleşme CSV'leri** (`app/models/contract.py`):
  - `events.csv`: `timestamp, line_id, carrier_id, station_id, event_type, duration, reason_code, operator_entered_reason, operator_entry_ts`. `event_type ∈ {LOAD, PROCESS, MOVE, UNLOAD, QC, OVER_RESIDENCE, DOWNTIME, MICROSTOP, STRIP}`; `duration` DAKİKA, negatif olamaz; hat-seviyesi olaylarda (DOWNTIME/MICROSTOP) `carrier_id` boş.
  - `production.csv`: `carrier_id, order_id, loaded_qty, good_count, redo_count, scrap_count`. Değişmez: `good_count + scrap_count == loaded_qty` (no-scrap: `scrap_count=0`); `redo_count` = redo'dan geçen ayrık parça.
  - `orders.csv`: `order_id, product_id, target_cycle, planned_qty`.
- **Firewall:** `ground_truth*` dosyaları ASLA gönderilmez (loader açmadan atlar).
- **Adaptör (H2):** profil `config/adapters/generic_plant.yaml`; örnek ham veri `backend/tests/fixtures/raw/`; uç `POST /ingest` gövde `{"path": "...", "adapter": "generic_plant"}`.
- **Hat tanımı (H7):** `config/line_default.yaml`; doğrulama `POST /line/validate` → `{"valid": bool, "errors": [...]}`; kılavuz `docs/line-definition-guide.md`.
- **Kirli-veri (H1):** loader bozuk satırı `LoadReport`'a yazar, sağlamı yükler; `POST /ingest` yanıtı `{"accepted":{...}, "rejected_count":N, "skipped":[...], "errors":[...]}`.
- **Güven (H3):** `/loss-tree/cost` kategorilerinde `tl_low/tl_high/confidence/low_confidence`; öneri kaleminde `low_confidence`.
- **Demo uçları:** `GET /scenarios` (6 senaryo, `narrative`/`highlight`), `POST /scenarios/{id}/activate`, `GET /oee`, `GET /loss-tree/cost`, `GET /recommendations`, `GET /replay/stream?scenario=&speed=&steps=`.
- **6 senaryo:** `baseline, breakdown_storm, microstop_plague, speed_bottleneck, fill_problem, redo_crisis`.
- **Deploy (H9):** `docs/deployment.md`; env `OEE_AUTH_PASS/USER/SECRET`, `SAMPLE_DATA_DIR`, `OEE_LOG_LEVEL`, `$PORT`; `/health` public.
- **Perf (H9):** pano uçları ~12 hafta veride < 2 sn.

---

## Task 0: Branch + dizin iskeleti

**Files:**
- Create: `oee-platform/docs/pilot-kit/` (dizin)

- [ ] **Step 1:** main'den branch: `git checkout main && git checkout -b feat/pilot-kit-docs`.
- [ ] **Step 2:** `docs/pilot-kit/` dizinini oluştur (ilk dosya Task 1'de gelir; boş dizin commit'lenmez — Task 1 ile birlikte).

---

## Task 1: `03-veri-onboarding.md` (teknik omurga — önce bu, çünkü diğerleri buna atıfta bulunur)

**Files:**
- Create: `oee-platform/docs/pilot-kit/03-veri-onboarding.md`

**Interfaces — Produces:** Diğer dosyaların link vereceği kanonik "veri nasıl bağlanır" kaynağı.

- [ ] **Step 1: İçeriği yaz.** Şu bölümlerle (kitle: saha teknik):
  1. **Sözleşme nedir** — platform 3 CSV bekler; her birinin kolonları + anlamı (yukarıdaki Sabitler'den birebir: events/production/orders). "Platform verinin kaynağını bilmez" ilkesi. `ground_truth` GÖNDERİLMEZ (firewall).
  2. **Ham export'unu nasıl verirsin** — PLC/SCADA/MES'ten ne çıkarabiliyorsan onu ver; kolon adların/birimlerin farklı olabilir. → **H2 adaptör profili**: `config/adapters/generic_plant.yaml` örneğini göster (kolon eşleme, `timestamp_format`, `timezone`, `duration_unit`, `reason_map`, `event_type_rule`, `required`, `defaults`); `POST /ingest` `{"path":"<ham_dizin>","adapter":"generic_plant"}`. "Yeni tesis = yeni YAML, kod değil."
  3. **Hattı tanımla** — `config/line_default.yaml` yapısı özet + `docs/line-definition-guide.md`'ye link; göndermeden önce `POST /line/validate` ile doğrula (`{"valid":true,"errors":[]}`).
  4. **Kirli veriye ne olur (H1 güvence)** — eksik/bozuk/tip-hatası satır reddedilip `rejected_count`+`errors`'a yazılır, SAĞLAM satır yüklenir; sistem çökmez. Örnek `POST /ingest` yanıtı göster.
  5. **Deploy** — `docs/deployment.md`'ye link (Render/Docker, env, `/health`).
- [ ] **Step 2: Doğrula (komutlar gerçekten çalışıyor).** Backend `.venv` ile dokümandaki onboarding yolunu koştur:
```bash
cd oee-platform/backend
.venv/Scripts/python.exe -m pytest tests/test_adapter_end_to_end.py tests/test_line_validate.py -q
```
Beklenen: PASS (dokümandaki adaptör + validate yolları gerçek).
- [ ] **Step 3: Link kontrolü.** `docs/line-definition-guide.md` ve `docs/deployment.md` dosyalarının var olduğunu doğrula (`ls oee-platform/docs/`).
- [ ] **Step 4: Commit:** `docs(pilot-kit): veri-onboarding kılavuzu (sözleşme + adaptör + validate + kirli-veri)`.

---

## Task 2: `01-deger-onermesi.md` (karar verici — tek sayfa)

**Files:**
- Create: `oee-platform/docs/pilot-kit/01-deger-onermesi.md`

- [ ] **Step 1: İçeriği yaz** (kitle: amir/müdür, jargonsuz, ~1 sayfa):
  1. **Problem** — kayıplar görünmez; Excel/manuel takip geç ve eksik; "en büyük kaybınız nerede?" cevapsız.
  2. **Çözüm** — bir bakışta: OEE + Availability×Performance×Quality şelalesi + **en büyük kayıp** + **TL karşılığı** + **ne yapmalı (öneri)**. Tek ekran, saha temposunda.
  3. **Neden güvenilir** — görünür (duruş/mikro-duruş) vs **çıkarımsal** (gizli hız/doluluk kaybı) ayrımı şeffaf; **güven aralığı** (H3: düşük veride "düşük güven" rozeti, sessiz yanlış sayı yok); tek manuel girdi = mikro-duruş, gerisi sistemce.
  4. **Abartı yok (anti-iddialar)** — kazanç tahminleri ÜST SINIR + aralık; örtüşebilir; kesinlik satmıyoruz, görünürlük satıyoruz.
  5. **Pilot ne getirir** — ~2 haftada: bilinmeyen bir kaybı görünür kılma + TL fırsatı (başarı kriterlerine link: `05-basari-kriterleri.md`).
- [ ] **Step 2: Link kontrolü** — `02-demo-senaryosu.md` ve `05-basari-kriterleri.md`'ye referanslar (bu dosyalar sonraki task'larda; göreli link adları doğru yazılsın).
- [ ] **Step 3: Commit:** `docs(pilot-kit): değer önermesi (karar verici, tek sayfa)`.

---

## Task 3: `02-demo-senaryosu.md` (satış/portföy — rehberli demo)

**Files:**
- Create: `oee-platform/docs/pilot-kit/02-demo-senaryosu.md`

- [ ] **Step 1: İçeriği yaz:**
  1. **Demoyu aç** — yerel: `docker compose up --build` → `http://localhost:8000` (veya Render URL); auth kapalıysa direkt pano.
  2. **Rehberli akış** — adım adım: senaryo dropdown'undan seç → üstte anlatı bandı + "neye bak" (H6) → **en büyük kaybı** oku → **TL Pareto** → **öneri (TL'li)**; canlı **Replay** (`/replay/stream`) ile birikimi göster.
  3. **6 senaryo anlatısı** — her biri için bir cümle + hangi grafiğe bak (`GET /scenarios` `narrative`/`highlight` alanlarından; senaryolar: baseline, breakdown_storm, microstop_plague, speed_bottleneck, fill_problem, redo_crisis). Bu, `config/scenarios.yaml` ile tutarlı olmalı.
  4. **"Kendi verinle"** — demo senaryosundan sonra: `03-veri-onboarding.md`'ye köprü (aynı pano, senin verinle).
- [ ] **Step 2: Doğrula** — `GET /scenarios` çıktısındaki `id` ve `narrative` alanlarının dokümandaki 6 senaryoyla eşleştiğini kontrol et:
```bash
cd oee-platform/backend
.venv/Scripts/python.exe -c "import yaml; d=yaml.safe_load(open('../config/scenarios.yaml',encoding='utf-8')); print([s['id'] for s in d['scenarios']])"
```
Beklenen: 6 senaryo id'si dokümanla aynı.
- [ ] **Step 3: Commit:** `docs(pilot-kit): rehberli demo senaryosu (6 senaryo + neye bak)`.

---

## Task 4: `04-pilot-runbook.md` (her iki kitle — 2 haftalık akış)

**Files:**
- Create: `oee-platform/docs/pilot-kit/04-pilot-runbook.md`

- [ ] **Step 1: İçeriği yaz** — fazlar + go/no-go + roller + zaman çizelgesi şablonu:
  - **Faz 0 — Hazırlık (kickoff, ~1 gün):** hattı tanımla → `POST /line/validate` yeşil (H7); müşteriden **bir örnek ham export** al; adaptör profilini kur (H2); deploy (H9). → link `03-veri-onboarding.md`.
  - **Faz 1 — Smoke (~1–2 gün · GO/NO-GO KAPISI):** örnek veriyi `POST /ingest?adapter=` ile yükle → pano açılıyor, `/oee` makul, **veri-yeterlilik skoru (H3) eşik üstü**, kirli-satır oranı kabul edilebilir. NO-GO → adaptör/veri düzelt, tekrar. *(Not: bu kapı B — pilot doctor ile otomatikleşecek.)*
  - **Faz 2 — Toplama (~2 hafta):** periyodik ingest; pano izlenir; trend birikir.
  - **Faz 3 — Review:** 3 başarı kriterine karşı değerlendir → **pilot raporu** (link `05-basari-kriterleri.md`; rapor artefaktı C alt-projesinde).
  - **Roller tablosu:** bizden (kurulum/analiz) / müşteriden (veri export, hat bilgisi, review katılımı).
  - **Zaman çizelgesi şablonu:** Gün 1 (kickoff) … Gün 3 (smoke gate) … Gün 14 (review) — doldurulabilir.
- [ ] **Step 2: Link kontrolü** — `03-veri-onboarding.md`, `05-basari-kriterleri.md` göreli linkleri doğru.
- [ ] **Step 3: Commit:** `docs(pilot-kit): 2 haftalık pilot runbook + go/no-go kapıları`.

---

## Task 5: `05-basari-kriterleri.md` (her iki kitle — ölçüm + değerlendirme)

**Files:**
- Create: `oee-platform/docs/pilot-kit/05-basari-kriterleri.md`

- [ ] **Step 1: İçeriği yaz** — 3 kriterin operasyonel tanımı + nasıl ölçülür + değerlendirme şablonu:
  1. **Bilinmeyen kaybı ortaya çıkardı** — nasıl ölçülür: `GET /loss-tree` + `/loss-tree/cost` ekibin önceden bilmediği bir **çıkarımsal** kanalı (FILL_LOSS/SPEED_LOSS) baskın gösterdi mi? Kanıt: ekip "bunu takip etmiyorduk" dedi.
  2. **TL fırsatı niceledi** — nasıl ölçülür: `GET /recommendations` `total_estimated_gain_tl` + kalem bazında `estimated_gain_tl_low/high`; en büyük 1–2 kalem için somut TL/dönem.
  3. **Veri uçtan uca güvenilir aktı** — nasıl ölçülür: `POST /ingest` `rejected_count` kabul edilebilir oranda; H3 veri-yeterlilik skoru eşik üstü; pano < 2 sn (H9); güven aralıkları şeffaf.
  - **Değerlendirme şablonu** — doldurulabilir tablo: kriter | ölçüm | sonuç (✓/✗) | not. + genel karar (GO/İyileştir/Durdur).
- [ ] **Step 2: Doğrula** — bahsedilen uçların gerçek olduğunu teyit (imza/anahtarlar): `GET /recommendations` `total_estimated_gain_tl` + `estimated_gain_tl_low/high` alanları `app/api/recommend_routes.py`/`recommend.py` ile tutarlı; `/loss-tree/cost` `confidence` alanı mevcut.
```bash
cd oee-platform/backend
.venv/Scripts/python.exe -m pytest tests/test_confidence_propagation.py tests/test_cost_endpoint_confidence.py -q
```
Beklenen: PASS.
- [ ] **Step 3: Commit:** `docs(pilot-kit): başarı kriterleri + ölçüm + değerlendirme şablonu`.

---

## Task 6: `README.md` (indeks) + çapraz-link doğrulama pası

**Files:**
- Create: `oee-platform/docs/pilot-kit/README.md`
- Modify: `oee-platform/docs/STATUS.md` (pilot kiti A başladı notu)

- [ ] **Step 1: `README.md` yaz** — kit indeksi:
  - "Pilot 3 cümlede" özet.
  - **Hangi dosyayı kim okur** tablosu: `01` karar verici, `02` demo/satış, `03` saha teknik, `04`+`05` her ikisi.
  - **Nasıl kullanılır** — iki yol: (a) satış görüşmesi (01 + 02), (b) gerçek kurulum (03 + 04 + 05).
  - Alt-projeler notu: B (pilot doctor) Faz 0–1'i otomatikler; C (showcase) pilot raporunu üretir — sonra gelecek.
- [ ] **Step 2: Ölü link taraması** — tüm göreli linkleri çöz:
```bash
cd oee-platform/docs/pilot-kit
grep -oE "\]\(([^)]+\.md)\)" *.md | sed -E 's/.*\(([^)]+)\)/\1/' | sort -u
# her dosya var mı elle doğrula (../deployment.md, ../line-definition-guide.md, ../superpowers/specs/... dahil)
ls . ../deployment.md ../line-definition-guide.md
```
Beklenen: referans verilen tüm `.md` yolları var; kırık link yok.
- [ ] **Step 3: STATUS.md güncelle** — "Sıradaki yol haritası"na: "Pilot kiti A (doküman paketi) TAMAM (`docs/pilot-kit/`); sırada B (pilot doctor CLI) + C (showcase)."
- [ ] **Step 4: Commit:** `docs(pilot-kit): README indeksi + link doğrulama + STATUS`.

---

## Doğrulama (uçtan uca)

1. **6 dosya var:** `docs/pilot-kit/{README,01-deger-onermesi,02-demo-senaryosu,03-veri-onboarding,04-pilot-runbook,05-basari-kriterleri}.md`.
2. **Komutlar gerçek:** onboarding + başarı-kriteri dokümanlarında geçen backend yolları ilgili testlerle (`test_adapter_end_to_end`, `test_line_validate`, `test_confidence_propagation`, `test_cost_endpoint_confidence`) doğrulandı.
3. **Şema tutarlı:** `03`'teki sözleşme kolonları `app/models/contract.py` ile birebir; senaryo id'leri `config/scenarios.yaml` ile aynı.
4. **Ölü link yok:** tüm göreli `.md` referansları çözülüyor (mevcut `deployment.md`, `line-definition-guide.md`, spec/plan dahil).
5. **İki kitle:** `01`/`02` jargonsuz; `03`/`04`/`05` komut/kolon düzeyinde somut.

## Tamamlanınca

- Branch `feat/pilot-kit-docs` → PR/merge → `main`.
- Sırada: **B — Pilot doctor CLI** (kendi brainstorming→spec→plan döngüsü), sonra **C — Showcase**.
