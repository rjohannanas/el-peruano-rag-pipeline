FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema necesarias para psycopg2
RUN apt-get update && apt-get install -y \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar e instalar dependencias de Python primero (para aprovechar cache de Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

# Cloud Run Jobs llama directamente al entrypoint sin TTY
# El exit code determina si el Job es exitoso (0) o fallido (1)
CMD ["python", "main.py"]
