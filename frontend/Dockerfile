FROM node:20-alpine as builder

WORKDIR /app
# Install dev deps in builder so tools like tsc are available
ENV NODE_ENV=development

COPY package.json package-lock.json ./
# install dev deps as well, be quiet to reduce logs
RUN npm ci --include=dev --silent --no-audit --prefer-offline

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
