# Anime Recommender — README

Aplicación demo con **Frontend** (Next.js + Tailwind + shadcn/ui) y **Backend** (Django REST + pandas) orquestada con **Docker Compose**.

---

## Requisitos

- **Docker Desktop** (macOS/Windows) o **Docker Engine** (Linux)
  - Verifica que el daemon está activo:
    ```bash
    docker ps
    ```
- Puertos libres: **3000** (frontend) y **8000** (backend).

> No necesitas Node ni Python instalados si usas Docker.

---

## Estructura del repositorio

```
anime_recommender/
├─ front/                  # Next.js (modo dev)
│  ├─ Dockerfile
│  └─ (código del front)
├─ back/                   # Django + DRF + pandas (modo dev)
│  ├─ Dockerfile
│  ├─ requirements.txt
│  └─ (código del back)
├─ docker-compose.yml      # orquesta front + back
└─ utils/                  # (opcional) data.json mock para el front
```

---

## Variables de entorno (opcional)

- **Frontend** (`front/.env.local`), solo si llamas directo al backend desde el navegador:
  ```env
  NEXT_PUBLIC_API_URL=http://backend:8000
  ```

- **Backend** (`back/.env`) si necesitas configurar algo adicional (DB externa, etc.).

En `back/recomendar/settings.py` para desarrollo:
```python
ALLOWED_HOSTS = ["*", "localhost", "127.0.0.1"]
INSTALLED_APPS += ["corsheaders", "rest_framework"]
MIDDLEWARE = ["corsheaders.middleware.CorsMiddleware", *MIDDLEWARE]
CORS_ALLOWED_ORIGINS = ["http://localhost:3000","http://127.0.0.1:3000"]
```

---

## 🚀 Levantar TODO con Docker

Desde la **raíz del repo** (donde está `docker-compose.yml`):

```bash
docker compose up --build
```

- **Backend**: http://localhost:8000
- **Frontend**: http://localhost:3000  
  (arranca cuando el backend esté "healthy").

En background:
```bash
docker compose up -d --build
docker compose logs -f
```

Detener:
```bash
docker compose down
```

---

## Archivos clave

### `back/requirements.txt`
```txt
Django==5.1.1
djangorestframework==3.15.2
django-cors-headers==4.4.0
pandas==2.2.3
numpy==2.1.2
gunicorn==21.2.0
# psycopg2-binary==2.9.9   # (opcional) si usas PostgreSQL
# python-dotenv==1.0.1     # (opcional) .env
```

### `back/Dockerfile` (dev)
```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl ca-certificates && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["sh","-c","python manage.py migrate --noinput && (python manage.py collectstatic --noinput || true) && python manage.py runserver 0.0.0.0:8000"]
```

### `front/Dockerfile` (dev)
```dockerfile
FROM node:20-alpine
WORKDIR /app
ENV NODE_ENV=development NEXT_TELEMETRY_DISABLED=1
COPY package*.json ./
RUN npm ci
COPY . .
EXPOSE 3000
CMD ["sh","-c","npm run dev -- -p 3000 -H 0.0.0.0"]
```

### `docker-compose.yml` (raíz)
```yaml
services:
  backend:
    build:
      context: ./back
    container_name: backend
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1
    volumes:
      - ./back:/app
      - ./back/db.sqlite3:/app/db.sqlite3
    healthcheck:
      test: ["CMD-SHELL", "curl -sSf http://localhost:8000/ > /dev/null || curl -sSf http://localhost:8000/getrecomenders > /dev/null"]
      interval: 10s
      timeout: 3s
      retries: 8

  frontend:
    build:
      context: ./front
    container_name: frontend
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=development
      - NEXT_PUBLIC_API_URL=http://backend:8000
    command: npm run dev -- -p 3000 -H 0.0.0.0
    volumes:
      - ./front:/app
      - /app/node_modules
    depends_on:
      backend:
        condition: service_healthy
```

---

## Desarrollo local sin Docker (opcional)

### Backend
```bash
cd back
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000
```

### Frontend
```bash
cd front
npm i
npm run dev
# abrir http://localhost:3000
```