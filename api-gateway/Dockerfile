FROM python:3.11-slim

WORKDIR /app

# Copy shared libraries
COPY ./shared /app/shared

# Copy API gateway code
COPY ./api-gateway/requirements.txt .
COPY ./api-gateway/main.py .

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt -r /app/shared/requirements.txt

# Expose port
EXPOSE 8000

# Run the API gateway
CMD ["python", "main.py"]
