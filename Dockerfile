FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY alembic.ini ./
COPY app ./app
COPY alembic ./alembic
COPY tests ./tests

RUN pip install --upgrade pip \
    && pip install .

RUN groupadd --system app \
    && useradd --system --gid app --create-home app \
    && mkdir -p /app/uploads /app/logs \
    && chown -R app:app /app

USER app

EXPOSE 8000

CMD ["uvicorn", "app.web.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
