FROM python:3.11-slim AS builder

ENV PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PYTHONUNBUFFERED=1 \
    PIP_DEFAULT_TIMEOUT=100 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    POETRY_VERSION=2.1.3

WORKDIR /app

RUN pip install "poetry==$POETRY_VERSION"

COPY memos-public-proxy .
RUN poetry config virtualenvs.in-project true && \
    poetry install --only=main --no-root && \
    poetry build && \
    ./.venv/bin/pip install ./dist/*.whl && \
    ln -sf /usr/bin/python /app/.venv/bin/python

FROM gcr.io/distroless/python3

ENV MEMOS_HOST=http://memos:5230
ENV MEMOS_LOG_LEVEL=error

COPY --from=builder /app/.venv /venv

EXPOSE 5000

ENTRYPOINT ["/venv/bin/python", "-m", "gunicorn", "--bind", "0.0.0.0:5000", "--forwarded-allow-ips=*", "-w", "4", "--log-level", "$MEMOS_LOG_LEVEL", "--capture-output", "memos_public_proxy.app:app"]
CMD []
