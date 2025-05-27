# --------------------
# Build Svelte frontend
# --------------------
FROM node:23 as frontend-builder
WORKDIR /app/frontend

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build


# --------------------
# Unified dev/prod container with nginx and Vite
# --------------------
FROM alpine:latest as frontend-server

# Install Node and nginx
RUN apk add --no-cache nodejs npm nginx

# Create working directory
WORKDIR /app/frontend

# Copy app and build artifacts
COPY --from=frontend-builder /app/frontend /app/frontend

# Copy custom nginx config
ARG NGINX_CONF=nginx.conf
COPY ${NGINX_CONF} /etc/nginx/nginx.conf

# Copy startup script
COPY start.sh /start.sh
RUN chmod +x /start.sh

# Set build arg for deployment mode
ARG DEPLOYMENT=production
ENV DEPLOYMENT=${DEPLOYMENT}

EXPOSE 8003
CMD ["/start.sh"]
