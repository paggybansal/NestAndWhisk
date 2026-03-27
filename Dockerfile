FROM node:22-alpine AS frontend-builder

WORKDIR /frontend

COPY package.json package-lock.json* postcss.config.js tailwind.config.js vite.config.js ./
COPY static_src ./static_src

RUN npm ci && npm run build


FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements /app/requirements
RUN pip install --upgrade pip && pip install -r requirements/prod.txt

COPY . /app
COPY --from=frontend-builder /frontend/static/build /app/static/build

RUN mkdir -p /app/static /app/staticfiles /app/media \
    && chmod +x /app/docker/web/entrypoint.sh /app/docker/celery/worker-entrypoint.sh /app/docker/celery/beat-entrypoint.sh

EXPOSE 8000

CMD ["/app/docker/web/entrypoint.sh"]

