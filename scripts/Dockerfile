FROM python:3.11-slim

WORKDIR /app
COPY scripts/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY scripts/seed_data.py .

CMD ["python", "seed_data.py"]
