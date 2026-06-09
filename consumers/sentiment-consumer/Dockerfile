# Build arg: keyword = fast (~30s), transformers = full AI (~10-15 min first build)
ARG SENTIMENT_MODE=keyword

FROM python:3.11-slim AS builder
ARG SENTIMENT_MODE

WORKDIR /app
COPY ./shared/requirements.txt /app/shared/requirements.txt

RUN if [ "$SENTIMENT_MODE" = "transformers" ]; then \
      apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*; \
    fi

COPY ./consumers/sentiment-consumer/requirements.txt ./requirements-ml.txt
COPY ./consumers/sentiment-consumer/requirements-keyword.txt .

RUN if [ "$SENTIMENT_MODE" = "transformers" ]; then \
      pip install --no-cache-dir --prefix=/install \
        torch --index-url https://download.pytorch.org/whl/cpu && \
      pip install --no-cache-dir --prefix=/install \
        -r requirements-ml.txt -r /app/shared/requirements.txt; \
    else \
      pip install --no-cache-dir --prefix=/install \
        -r requirements-keyword.txt -r /app/shared/requirements.txt; \
    fi

FROM python:3.11-slim
ARG SENTIMENT_MODE
ENV SENTIMENT_MODE=$SENTIMENT_MODE

WORKDIR /app
COPY --from=builder /install /usr/local
COPY ./shared /app/shared
COPY ./consumers/sentiment-consumer/main.py .

CMD ["python", "main.py"]
