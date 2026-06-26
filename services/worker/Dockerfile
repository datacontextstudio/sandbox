FROM python:3.14.6-slim-bookworm

WORKDIR /app

# system deps for docling (poppler for PDF, libmagic for mime detection)
RUN apt-get update && apt-get install -y --no-install-recommends \
  poppler-utils \
  libmagic1 \
  tesseract-ocr \
  && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -c "from docling.document_converter import DocumentConverter; DocumentConverter()"

COPY worker/ ./worker/

EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8080/healthz')"

CMD ["python", "-m", "worker.main"]
