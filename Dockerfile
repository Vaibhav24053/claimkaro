FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

COPY agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agent/ ./agent/
COPY frontend/ ./frontend/
COPY sample_bill.png .
COPY .env .

WORKDIR /app/agent

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
