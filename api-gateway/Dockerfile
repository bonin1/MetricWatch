FROM python:3.11-slim AS builder

WORKDIR /app
COPY ./shared/requirements.txt /app/shared/requirements.txt
COPY ./api-gateway/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt -r /app/shared/requirements.txt

FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /install /usr/local
COPY ./shared /app/shared
COPY ./api-gateway/main.py .

EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=10s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["python", "main.py"]
