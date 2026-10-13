# ── Production image ──────────────────────────────────────────────────────────
# Stage 1: build the React SPA
# Stage 2: serve the compiled /dist with Nginx
#
# This image is used by CI/CD → ACR → AKS.
# Node and source files are not present in the final image.
#
# API configuration for production:
#   Set VITE_API_BASE_URL="" (empty string) at build time so the frontend uses
#   relative URLs (/api/v1/...). Nginx then proxies /api/ to the backend service.
#   This avoids hardcoding any public backend hostname in the JS bundle.

# ── Stage 1: build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

# Build the SPA. VITE_API_BASE_URL can be overridden at build time via
# --build-arg if needed (e.g. for a dedicated staging backend).
ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build

# ── Stage 2: serve ────────────────────────────────────────────────────────────
FROM nginx:1.27-alpine AS runtime

# Remove the default Nginx site
RUN rm -rf /usr/share/nginx/html/*

# Copy compiled SPA
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx config
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
