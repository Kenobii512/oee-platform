# Pilot Kiti — Alt-proje B: Pilot Doctor CLI (Tasarım/Spec)

**Tarih:** 2026-07-01 · **Durum:** onaylandı, plana hazır

## Context

Pilot Kiti A (doküman paketi, `docs/pilot-kit/`) main'de. A→B devir sözleşmesi
(`2026-06-30-pilot-kiti-A-dokuman-paketi-design.md` "Alt-proje sınırları"): **runbook Faz 0–1
kontrol listesi, B'nin otomatikleyeceği denetimlerin sözleşmesidir** — hat validator + adaptör +
kirli-veri raporu + yeterlilik skoru → tek "hazır mı?" raporu. Bugün bu kontroller runbook'ta elle,
tek tek HTTP uçlarına karşı yapılıyor; sahadaki teknik sorumlu için tek komutluk, makine-karar
verebilen bir kapı gerekiyor.

## Goal

`python -m tools.pilot_doctor <veri-dizini>` tek komutla Faz 0–1 kontrollerini koşar ve tek bir
**GO / NO-GO** raporu üretir. Yeni analitik YOK — mevcut H1/H2/H3/H7 yapı taşları yeniden
kullanılır; araç yalnız orkestre eder ve eşiklere karşı karar verir.

## Sabit kararlar (brainstorming çıktısı)

- **In-process, sunucusuz:** CLI backend fonksiyonlarını doğrudan çağırır
  (`validate_line_dict`, `apply_mapping`, `load_csv_dir`, `compute_oee`, `data_sufficiency`) ve
  **geçici DuckDB** kullanır. Gerçek `oee.duckdb`'ye asla dokunmaz; sunucu gerekmez. Aynı
  loader/validator kod yolu = sunucunun yapacağının birebir provası. (HTTP modu YAGNI —
  gerekirse sonra `--url`.)
- **Eşikler = runbook varsayılanları + CLI bayrakları:** yeterlilik ≥ **0.6**
  (`--min-sufficiency`), red oranı ≤ **%5** (`--max-reject`). `config/confidence.yaml`'daki
  `sufficiency_threshold: 0.5` pano "düşük güven" rozetinin eşiğidir — AYRI amaç, DOKUNULMAZ;
  fark runbook'ta not edilir.
- **Çıktı:** ASCII insan-okur kontrol listesi (Windows cp1252 konsolu; `tools/corrupt.py`
  emsali) + exit code (**0=GO, 1=NO-GO, 2=kullanım hatası**) + `--json` makine-okur çıktı.
- **Yer/desen:** `backend/tools/pilot_doctor.py`, `tools/corrupt.py` deseninde (argparse,
  `main(argv) -> int`, saf çekirdek fonksiyonlar + I/O yalnız orkestrasyonda).

## Denetimler (6 kontrol)

| # | Ad | Kaynak | Geçme koşulu |
|---|----|--------|--------------|
| 1 | `line` | `config_validate.validate_line_dict` | hata listesi boş |
| 2 | `adapter` | `adapter.load_adapter_config` + `adapt_dir_to_contract` | `AdapterError` yok (yalnız `--adapter` verilirse; yoksa SKIP) |
| 3 | `ingest` | `loader.load_csv_dir` → `LoadReport` (temp DuckDB) | kabul edilen satır > 0; `skipped`'ta `ground_truth` görünür (firewall kanıtı) |
| 4 | `oee` | `analytics.oee.compute_oee` | `0 < oee <= 1.0` (detayda A/P/Q — teşhis edilebilir FAIL) |
| 5 | `sufficiency` | `analytics.confidence.data_sufficiency` | `>= --min-sufficiency` (vars. 0.6) |
| 6 | `rejection` | `len(report.rejected) / (kabul+ret)` | `<= --max-reject` (vars. 0.05); 0 satır → FAIL |

**Bağımlılık kuralları:** line FAIL → oee + sufficiency SKIP (ingest/rejection yine koşar);
adapter FAIL → ingest/oee/sufficiency/rejection SKIP. **GO = hiç FAIL yok** (SKIP nötr).

## Mimari

- **Katmanlama:** araç yalnız `app.config`, `app.config_validate`, `app.ingest.*`,
  `app.store.duckdb_repo`, `app.analytics.{oee,confidence}` import eder — ASLA `app.api`/
  `app.main` (FastAPI import'u yok, lifespan yok, kazara gerçek DB yok).
- **Ön refactor:** `ingest_routes._adapt_to_contract` (api katmanında private) →
  `app/ingest/adapter.py`'ye public `adapt_dir_to_contract(raw_dir, mapping, out_dir)` taşınır;
  route yeni fonksiyonu çağırır. Katmanlama `api → ingest` yönüne döner, CLI de aynı fonksiyonu
  kullanır.
- **Geçici çalışma alanı:** `tempfile.TemporaryDirectory(ignore_cleanup_errors=True)` içinde
  `doctor.duckdb` + (adaptörlü yolda) `adapted/`; `repo.close()` `finally`'de, cleanup'tan önce
  (Windows dosya kilidi).

## Kapsam dışı (YAGNI)

- HTTP/canlı-sunucu modu (`--url`) — gerçek ihtiyaç doğunca.
- Faz 3 pilot raporu üretimi — o **C (showcase)** alt-projesi.
- Yeni eşik config dosyası — CLI bayrağı yeter; talep gelirse sonra.
- Periyodik/zamanlanmış koşum — pilot sırasında elle/CI'da çağrılır.

## Doğrulama

1. `tests/fixtures/baseline` → GO (exit 0); `skipped == ["ground_truth.csv"]`.
2. `tests/fixtures/dirty/type_corruption` → NO-GO (red ~%9.6 > %5); `--max-reject 0.5` ile GO
   (bayrak override çalışır).
3. `tests/fixtures/raw` + `--adapter generic_plant` → adaptör PASS; varsayılan eşikle NO-GO
   (13 olay → yeterlilik ~0.4), `--min-sufficiency 0` ile GO yolu.
4. Kenar durumlar çökmez: boş dizin, bozuk YAML, olmayan dizin/profil (exit 2).
5. Çıktı ASCII (`format_report(...).encode("ascii")` testte); `--json` şeması sabit.

## Sırada

Spec onaylanınca → uygulama planı (`docs/superpowers/plans/2026-07-01-pilot-kiti-B-pilot-doctor.md`).
Sonra **C — showcase** kendi döngüsünde.
