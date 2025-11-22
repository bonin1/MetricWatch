FROM python:3.11-slim

WORKDIR /app

# Copy shared libraries
COPY ./shared /app/shared

# Copy consumer code
COPY ./consumers/metrics-consumer/requirements.txt .
COPY ./consumers/metrics-consumer/main.py .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt -r /app/shared/requirements.txt

# Run the consumer
CMD ["python", "main.py"]
