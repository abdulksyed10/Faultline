FROM node:22-bookworm-slim AS frontend
WORKDIR /build
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 FAULTLINE_DATA_DIR=/data FAULTLINE_FRONTEND_DIR=/app/frontend/dist
WORKDIR /app
COPY pyproject.toml requirements.lock ./
COPY backend/ ./backend/
RUN pip install --no-cache-dir -r requirements.lock && pip install --no-cache-dir --no-deps . && useradd --create-home --uid 10001 lab && mkdir /data && chown lab:lab /data
COPY --from=frontend /build/dist ./frontend/dist/
USER lab
EXPOSE 8000
VOLUME ["/data"]
HEALTHCHECK --start-period=45s --interval=30s --timeout=5s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health',timeout=3)"
CMD ["python", "-m", "faultline", "--host", "0.0.0.0", "--port", "8000"]
