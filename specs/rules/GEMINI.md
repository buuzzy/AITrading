# GEMINI.md: Project Context for ShipAny Template One

This document provides essential context for interacting with the `shipany-template-one` codebase. It outlines the project's architecture, key technologies, and operational procedures.

## Project Overview

This project is a comprehensive AI SaaS boilerplate built on the "ShipAny Template One". It's designed to accelerate the development of full-stack AI applications.

The stack is modern and robust, featuring:
- **Framework**: Next.js 15 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS with shadcn/ui components
- **Database**: PostgreSQL with Drizzle ORM for type-safe queries
- **Authentication**: NextAuth.js, supporting Google (OAuth & One Tap) and GitHub providers
- **Payments**: Stripe integration for subscriptions and one-time purchases
- **Content**: `fumadocs-mdx` for documentation and `react-tweet` for embedding tweets.
- **Internationalization (i18n)**: `next-intl` supporting English (`en`) and Chinese (`zh`)
- **AI**: Generic AI provider integration layer (`@ai-sdk/provider`) with specific implementations for OpenAI, DeepSeek, and Replicate.

The application is structured as a multi-module SaaS platform, including user management, an order/credit system, API key management, a content/blogging system (`posts`), an affiliate program, and a user feedback mechanism.

## Key Files & Directories

- `src/app/[locale]/`: Main application routes, following the Next.js App Router structure.
- `src/db/schema.ts`: Defines the entire database schema using Drizzle ORM.
- `src/auth/config.ts`: Configures NextAuth.js, including all authentication providers and callbacks.
- `src/i18n/`: Contains all internationalization configuration and message files.
- `src/services/`: Business logic for interacting with the database models.
- `src/components/`: Reusable React components, including UI components from `shadcn/ui`.
- `content/docs/`: MDX files for documentation, processed by `fumadocs`.
- `next.config.mjs`: Next.js configuration, including plugins for MDX, i18n, and bundle analysis.
- `package.json`: Defines all dependencies and scripts.

## Building and Running

### 1. Prerequisites
- Node.js (version specified in `.nvmrc` if present)
- pnpm package manager
- Docker (for database or deployment)

### 2. Initial Setup
First, copy the example environment file and fill in the necessary secrets (database credentials, auth provider keys, Stripe keys, etc.).

```bash
cp .env.example .env.development
```

### 3. Install Dependencies
```bash
pnpm install
```

### 4. Run Development Server
The application will be available at `http://localhost:3000`.

```bash
pnpm dev
```

### 5. Build for Production
```bash
pnpm build
```

### 6. Run Production Server
```bash
pnpm start
```

## Database Management

The project uses `drizzle-kit` for database migrations and management.

- **Generate Migrations**: After changing `src/db/schema.ts`, generate a new migration file.
  ```bash
  pnpm db:generate
  ```
- **Apply Migrations**: Apply pending migrations to the database.
  ```bash
  pnpm db:migrate
  ```
- **Push Schema (for development)**: Directly push schema changes to the database without creating a migration file. **Warning**: This can be destructive.
  ```bash
  pnpm db:push
  ```
- **Drizzle Studio**: Open a local GUI to browse and manage your database.
  ```bash
  pnpm db:studio
  ```

## Development Conventions

- **Code Style**: The project uses ESLint and Prettier (inferred from standard Next.js setups) to enforce a consistent code style. Run `pnpm lint` to check for issues.
- **Path Aliases**: The `tsconfig.json` sets up a path alias `@/*` which maps to the `src/*` directory. Use this for cleaner imports.
- **Internationalization**: All user-facing strings should be added to the message files in `src/i18n/messages/`. Do not hardcode text in components.
- **Environment Variables**: All secrets and environment-specific configurations must be managed through `.env` files. Refer to `.env.example` for a complete list of required variables.

## Backend Trading Engine (Alpha-Arena-Lite)

The project includes a Python-based backtesting and simulated trading engine located in the `@demo` directory. Its purpose is to test and run trading strategies on Chinese A-shares using different LLMs.

### Core Components
- **Engine**: `backtest.py` (for historical backtesting) and `livetrade.py` (for simulated live trading).
- **Decision Logic**: `trade_decision_simple_AI.py` constructs prompts and uses a DeepSeek LLM (via an OpenAI-compatible API) to make trading decisions (`buy`, `sell`, `hold`).
- **Data Source**: Market data (daily prices, technical factors) is fetched exclusively via the `tinyshare` API, which requires a `TINYSHARE_TOKEN`.
- **Portfolio Management**: `simple_portfolio.py` enforces A-share market rules, including T+1 settlement, lot sizes (100 shares), and transaction fees.

### Data Output
The backtesting script (`backtest.py`) is the primary source of data for the frontend. It generates several files in the `backtest/<symbol>/` directory for each run.

The most critical file is the trade log:
- **File**: `trades_<symbol>_<start>_<end>.csv`
- **Columns**: `date,price,signal,quantity,leverage,success,available_cash,total_asset,llm_ms,effective_price`
- **Key Column**: `total_asset` represents the daily equity of the model for that specific stock, which is the basis for all frontend performance visualizations.

### Frontend API Goal
The ultimate goal is to create a frontend that displays aggregated performance for each LLM model across all stocks it trades. This requires a new backend API layer within the Next.js application that will:
1.  Read all the individual `trades_*.csv` files generated by the Python engine.
2.  Aggregate the `total_asset` and other metrics on a per-model, per-day basis.
3.  Expose this aggregated data through endpoints that mimic the reference specification in `@specs/refer/api.md`, such as `/api/account-totals` and `/api/since-inception-values`.
