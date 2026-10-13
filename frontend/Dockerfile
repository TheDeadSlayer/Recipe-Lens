# ── Production image ──────────────────────────────────────────────────────────
# Stage 1: build the React SPA with Node.
# Stage 2: serve the compiled /dist with Nginx (non-root, port 8080).
#
# Node and all source files are absent from the final image.
#
# /api/ routing strategy
# ──────────────────────
# The frontend JavaScript uses relative /api/v1/... URLs.
# Nginx does NOT proxy /api/ — that is the responsibility of:
#   • AKS: the Kubernetes Ingress (routes /api/* → backend Service)
#   • Local production smoke test: the Caddy gateway in docker-compose.prod.yml
# This keeps the image environment-agnostic; no backend URL is ever baked in.
#
# VITE_API_BASE_URL
# ─────────────────
# Left as "" (empty) so that Vite emits relative /api/... fetch calls.
# This value must NOT be overridden to a full URL in CI for production builds
# — doing so would bake a host-specific URL into the JS bundle.
# For a dedicated staging backend override, pass --build-arg VITE_API_BASE_URL=...
# only when building a staging-specific image.

# ── Stage 1: build ────────────────────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json* ./
RUN npm ci

COPY . .

ARG VITE_API_BASE_URL=""
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}

RUN npm run build

# ── Stage 2: serve ────────────────────────────────────────────────────────────
# nginxinc/nginx-unprivileged runs as uid 101 (non-root) out of the box
# and listens on port 8080 — no capability grants required.
# Kubernetes Services can still expose port 80 by mapping targetPort: 8080.
FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime

# Remove the default Nginx site config.
RUN rm -f /etc/nginx/conf.d/default.conf

# Copy compiled SPA assets.
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy the custom Nginx site config.
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 8080

CMD ["nginx", "-g", "daemon off;"]
