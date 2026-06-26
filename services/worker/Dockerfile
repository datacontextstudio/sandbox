FROM python:3.12.18-slim

WORKDIR /app

# system deps for docling (poppler for PDF, libmagic for mime detection)
RUN apt-get update && apt-get install -y --no-install-recommends \
  poppler-utils \
  libmagic1 \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY worker/ ./worker/

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz')"

CMD ["python", "-m", "worker.main"]
