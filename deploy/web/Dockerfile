# ANAC Flight Intelligence v2 — dashboard (Next.js).
# Build from the repository root. The API URL is baked in at build time:
#   docker build -f deploy/web/Dockerfile --build-arg NEXT_PUBLIC_API_URL=https://api.example -t anac-fi-web .
FROM node:22-slim AS build
WORKDIR /app
ARG NEXT_PUBLIC_DATA_SOURCE=api
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_DATA_SOURCE=$NEXT_PUBLIC_DATA_SOURCE \
    NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL \
    NEXT_TELEMETRY_DISABLED=1
RUN test -n "$NEXT_PUBLIC_API_URL" || (echo "NEXT_PUBLIC_API_URL is required" && exit 1)
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM node:22-slim
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000
COPY --from=build /app ./
USER node
EXPOSE 3000
CMD ["sh", "-c", "npx next start -p ${PORT}"]
