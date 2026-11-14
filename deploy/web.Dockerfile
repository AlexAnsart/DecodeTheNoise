# The web image: the front end built once, then served as static files.
# Official images come from Google's mirror of Docker Hub, which rate-limits the shared runners.
FROM mirror.gcr.io/library/node:22-alpine AS build
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend ./
RUN npm run build

FROM mirror.gcr.io/library/nginx:1.27-alpine
COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
