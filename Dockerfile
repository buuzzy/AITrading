FROM node:18-alpine AS base

# Install dependencies only when needed
FROM base AS deps
RUN apk add --no-cache libc6-compat && yarn global add pnpm

WORKDIR /app

# Install dependencies based on the preferred package manager
COPY package.json pnpm-lock.yaml* source.config.ts ./
RUN pnpm i --frozen-lockfile

# Rebuild the source code only when needed
FROM deps AS builder

WORKDIR /app

# Install dependencies based on the preferred package manager
COPY . .

# Declare build arguments for public environment variables
# These must be passed via --build-arg during docker build
# Setting defaults here ensures they work for Cloud Run source-based deployments
ARG NEXT_PUBLIC_AUTH_GOOGLE_ENABLED=true
ARG NEXT_PUBLIC_WEB_URL=https://www.pricetrade.top
ARG NEXT_PUBLIC_SUPABASE_URL=https://umbekzubzgqkuegouhlz.supabase.co
ARG NEXT_PUBLIC_SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InVtYmVrenViemdxa3VlZ291aGx6Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjMwOTAxOTgsImV4cCI6MjA3ODY2NjE5OH0.0nd8xrAgIkKT9xgFg3Fogt5KFgAEgxEbP4agt-SuYWQ
ARG NEXTAUTH_URL=https://www.pricetrade.top

# Make them available as environment variables during build
ENV NEXT_PUBLIC_AUTH_GOOGLE_ENABLED=$NEXT_PUBLIC_AUTH_GOOGLE_ENABLED
ENV NEXT_PUBLIC_WEB_URL=$NEXT_PUBLIC_WEB_URL
ENV NEXT_PUBLIC_SUPABASE_URL=$NEXT_PUBLIC_SUPABASE_URL
ENV NEXT_PUBLIC_SUPABASE_KEY=$NEXT_PUBLIC_SUPABASE_KEY
ENV NEXTAUTH_URL=$NEXTAUTH_URL

RUN pnpm build

# Production image, copy all the files and run next
FROM base AS runner
WORKDIR /app

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs && \
    mkdir .next && \
    chown nextjs:nodejs .next

# COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV NODE_ENV production

ENV PORT 3000
ENV HOSTNAME "0.0.0.0"

# server.js is created by next build from the standalone output
CMD ["node", "server.js"]