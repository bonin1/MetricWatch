FROM python:3.11-slim

WORKDIR /app

# Install system dependencies for PyTorch
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy shared libraries
COPY ./shared /app/shared

# Copy consumer code
COPY ./consumers/sentiment-consumer/requirements.txt .
COPY ./consumers/sentiment-consumer/main.py .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt -r /app/shared/requirements.txt

# Run the consumer
CMD ["python", "main.py"]
