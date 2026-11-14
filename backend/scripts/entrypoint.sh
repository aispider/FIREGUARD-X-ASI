#!/bin/sh
# Backend entrypoint: wait for the database, migrate, seed, then start the server.
# The worker container overrides CMD and skips bootstrap (it waits for the backend healthcheck).
set -e
if [ "$1" = "uvicorn" ]; then
  python -m app.bootstrap
fi
exec "$@"
