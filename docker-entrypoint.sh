#!/bin/sh

set -e

. .venv/bin/activate

exec gunicorn --bind 0.0.0.0:5000 --forwarded-allow-ips='*' -w 4 --log-level $MEMOS_LOG_LEVEL --capture-output memos_public_proxy.app:app
