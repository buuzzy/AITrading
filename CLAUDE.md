# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ShipAny Template One - A Next.js 15 AI SaaS boilerplate with App Router, TypeScript, authentication, payments, internationalization, and MDX documentation support.

## Development Commands

### Core Development
```bash
pnpm dev          # Start dev server with Turbopack
pnpm build        # Build for production
pnpm start        # Run production build
pnpm lint         # Run ESLint
pnpm analyze      # Analyze bundle size
```

### Database Operations (Drizzle ORM)
```bash
pnpm db:generate  # Generate migrations from schema
pnpm db:migrate   # Run migrations
pnpm db:push      # Push schema directly to DB
pnpm db:studio    # Open Drizzle Studio
```

### Docker
```bash
pnpm docker:build # Build Docker image
```

## Architecture

### Authentication Flow
- **NextAuth 5.0** (`src/auth/`) - OAuth and credentials providers
- Supports Google (OAuth + One Tap), GitHub authentication
- Custom JWT callbacks handle user persistence in `src/auth/config.ts:148`
- Sign-in handler at `src/auth/handler.ts` coordinates with user service
- Session component at `src/auth/session.tsx` provides client-side auth state

### Database Layer
- **Drizzle ORM** with PostgreSQL
- Schema: `src/db/schema.ts`
- Connection: `src/db/index.ts`
- Config: `src/db/config.ts` (loads from .env.development/.env.local)
- Migrations: `src/db/migrations/`

### Data Architecture (Models + Services)
- **Models** (`src/models/`): Database queries and data access
  - `user.ts`, `order.ts`, `credit.ts`, `affiliate.ts`, `apikey.ts`, `feedback.ts`, `post.ts`
- **Services** (`src/services/`): Business logic layer
  - `user.ts`, `order.ts`, `credit.ts`, `stripe.ts`, `affiliate.ts`, `page.ts`
- Services consume models and implement business rules

### Payment Integration
- Dual payment provider support (Stripe/Creem)
- Provider controlled via `PAY_PROVIDER` env var
- Stripe integration: `src/integrations/stripe/` and `src/services/stripe.ts`
- Creem integration: `src/integrations/creem/`
- Checkout API: `src/app/api/checkout/`
- Webhook handlers: `src/app/api/pay/stripe/` and `src/app/api/pay/creem/`

### Internationalization (next-intl)
- Middleware: `src/middleware.ts` handles locale routing
- Supported locales: en, en-US, zh, zh-CN, zh-TW, zh-HK, zh-MO, ja, ko, ru, fr, de, ar, es, it
- Config: `src/i18n/routing.ts`
- Page content: `src/i18n/pages/landing/`
- Messages: `src/i18n/messages/`
- Navigation helpers: `src/i18n/navigation.ts`

### Route Structure
- App Router with locale prefix: `src/app/[locale]/`
- Default layout: `src/app/[locale]/(default)/`
- Console routes: `src/app/[locale]/(default)/(console)/` - Protected user dashboard
  - `/my-orders`, `/my-credits`, `/my-invites`, `/api-keys`
- Legal routes: `src/app/(legal)/` - Privacy/Terms (bypasses locale)
- Auth: `src/app/[locale]/auth/signin/`
- API routes: `src/app/api/`

### Component Organization
- **blocks/** - Page sections (header, footer, pricing, etc.) for landing pages
- **ui/** - Shadcn UI components (button, dialog, dropdown, etc.)
- **dashboard/** - Console-specific components
- **console/** - Console feature components
- **feedback/** - User feedback components
- **sign/** - Authentication UI
- **analytics/** - Analytics integration wrappers
- **locale/** - Locale switcher
- **theme/** - Theme switcher
- **markdown/** - MDX rendering components

### Utility Libraries (`src/lib/`)
- `auth.ts` - Auth helpers
- `cache.ts` - Caching utilities
- `hash.ts` - UUID generation
- `ip.ts` - Client IP detection
- `resp.ts` - API response formatting
- `storage.ts` - AWS S3 storage integration
- `time.ts` - Time formatting (ISO strings)
- `utils.ts` - General utilities

### AI SDK Integration
- AI SDK providers: `src/aisdk/` (OpenAI, Deepseek, Replicate, OpenRouter)
- Demo endpoints: `src/app/api/demo/` showcase AI streaming capabilities

### MDX Documentation
- Fumadocs integration for `/docs` routes
- Config: `source.config.ts`
- Content: `content/` directory
- MDX components: `src/mdx-components.tsx`

## Key Configuration Files

- `next.config.mjs` - Enables MDX (mdxRs), bundle analysis, next-intl
- `tsconfig.json` - Path aliases: `@/*` → `src/*`, `@/.source` → `.source/`
- `components.json` - Shadcn UI configuration
- `.env.development` - Local environment variables (copy from `.env.example`)

## Environment Setup

1. Copy environment template: `cp .env.example .env.development`
2. Required variables:
   - `DATABASE_URL` - PostgreSQL connection string
   - `AUTH_SECRET` - NextAuth secret (generate with `openssl rand -base64 32`)
   - `AUTH_URL` - Auth callback URL (http://localhost:3000/api/auth)
3. Optional integrations:
   - Google/GitHub OAuth credentials
   - Stripe/Creem payment keys
   - Analytics (Google Analytics, OpenPanel, Plausible)
   - Storage (AWS S3)

## Tech Stack

- **Framework**: Next.js 15.2.3 (App Router, Turbopack)
- **Runtime**: React 19
- **Language**: TypeScript 5.7
- **Styling**: Tailwind CSS 4.1 + Shadcn UI + Radix UI
- **Database**: PostgreSQL + Drizzle ORM 0.44
- **Auth**: NextAuth 5.0 (beta)
- **Payments**: Stripe 17.5 / Creem 0.3
- **i18n**: next-intl 4.1
- **AI**: Vercel AI SDK 4.1 (OpenAI, Deepseek, Replicate)
- **Docs**: Fumadocs (MDX)
- **Animation**: Framer Motion 11.15
- **Package Manager**: pnpm

## Development Notes

- **Turbopack enabled** for faster dev builds
- **React StrictMode disabled** (reactStrictMode: false)
- **Standalone output** for Docker deployment
- **MDX support** for .md/.mdx page extensions
- **TypeScript strict mode** enabled
- Use `@/` imports for src files (e.g., `@/components/ui/button`)
- Middleware excludes: `/api`, `/_next`, `/_vercel`, legal routes, static assets
