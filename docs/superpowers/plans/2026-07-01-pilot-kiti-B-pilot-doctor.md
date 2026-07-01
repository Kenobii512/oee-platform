# Pilot Kiti B — Pilot Doctor CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Kanonik kayıt:** bu plan zaten `oee-platform/docs/superpowers/plans/` altında.
> **Spec:** `docs/superpowers/specs/2026-07-01-pilot-kiti-B-pilot-doctor-design.md`.

**Goal:** `backend/tools/pilot_doctor.py` — Faz 0–1 kontrollerini (hat doğrulama, adaptör, smoke
ingest, OEE anlamlılığı, H3 yeterlilik, red oranı) tek GO/NO-GO raporunda otomatikleyen,
in-process + geçici-DuckDB CLI aracı. `tools/corrupt.py` deseni; TDD.

**Tech Stack:** stdlib argparse (click/typer YOK — requirements'ta yok), mevcut `app.*`
fonksiyonları, pytest.

## Global Constraints

- **Import hijyeni:** `tools/pilot_doctor.py` ASLA `app.api`/`app.main` import etmez.
- **Gerçek DB'ye dokunma:** tüm ingest geçici DuckDB'ye; cwd'de `*.duckdb` kalıntısı bırakma.
- **Konsol çıktısı ASCII** (Windows cp1252; Türkçe aksansız — corrupt.py emsali). Kaynak kod
  docstring/yorumları Türkçe (UTF-8 dosya sorun değil).
- **Eşik varsayılanları:** `--min-sufficiency 0.6`, `--max-reject 0.05`;
  `config/confidence.yaml` DEĞİŞMEZ.
- **Red oranı `len(report.rejected)`'ten** — `to_dict()["errors"]` 50'de kırpılır, ondan DEĞİL.
- **Exit:** 0=GO, 1=NO-GO, 2=kullanım hatası (olmayan dizin/dosya/profil; argparse hataları).
  Bozuk İÇERİK (YAML/CSV) = NO-GO (1), kullanım hatası değil.

---

## Task 1: Refactor — `adapt_dir_to_contract` api→ingest katmanına

**Files:** `backend/app/ingest/adapter.py`, `backend/app/api/ingest_routes.py`

- [ ] `_adapt_to_contract` + `_write_contract_events` + `_ADAPTED_FILE`/`_PASSTHROUGH_FILES`
  sabitlerini `ingest_routes.py`'den `adapter.py`'ye taşı; public ad:
  `adapt_dir_to_contract(raw_dir: str | Path, mapping: AdapterConfig, out_dir: Path) -> None`.
  `_EVENT_FIELDS` ile adapter.py'deki `_CONTRACT_EVENT_FIELDS`'i TEK sabitte birleştir.
- [ ] `ingest_routes.py` yeni public fonksiyonu import edip çağırır (`_resolve_profile` api'de kalır).
- [ ] Kapı: `pytest -q` (özellikle test_adapter_end_to_end / test_adapter_errors /
  test_ingest_endpoint) yeşil. Davranış değişikliği YOK.
- [ ] Commit: `refactor(ingest): adapt_dir_to_contract ingest katmanina (api -> ingest yonu)`

## Task 2: Saf kontroller + birim testleri (TDD)

**Files:** `backend/tests/test_pilot_doctor.py` (önce), `backend/tools/pilot_doctor.py`

- [ ] Testleri yaz (kırmızı): geçerli/geçersiz hat dict; oee 0 → FAIL, 0.6 & 1.0 → PASS;
  sufficiency 0.59/0.6 sınırı; `rejection_rate({}, 0) is None` + boş LoadReport → FAIL
  (ZeroDivision yok); 6/100 FAIL, 5/100 PASS; 60 ret (> max_errors) → oran 60'tan;
  SKIP nötr / herhangi FAIL → NO-GO; `format_report` ASCII.
- [ ] `pilot_doctor.py`: `CheckResult` (frozen dataclass: name/status/detail/value/threshold),
  `DoctorReport` (checks/ingest/oee + `go()` + `to_dict()`), `PASS/FAIL/SKIP` sabitleri,
  `check_line/check_oee/check_sufficiency/rejection_rate/check_rejection/check_ingest/decide/
  format_report` saf fonksiyonları (yeşil).
- [ ] Commit: `feat(doctor): saf kontrol cekirdegi + birim testleri`

## Task 3: `run_doctor` orkestrasyonu + e2e testleri

**Files:** `backend/tests/test_pilot_doctor_e2e.py` (önce), `backend/tools/pilot_doctor.py`

- [ ] Testler (kırmızı): baseline GO; baseline `skipped == ["ground_truth.csv"]`;
  dirty/type_corruption NO-GO; bottleneck'siz tmp hat YAML → line FAIL + oee/sufficiency SKIP +
  ingest yine koştu; parse edilemez YAML → NO-GO (traceback yok); boş dizin → NO-GO (çökme yok);
  `monkeypatch.chdir(tmp_path)` → cwd'de `*.duckdb` YOK.
- [ ] `run_doctor(data_dir, line_path, adapter, min_sufficiency, max_reject) -> DoctorReport`:
  yaml.safe_load güvenli; `TemporaryDirectory(prefix="oee_doctor_", ignore_cleanup_errors=True)`;
  `DuckDBRepository` connect/init_schema + `try/finally: repo.close()`; `load_csv_dir` →
  `fetch_events()`/`fetch_production()` (argümansız) → `load_line_definition` (defans:
  `except (KeyError, TypeError, ValueError)`) → compute_oee + data_sufficiency.
- [ ] Commit: `feat(doctor): run_doctor orkestrasyonu + e2e fixtures testleri`

## Task 4: Adaptör yolu

**Files:** `backend/tests/test_pilot_doctor_e2e.py`, `backend/tools/pilot_doctor.py`

- [ ] Testler (kırmızı): `raw/ --adapter generic_plant --min-sufficiency 0` → adapter PASS +
  events kabul > 0; override'sız → NO-GO (sufficiency ~0.4 < 0.6).
- [ ] Profil çözümü: `Path(__file__).resolve().parents[2] / "config" / "adapters" / f"{name}.yaml"`;
  `adapt_dir_to_contract(data_dir, mapping, tmp/"adapted")`; `AdapterError` → adapter FAIL +
  kalan kontroller SKIP.
- [ ] Commit: `feat(doctor): --adapter yolu (ham export -> sozlesme -> ingest)`

## Task 5: CLI `main` + JSON + exit kodları

**Files:** `backend/tests/test_pilot_doctor_e2e.py`, `backend/tools/pilot_doctor.py`

- [ ] Testler (kırmızı): `main([baseline]) == 0`; dirty == 1; `--max-reject 0.5` → 0;
  `--min-sufficiency 1.01` → 1; olmayan data_dir → 2; bilinmeyen `--adapter` → 2;
  `--json` şekli (go/exit_code/checks[6]/thresholds/ingest/oee; go ↔ exit tutarlı; capsys).
- [ ] argparse: `data_dir` pozisyonel; `--line` (vars. `<repo_root>/config/line_default.yaml`,
  `__file__` tabanlı — cwd'den bağımsız); `--adapter`; `--min-sufficiency 0.6`;
  `--max-reject 0.05`; `--max-errors 5`; `--json`. `main(argv) -> int` +
  `if __name__ == "__main__": sys.exit(main())`.
- [ ] İnsan-okur format: başlık + hizalı `[PASS|FAIL|SKIP] ad  detay` satırları + FAIL altına
  girintili ilk `--max-errors` mesaj + `SONUC: GO|NO-GO`. Kutu-çizim karakteri YOK.
  `--json`: `json.dumps(rep.to_dict())` (ensure_ascii varsayılan).
- [ ] Commit: `feat(doctor): CLI main + ASCII rapor + --json + exit kodlari`

## Task 6: Dokümanlar + Makefile

**Files:** `docs/pilot-kit/04-pilot-runbook.md`, `docs/pilot-kit/README.md`, `docs/STATUS.md`, `Makefile`

- [ ] Runbook Faz 1: kapı artık otomatik — `cd backend && python -m tools.pilot_doctor
  <veri-dizini> --adapter <profil>` (exit 0 = GO); eşik notu (doctor 0.6/0.05; confidence.yaml
  0.5 = pano rozeti, ayrı); Faz 0 0.1'e "doctor da koşar" işareti; "gerçek Faz-1 örneği tam
  vardiya olmalı (13 satırlık örnek değil)" notu.
- [ ] pilot-kit README: B "Yakında gelecekler" → mevcut (çağrı tek-satırı).
- [ ] STATUS.md: tamamlananlar tablosuna **Pilot B** satırı; "sırada C"; test sayıları güncelle.
- [ ] Makefile: `doctor` hedefi (`DATA ?= tests/fixtures/baseline`), `.PHONY` güncelle; `ci`'a EKLEME.
- [ ] Commit: `docs(doctor): runbook otomasyonu + README + STATUS + make doctor`

## Task 7: Doğrulama + PR

- [ ] `cd backend && python -m pytest -q` (186 + ~24 yeni yeşil); `python -m ruff check .` temiz.
- [ ] Elle duman: baseline → GO/0; dirty → NO-GO/1; `--json | python -m json.tool` parse;
  `make doctor`; PowerShell'de UnicodeEncodeError yok.
- [ ] Push + PR (`feat/pilot-doctor-cli` → main); CI yeşil; merge kullanıcı onayıyla.
