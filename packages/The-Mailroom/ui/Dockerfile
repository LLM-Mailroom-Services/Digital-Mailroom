# Optional standalone React operator desk — for UI development against a
# running visualizer. NOT the production path: operator_desk/Dockerfile
# bakes ui/dist into the visualizer image and nginx serves it at /desk.
#
#   docker build -t mailroom-ui ui/
#   docker run --rm -p 5174:80 --add-host mailroom:host-gateway mailroom-ui
#   # → http://localhost:5174/desk/  (proxies /api /v1 /ws to mailroom:8001)
FROM node:22-alpine AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . .
RUN NODE_ENV=production npm run build

FROM nginx:alpine
COPY --from=builder /app/dist /usr/share/nginx/html/desk
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
