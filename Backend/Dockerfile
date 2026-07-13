FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias del sistema requeridas por mysql-connector si aplica
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copiar requerimientos e instalar dependencias de Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar todo el contenido de la carpeta Backend actual
COPY . .

EXPOSE 5000

CMD ["python", "app.py"]