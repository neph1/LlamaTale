FROM python:3.10-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    XDG_DATA_HOME=/data

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN useradd --create-home --uid 1000 tale \
    && mkdir -p /data \
    && chown -R tale:tale /data /app
USER tale

VOLUME ["/data"]

EXPOSE 8180 8765

ENV LLAMATALE_HOST=0.0.0.0 \
    LLAMATALE_PORT=8180

HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen(urllib.request.Request('http://127.0.0.1:8180/', method='HEAD'), timeout=4)" || exit 1

ENTRYPOINT ["python", "-m", "tale.main"]
CMD ["-g", "/app/stories/prancingllama", "-m", "mud"]
