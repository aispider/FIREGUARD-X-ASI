FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Run as an unprivileged user. /data is a bind mount from ./data on the host.
RUN useradd --system --uid 10001 --home /app fireguard \
    && mkdir -p /data/raw /data/processed /data/manifests \
    && chown -R fireguard:fireguard /app /data \
    && chmod +x /app/scripts/entrypoint.sh
USER fireguard

EXPOSE 8000
ENTRYPOINT ["/app/scripts/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
