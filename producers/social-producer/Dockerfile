FROM python:3.11-slim AS builder

WORKDIR /app
COPY ./shared/requirements.txt /app/shared/requirements.txt
COPY ./producers/social-producer/requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt -r /app/shared/requirements.txt

FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /install /usr/local
COPY ./shared /app/shared
COPY ./producers/social-producer/main.py .

CMD ["python", "main.py"]
