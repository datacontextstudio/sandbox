FROM python:3.14.6-slim-bookworm

WORKDIR /app

# system deps for docling (poppler for PDF, libmagic for mime detection)
RUN apt-get update && apt-get install -y --no-install-recommends \
  poppler-utils \
  libmagic1 \
  tesseract-ocr \
  libgl1 \
  libglib2.0-0 \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download docling/HF models into the image so runtime works fully offline.
# HF_HOME pins the cache to a stable path that survives container restarts.
# We must actually *convert* a PDF during build — DocumentConverter() is lazy
# and only downloads pipeline models on the first convert() call per format.
ENV HF_HOME=/opt/hf-models
COPY warmup/ /tmp/warmup/
RUN python /tmp/warmup/download_models.py && rm -rf /tmp/warmup

COPY worker/ ./worker/

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz')"

CMD ["python", "-m", "worker.main"]
