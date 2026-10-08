# ── Stage 1: build ───────────────────────────────────────────────────────────
# Node is only needed to turn src/ into static files in dist/.
FROM node:22-slim AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY index.html vite.config.js ./
COPY public/ public/
COPY src/ src/

# Baked into the bundle at build time: the browser calls /api/... on the same
# server that served the page, and nginx forwards it to the api container.
ENV VITE_API_BASE=/api
RUN npm run build

# ── Stage 2: serve ───────────────────────────────────────────────────────────
# Only the built files and a web server ship. Node and node_modules stay behind.
FROM nginx:1.29-alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
