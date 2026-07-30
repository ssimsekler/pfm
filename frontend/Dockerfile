# PFM frontend (React + Vite + UI5 Web Components). Fleshed out in Phase 8.
FROM node:20-alpine AS build

WORKDIR /app

ARG VITE_API_BASE_URL
ARG VITE_KEYCLOAK_URL
ARG VITE_KEYCLOAK_REALM
ARG VITE_KEYCLOAK_CLIENT_ID

COPY package.json ./
RUN npm install --legacy-peer-deps

COPY . .
RUN npm run build

# --- Serve static build via nginx ---
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]