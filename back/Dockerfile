# back/Dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Paquetes básicos (pandas/numpy usan ruedas manylinux; build-essential por si acaso)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

# Dependencias Python
COPY requirements.txt .
RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

# Código
COPY . .

EXPOSE 8000

# Migraciones + runserver (dev). Sin collectstatic para evitar STATIC_ROOT.
CMD ["sh","-c","python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000"]
