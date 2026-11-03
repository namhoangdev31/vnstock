FROM oven/bun:1 AS build

WORKDIR /app

COPY package.json bun.lock /app/
COPY packages /app/packages/
COPY frontend /app/frontend/

RUN bun install

WORKDIR /app/packages/dnse
RUN bun run build

WORKDIR /app/frontend
ARG VITE_API_URL=https://api.vidub.ai
ENV VITE_API_URL=${VITE_API_URL}

RUN bun run build

FROM nginx:alpine

COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/frontend/dist /usr/share/nginx/html

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
