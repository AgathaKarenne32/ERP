# syntax=docker/dockerfile:1

# ---- deps: install node_modules once (cached) ----
FROM node:22-slim AS deps
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci

# ---- dev: hot-reloading `ng serve` used by the default docker-compose ----
FROM deps AS dev
COPY . .
EXPOSE 4200
# --host 0.0.0.0 so the dev server is reachable from outside the container;
# --poll makes file watching work reliably on mounted volumes.
CMD ["npx", "ng", "serve", "--host", "0.0.0.0", "--poll", "1000"]

# ---- build: production Angular bundle ----
FROM deps AS build
COPY . .
RUN npx ng build --configuration production

# ---- prod: static bundle served by Nginx (used by docker-compose.prod.yml) ----
FROM nginx:1.27-alpine AS prod
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist/frontend/browser /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
