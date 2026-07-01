# Pilot Kiti C — Showcase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.
> **Kanonik kayıt:** bu plan zaten `oee-platform/docs/superpowers/plans/` altında.
> **Spec:** `docs/superpowers/specs/2026-07-02-pilot-kiti-C-showcase-design.md`.

**Goal:** (1) `backend/tools/pilot_report.py` — pilot verisinden tek dosyalık HTML
raporu (Faz 3 artefaktı); (2) `docs/showcase/ornek-pilot-raporu.html` — breakdown_storm
fixture'ından commit'li örnek; (3) `docs/showcase/landing.html` + public `GET /tanitim`.

**Tech Stack:** stdlib (argparse, html, xml yok — string şablon), mevcut `app.analytics.*`,
elle yazılmış satır içi SVG, pytest. Harici bağımlılık YOK.

## Global Constraints

- **Import hijyeni:** `tools/pilot_report.py` ASLA `app.api`/`app.main` import etmez.
- **Tek dosya HTML:** harici istek yok (font/CDN/stylesheet); CSS+SVG gömülü. UTF-8.
- **Konsol çıktısı ASCII** (durum mesajları); HTML İÇERİĞİ Türkçe UTF-8 (dosyaya yazılır).
- **Metrik yeniden uygulanmaz:** compute_oee / extract_loss_tree / to_tl /
  generate_recommendations / bucket_oee_series / data_sufficiency aynen çağrılır.
- **Rapor karar VERMEZ:** eşik ihlali ✗ olarak gösterilir; exit 0 (yalnız kullanım
  hatası 2). Doctor'ın işi ayrı.
- **Determinizm:** `--generated-at "2026-07-02 12:00"` verilirse künyede o basılır;
  örnek rapor bu bayrakla üretilir (bayt-eş tekrar üretilebilir).
- Kriter eşikleri 05-basari-kriterleri ile aynı: K1 üst-⅓ + %15, K2 gain>0 + low>0,
  K3 red ≤ %5 + H3 ≥ 0.6. Elle alanlar boş basılır.

---

## Task 1: Veri çekirdeği — `build_report_data` (TDD)

**Files:** `backend/tests/test_pilot_report.py` (önce), `backend/tools/pilot_report.py`

- [ ] Testler (kırmızı): breakdown_storm fixture → dict'te `oee` (0<oee≤1), `losses`
  (TL azalan, en üstte DOWNTIME, her kalemde tl_low/high/kind), `recommendations`
  (total>0, low/high dolu), `trend` (≥1 nokta), `quality` (sufficiency/red oranı/
  event_count/span), `criteria` (k1/k2/k3 auto alanları bool + gerekçe metni);
  boş dizin → bölümler "veri yok" işaretli, çökme yok; adapter yolu (raw fixture).
- [ ] Implementasyon: pilot_doctor'ın temp-DuckDB + adaptör akışı deseni (
  `resolve_profile_path`/`adapt_dir_to_contract`/`line_definition_from_dict` yeniden
  kullan); pipeline: ingest → fetch → compute_oee → extract_loss_tree → to_tl →
  generate_recommendations → bucket_oee_series → data_sufficiency → `_evaluate_criteria`.
  `--from/--to` verilirse fetch pencereli (fetch_events(frm,to) imzası mevcut).
- [ ] Commit: `feat(report): build_report_data veri boru hatti + testler`

## Task 2: SVG + HTML render (TDD)

**Files:** `backend/tests/test_pilot_report.py`, `backend/tools/pilot_report.py`

- [ ] Testler (kırmızı): `render_html(data)` → `<html` içerir; `http://`/`https://`
  `src=`/`link rel=` YOK (kendine yeten); Türkçe başlıklar; kriter tablosunda
  otomatik ✓/✗ + boş elle-alanlar (`____` / ☐); SVG Pareto çubuk sayısı = kayıp
  kalemi sayısı; trend <3 nokta → "yeterli geçmiş yok"; `html.escape` uygulanır
  (kötü niyetli hat adı `<script>` kaçışlanır).
- [ ] Implementasyon: `_svg_pareto(losses)` (yatay çubuk + tl_low–high aralık çizgisi
  + kind rozeti), `_svg_trend(points)` (çizgi + eksen), `render_html(data) -> str`
  (string şablon; gömülü CSS — Foundry Gauge light paleti: bkz. üst dizin DESIGN.md
  token'ları; sade print-uyumlu düzen `@media print` dahil).
- [ ] Commit: `feat(report): satir ici SVG + kendine-yeten HTML render`

## Task 3: CLI `main` + örnek showcase raporu

**Files:** `backend/tools/pilot_report.py`, `docs/showcase/ornek-pilot-raporu.html`

- [ ] Testler (kırmızı): `main([dir, "-o", out]) == 0` + dosya oluşur; olmayan dizin/
  hat/profil → exit 2 (ASCII stderr, doctor deseni); `--generated-at` sabitken iki
  koşu bayt-eş; varsayılan çıktı `pilot-raporu.html` (cwd).
- [ ] argparse: `data_dir`, `--adapter`, `--line` (env-onurlandıran doctor çözümü),
  `--from/--to`, `--bucket day|week` (vars. day), `-o/--out`, `--generated-at`.
- [ ] Örnek üretimi: `python -m tools.pilot_report tests/fixtures/scenarios/breakdown_storm
  --generated-at "2026-07-02 12:00" -o ../docs/showcase/ornek-pilot-raporu.html` →
  commit'le; tarayıcıda elle doğrula.
- [ ] Commit: `feat(report): CLI + ornek showcase raporu (breakdown_storm)`

## Task 4: Landing + `GET /tanitim`

**Files:** `docs/showcase/landing.html`, `backend/app/main.py` (ya da yeni
`app/api/showcase_routes.py`), `backend/app/auth.py` (istisna), `backend/tests/test_tanitim.py`

- [ ] Testler (kırmızı): `GET /tanitim` → 200 + `text/html` + "OEE" içerir;
  `OEE_AUTH_PASS` set'liyken de 200 (public istisna, test_auth deseni); dosya
  kendine yeten (harici src yok).
- [ ] `landing.html`: tek sayfa öz — problem → tek-bakış tablosu → güven mimarisi →
  `ornek-pilot-raporu.html` linki → pilot CTA. Foundry Gauge light gömülü CSS;
  SVG mini-görseller (mini gauge, mini pareto). Ekran görüntüsü YOK.
- [ ] Rota: `FileResponse(repo_root/docs/showcase/landing.html)`; yoksa 404; auth
  istisnalar listesine `/tanitim` (+ örnek rapor dosyasını da `/tanitim/ornek-rapor`
  olarak sun — landing'deki link buna işaret eder, dosya sisteminde göreli link
  de çalışır).
- [ ] Commit: `feat(showcase): landing sayfasi + public /tanitim rotasi`

## Task 5: Dokümanlar + doğrulama + PR

**Files:** `docs/pilot-kit/README.md`, `docs/pilot-kit/04-pilot-runbook.md`, `docs/STATUS.md`

- [ ] README: C "Yakında" → mevcut (rapor komutu + landing yolu). Runbook Faz 3:
  "Pilot raporu artık araçla: `python -m tools.pilot_report <dizin> -o rapor.html`";
  şablon notu güncelle (L104). STATUS: Pilot C satırı + "Pilot Kiti A+B+C TAMAM" +
  test sayıları.
- [ ] `pytest -q` tam paket + `ruff check .`; duman: breakdown_storm raporu + landing
  tarayıcıda (Playwright) görsel kontrol; `/tanitim` Docker'sız uvicorn'da.
- [ ] Push + PR (`feat/pilot-kit-showcase` → main); CI yeşil; merge (kullanıcı onayı
  akışına göre); memory güncelle.
