FROM node:20-alpine

WORKDIR /app
ENV NODE_ENV=development
ENV NEXT_TELEMETRY_DISABLED=1

# instala deps
COPY package*.json ./
RUN npm ci

# copia código
COPY . .

EXPOSE 3000

# Next dev escuchando en 0.0.0.0:3000
CMD ["sh", "-c", "npm run dev -- -p 3000 -H 0.0.0.0"]
