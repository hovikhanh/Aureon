# Aureon web (Next.js 15, T-513). Build context = repo root:
#   docker build -f apps/web/Dockerfile -t aureon-web:local .
# NEXT_PUBLIC_* are inlined at build time (non-secret only). Secrets (NEXTAUTH_SECRET,
# DEMO_*_PASSWORD) are runtime env from compose `env_file` — never baked into the image.
FROM node:24-slim AS build
ENV PNPM_HOME=/pnpm PATH=/pnpm:$PATH NEXT_TELEMETRY_DISABLED=1
RUN npm install -g pnpm@12.6.0 >/dev/null
WORKDIR /repo

COPY package.json pnpm-lock.yaml pnpm-workspace.yaml ./
COPY apps/web/package.json apps/web/package.json
COPY packages/shared-types/package.json packages/shared-types/package.json
RUN pnpm install --frozen-lockfile --filter @aureon/web...

COPY packages/shared-types packages/shared-types
COPY apps/web apps/web
ARG NEXT_PUBLIC_DEMO_MODE=true
ARG NEXT_PUBLIC_DEMO_REFERENCE_DATE=2026-10-20
ARG NEXT_PUBLIC_DASHBOARD_PERIOD=2026-09
ENV NEXT_PUBLIC_DEMO_MODE=$NEXT_PUBLIC_DEMO_MODE \
    NEXT_PUBLIC_DEMO_REFERENCE_DATE=$NEXT_PUBLIC_DEMO_REFERENCE_DATE \
    NEXT_PUBLIC_DASHBOARD_PERIOD=$NEXT_PUBLIC_DASHBOARD_PERIOD
RUN pnpm --filter @aureon/web build

FROM node:24-slim
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1 PORT=3000 HOSTNAME=0.0.0.0
WORKDIR /repo
COPY --from=build --chown=node:node /repo /repo
USER node
WORKDIR /repo/apps/web
EXPOSE 3000
CMD ["node", "node_modules/next/dist/bin/next", "start", "--port", "3000", "--hostname", "0.0.0.0"]
