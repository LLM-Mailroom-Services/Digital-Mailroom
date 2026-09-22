# Optional React operator desk — STANDALONE image.
#
# NOTE: production does NOT use this image. The operator compose builds the
# `operator` target of the root Dockerfile, which bakes the same Vite build
# into the backend image and serves it at /desk behind the single nginx front
# door. This image exists only for isolating the React UI (e.g. `docker run`
# against a backend reachable as `mailroom:8001` on a shared network).
FROM node:22-alpine AS builder
ENV NODE_ENV=production
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
# Vite production base is /desk/ — serve the SPA under /desk, not at /.
COPY --from=builder /app/dist /usr/share/nginx/html/desk
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]