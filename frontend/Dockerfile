# ─── Build Stage ─────────────────────────────────────────────
FROM node:20-alpine AS builder

WORKDIR /app

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
    # Vue Router — alle Pfade auf index.html\n\
    location / {\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
\n\
    # API-Proxy → MiroFish Backend\n\
    location /api/ {\n\
        proxy_pass         http://mirofish-backend:5001/api/;\n\
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
