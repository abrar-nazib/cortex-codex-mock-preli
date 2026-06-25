# QueueStorm Frontend

This is the Next.js frontend for the QueueStorm Mock Preliminary Task. It provides a modern, minimalist UI to submit customer support tickets and visualize the AI routing classifications (intent, severity, routing team, and model confidence).

## Tech Stack

- **Framework**: Next.js (App Router)
- **Styling**: Tailwind CSS v4, shadcn/ui
- **Typography**: Geist Sans & Mono
- **Deployment**: Docker (Multi-stage Standalone Build)

## Getting Started Locally

First, install dependencies using pnpm (the repository's preferred package manager):

```bash
pnpm install
```

Start the development server:

```bash
pnpm dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser to interact with the UI.

## Environment Variables

To connect to the backend, the frontend relies on the following environment variable (configurable via `.env`):

- `NEXT_BACKEND_URL`: The URL of the QueueStorm backend API (e.g., `http://localhost:38181`).

## Docker Deployment

This frontend is optimized for containerized environments. It compiles into a Next.js `standalone` build for minimal image sizes.

The easiest way to run the entire stack (Frontend + Backend + Normalizer) is via the root `docker-compose.yml`:

```bash
cd ..
docker compose up --build
```

The frontend will be accessible at `http://localhost:38283`.

### Manual Docker Build

If you wish to build the frontend image independently:

```bash
docker build -t queuestorm-frontend .
docker run -p 3000:3000 --env-file .env queuestorm-frontend
```

## Features

- **Split Layout Architecture**: Clean input form mapping to the `/sort-ticket` API payload.
- **Skeletal Loaders**: Beautiful structural loading states that mirror the final UI shapes while awaiting backend resolution.
- **Bento Grid Presentation**: Results are rendered in a high-density, easily scannable dashboard.
- **Fallback Mocks**: If the backend is unavailable, the UI gracefully falls back to a simulated mock response for seamless demonstration.
