# Dağıtım (Deployment) — Tek Müşteri Kurulumu

Pano bir müşteriye link ile açılacaksa gereken kurulum. Tek Docker imajı (backend +
React SPA) herhangi bir konteyner platformunda çalışır; referans hedef **Render Blueprint**'tir.

## Mimari

Tek imaj, çok aşamalı `backend/Dockerfile`:
1. **Stage 1** (`node:20-slim`): `frontend/` Vite build → statik SPA.
2. **Stage 2** (`python:3.11-slim`): FastAPI backend; SPA'yı `app/frontend_dist`'ten `/`'ta sunar.

`CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}` (shell form → `$PORT` Render/Railway'de genişler). `EXPOSE 8000`.

## Render (önerilen) — Blueprint akışı

`render.yaml` repo kökündeki tek web servisini tanımlar (runtime: docker, region: frankfurt, plan: free, `healthCheckPath: /health`, `autoDeploy: true`).

1. Render → **New → Blueprint** → repoyu seç → **Apply**.
2. Build (Docker multi-stage) + deploy; `/health` yeşil olunca canlı.
3. `main`'e her push otomatik yeniden dağıtır (`autoDeploy: true`).
4. Şifreyi Render Dashboard'dan gir (aşağıdaki `OEE_AUTH_PASS`).

Aynı imaj **Railway / Fly.io**'da da çalışır (`$PORT` desteği var).

## Ortam değişkenleri (env)

| Değişken | Zorunlu | Varsayılan | Açıklama |
|----------|---------|------------|----------|
| `OEE_AUTH_PASS` | erişim için evet | (boş = auth KAPALI) | Pano giriş şifresi. Tanımlıysa pano giriş arkasına alınır; `/health` daima public. |
| `OEE_AUTH_USER` | hayır | `admin` | Giriş kullanıcı adı. |
| `OEE_AUTH_SECRET` | hayır | (üretilir) | İmzalı çerez HMAC anahtarı. Render'da `generateValue: true`. |
| `SAMPLE_DATA_DIR` | hayır | — | Verilirse açılışta otomatik ingest (demo). Render: `/app/tests/fixtures/scenarios/baseline`. |
| `OEE_DUCKDB_PATH` | hayır | `oee.duckdb` | DuckDB dosya yolu (aşağıdaki kalıcılık notuna bakın). |
| `OEE_LINE_CONFIG` / `OEE_COST_CONFIG` / `OEE_RECOMMEND_CONFIG` / `OEE_SCENARIO_CONFIG` | hayır | `/app/config/*.yaml` | Config YAML yolları (Dockerfile'da sabitlenir). |
| `OEE_LOG_LEVEL` | hayır | `INFO` | Loglama seviyesi (`DEBUG`/`INFO`/`WARNING`). İstek logları `oee.request`, ingest `oee.ingest`. |
| `PORT` | platform verir | `8000` | Dinlenen port (Render/Railway enjekte eder). |

## Erişim (auth) ve HTTPS

- **Auth:** form-tabanlı giriş (`app/auth.py`); yalnız `OEE_AUTH_PASS` tanımlıysa aktif. İmzalı çerez (HMAC). Korumalı uçlar token'sız → HTML için `/login`'e 303, API için 401. `/login`, `/logout`, `/health` daima public.
- **HTTPS:** Render/Railway/Fly TLS'i otomatik sonlandırır (özel domain dahil). Giriş çerezi proxy `x-forwarded-proto: https` ise `secure` işaretlenir. Üretimde mutlaka HTTPS arkasında çalıştırın (şifre düz HTTP'de açık gider).

## Loglama ve gözlemlenebilirlik (H9)

- Her istek `oee.request` logger'ında `method path status duration_ms` ile loglanır.
- Her ingest `oee.ingest`'te `accepted/rejected/skipped` özetiyle loglanır.
- Seviye `OEE_LOG_LEVEL` ile ayarlanır; platform log akışından (Render Logs) izlenir.

## DuckDB kalıcılık uyarısı

Render free imajının dosya sistemi **ephemeral**'dır: yeniden dağıtım/restart'ta `OEE_DUCKDB_PATH` sıfırlanır. Bu yüzden `SAMPLE_DATA_DIR` ile açılışta baseline yeniden ingest edilir (demo için yeterli). Kalıcı veri gerekiyorsa: kalıcı disk (Render Disk) bağlayın ya da DuckDB→Postgres geçişi yapın (iş mantığı yalnız `Repository` arayüzüne bağlı; geçiş tek dosyada izole).

## Sağlık ve doğrulama

- `GET /health` → `{"status":"ok"}` (auth'tan muaf; platform health-check'i bunu kullanır).
- Dağıtım sonrası: panoyu açın, giriş yapın (auth açıksa), bir senaryo seçin → KPI/Pareto/öneriler görünmeli.
- Yerel doğrulama: `docker compose up --build` → `http://localhost:8000`.
