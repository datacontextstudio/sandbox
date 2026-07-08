FROM python:3.14.6-slim-bookworm
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY fake_refund/ ./fake_refund/

EXPOSE 8010
CMD ["python", "-m", "fake_refund.main"]
