# ─── Build Stage ─────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

# Build-Argumente definieren (Coolify reicht diese durch)
ARG VITE_CLERK_PUBLISHABLE_KEY
ARG VITE_API_BASE_URL

# Diese Argumente als Umgebungsvariablen für den Build-Prozess setzen
ENV VITE_CLERK_PUBLISHABLE_KEY=$VITE_CLERK_PUBLISHABLE_KEY
ENV VITE_API_BASE_URL=$VITE_API_BASE_URL

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

# Produktions-Build (statische Assets)
RUN npm run build

# ─── Runtime Stage ───────────────────────────────────────────
# Nginx serviert die statischen Vue.js-Dateien
FROM nginx:1.27-alpine AS runtime

# Nginx-Konfiguration für Vue Router (history mode)
RUN printf 'server {\n\
    listen 3000;\n\
    root /usr/share/nginx/html;\n\
    index index.html;\n\
\n\
    # Resolver für Docker DNS\n\
    resolver 127.0.0.11 valid=30s;\n\
\n\
    # Vue Router — alle Pfade auf index.html\n\
    location / {\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
\n\
    # API-Proxy → MiroFish Backend\n\
    location /api/ {\n\
        set $upstream_backend backend;\n\
        proxy_pass         http://$upstream_backend:5001/api/;\n\
        proxy_set_header   Host              $host;\n\
        proxy_set_header   X-Real-IP         $remote_addr;\n\
        proxy_set_header   X-Forwarded-For   $proxy_add_x_forwarded_for;\n\
        proxy_set_header   X-Forwarded-Proto $scheme;\n\
        proxy_read_timeout 600s;\n\
    }\n\
\n\
    # Cache für statische Assets\n\
    location ~* \\.(js|css|png|jpg|jpeg|gif|ico|svg|woff2?)$ {\n\
        expires 1y;\n\
        add_header Cache-Control "public, immutable";\n\
    }\n\
}\n' > /etc/nginx/conf.d/default.conf

COPY --from=builder /app/dist /usr/share/nginx/html

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
