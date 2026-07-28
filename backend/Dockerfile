FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

WORKDIR /app

RUN addgroup --system app && adduser --system --ingroup app app

COPY requirements.txt requirements-dev.txt ./

RUN pip install --upgrade pip \
    && pip install -r requirements.txt \
    && python -m playwright install --with-deps chromium \
    && chmod -R a+rX /ms-playwright

COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic

FROM base AS test

COPY tests ./tests
RUN pip install -r requirements-dev.txt

CMD ["python", "-m", "pytest"]

FROM base AS runtime

RUN mkdir -p /app/data/application-documents \
    && chown -R app:app /app/data

USER app

EXPOSE 8080

CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host \"${APP_HOST:-0.0.0.0}\" --port \"${APP_PORT:-8080}\""]
