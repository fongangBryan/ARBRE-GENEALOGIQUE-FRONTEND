FROM node:20-alpine

WORKDIR /app

# Installer les dépendances en couche cachée séparée
COPY package*.json ./
RUN npm ci --silent

EXPOSE 4200

# --host 0.0.0.0  → expose hors du conteneur
# --poll 1000     → hot-reload fiable sur volumes Docker/Windows
CMD ["npx", "ng", "serve", "--host", "0.0.0.0", "--poll", "1000"]
