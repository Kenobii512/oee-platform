# Çok aşamalı imaj: Stage 1 React/Vite build, Stage 2 Python backend + SPA servisi.
# Build context = repo kökü (oee-platform/); docker-compose `dockerfile: backend/Dockerfile`.

# --- Stage 1: frontend build ---
FROM node:20-slim AS frontend
WORKDIR /fe
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- Stage 2: backend + SPA ---
FROM python:3.11-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/app ./app
COPY config ./config
# Demo senaryo verileri (G8) — aktivasyon imaj içinden çalışsın (firewall: ground_truth ingest edilmez).
COPY backend/tests/fixtures/scenarios ./tests/fixtures/scenarios
# React build çıktısı: kök '/' bunu SPA olarak sunar (Jinja '/legacy'de).
COPY --from=frontend /fe/dist ./app/frontend_dist
# Config yolları imaj içine sabitlenir (volume mount'a bağımlı değil).
ENV OEE_LINE_CONFIG=/app/config/line_default.yaml \
    OEE_COST_CONFIG=/app/config/costs.yaml \
    OEE_RECOMMEND_CONFIG=/app/config/recommend.yaml \
    OEE_SCENARIO_CONFIG=/app/config/scenarios.yaml
EXPOSE 8000
# Bulut platformları (Render/Railway) dinlenecek portu $PORT ile enjekte eder; yoksa 8000.
# Shell formu kasıtlı: ${PORT} genişlesin diye (exec/JSON formu env genişletmez).
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
