# Build the browser app, then ship it with FastAPI so the reviewer has one origin and one URL.
FROM node:24.15.0-alpine AS frontend-build
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM python:3.11-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STORAGE_DIR=/tmp/township-private

RUN apt-get update \
    && apt-get install -y --no-install-recommends libgomp1 ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system township \
    && useradd --system --gid township --create-home township

WORKDIR /app
COPY requirements-runtime.txt ./requirements-runtime.txt
RUN python -m pip install --no-cache-dir --upgrade pip \
    && python -m pip install --no-cache-dir -r requirements-runtime.txt

COPY --chown=township:township . ./
COPY --from=frontend-build --chown=township:township /build/frontend/dist ./frontend/dist
RUN chmod +x /app/entrypoint.sh
RUN mkdir -p /tmp/township-private && chown -R township:township /tmp/township-private

USER township
EXPOSE 8000
ENTRYPOINT ["/bin/sh", "/app/entrypoint.sh"]
