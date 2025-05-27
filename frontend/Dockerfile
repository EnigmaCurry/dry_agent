# --------------------
# Build svelte frontend stage
# --------------------
FROM docker.io/library/node:23 as frontend-builder
WORKDIR /app/frontend

# Copy only package files first to leverage Docker cache.
COPY package*.json ./
RUN npm install

# Copy the rest of the Svelte source code.
COPY . .

# Build static files (even in dev mode, this ensures consistent output)
RUN npm run build

# --------------------
# Dev server for development
# --------------------
FROM docker.io/library/node:23 as dev-server
WORKDIR /app/frontend
COPY --from=frontend-builder /app/frontend ./

# Expose port Vite will use
EXPOSE 5173

# Use Vite's development server
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "8003"]

# --------------------
# Production server using nginx
# --------------------
FROM docker.io/library/nginx:stable-alpine as prod-server
COPY --from=frontend-builder /app/frontend/build /usr/share/nginx/html

# Optional: override default nginx.conf if needed
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 8003
CMD ["nginx", "-g", "daemon off;"]
