# Frontend image for the Study-Group RAG Tutor (build context: ./frontend).
# Stage 1 builds the static bundle; stage 2 serves it with nginx, which also
# proxies /api to the backend container — the same job vercel.json does in
# production, so the built app needs no VITE_API_URL.
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:1.27-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
