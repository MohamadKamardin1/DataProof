# Stage 1: Build
FROM node:20-alpine AS builder

WORKDIR /app
COPY package*.json /app/
RUN npm ci
COPY . /app/
RUN npm run build

# Stage 2: Serve via nginx
FROM nginx:alpine

COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget -qO- http://localhost:80/ || exit 1
