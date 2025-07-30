FROM python:3.11-slim AS base

ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1

WORKDIR /app

FROM base AS builder

ENV PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=2.1.3

RUN pip install "poetry==$POETRY_VERSION"

COPY memos-public-proxy .
RUN poetry config virtualenvs.in-project true && \
    poetry install --only=main --no-root && \
    poetry build

FROM base AS final

ENV MEMOS_PROTOCOL=http
ENV MEMOS_HOST=memos
ENV MEMOS_LOG_LEVEL=error

COPY --from=builder /app/.venv ./.venv
COPY --from=builder /app/dist .
COPY docker-entrypoint.sh .

RUN ./.venv/bin/pip install *.whl
CMD ["./docker-entrypoint.sh"]
