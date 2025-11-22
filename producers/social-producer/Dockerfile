FROM python:3.11-slim

WORKDIR /app

# Copy shared libraries
COPY ./shared /app/shared

# Copy producer code
COPY ./producers/social-producer/requirements.txt .
COPY ./producers/social-producer/main.py .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt -r /app/shared/requirements.txt

# Run the producer
CMD ["python", "main.py"]
