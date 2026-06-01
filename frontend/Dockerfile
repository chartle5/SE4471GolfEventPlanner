# Golf Planner — Vite/React frontend
# Multi-stage: build static assets with Node, then serve them with nginx.

# ---- Build stage ----
FROM node:20-alpine AS build

WORKDIR /app

# IMPORTANT: Vite inlines import.meta.env.VITE_API_URL at BUILD time, not
# runtime. So the backend URL must be supplied here as a build arg. Point it at
# your public API hostname (e.g. https://api.yourdomain.com).
ARG VITE_API_URL=https://api.yourdomain.com
ENV VITE_API_URL=${VITE_API_URL}

# Install deps first (cached unless lockfile changes).
COPY package.json package-lock.json ./
RUN npm ci

# Build the production bundle into /app/dist.
COPY . .
RUN npm run build

# ---- Serve stage ----
FROM nginx:alpine

# SPA-friendly nginx config (history-mode routing falls back to index.html).
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Static build output.
COPY --from=build /app/dist /usr/share/nginx/html

# Serves on port 80 internally.
EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
