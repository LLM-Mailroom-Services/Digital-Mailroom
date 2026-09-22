# Optional React operator desk — STANDALONE / manual use only.
# Production compose (operator_desk/docker-compose.yml) does NOT use this
# image: the desk is baked into the `operator` target of the root Dockerfile
# and served at /desk via nginx → mailroom. This image is for local
# evaluation: docker build -t mailroom-ui ./ui && docker run -p 5174:80 mailroom-ui
FROM node:22-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci --no-audit --no-fund || npm install --no-audit --no-fund
COPY . .
# Standalone container serves the SPA at / (nginx root); the baked operator
# desk inside the root image keeps the /desk/ base from vite.config.ts.
ENV VITE_BASE=/
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
