FROM node:20-alpine as builder

WORKDIR /app
ENV NODE_ENV=production

COPY package.json package-lock.json ./
# install prod deps only, be quiet to reduce logs
RUN npm ci --silent --no-audit --prefer-offline

COPY . .
RUN npm run build

FROM nginx:alpine

# Copy built assets and nginx config
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Ensure nginx serves files as non-root inside container (default user in nginx image is nginx)
EXPOSE 3000

# Healthcheck left to orchestration (docker-compose / Kubernetes)
CMD ["nginx", "-g", "daemon off;"]
