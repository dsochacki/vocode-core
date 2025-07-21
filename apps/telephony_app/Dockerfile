FROM python:3.11-slim

WORKDIR /app

# Installiere system packages, darunter git
RUN apt-get update && apt-get install -y git && apt-get clean

# Kopiere requirements und installiere
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Kopiere restliche App
COPY . .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]