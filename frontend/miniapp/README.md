# LectionSeller Mini App Frontend

Telegram Mini App frontend for LectionSeller TG Bot.

## Stack

- React
- Vite
- TypeScript
- Tailwind CSS
- TanStack Query
- lucide-react
- Telegram WebApp JS API

## Local Development

From this directory:

```bash
npm install
npm run dev
```

The dev server proxies `/miniapp/api/*` to `http://127.0.0.1:8000`.
Open the local app at `http://127.0.0.1:5173/app/`.

Backend health check:

```bash
curl -f http://127.0.0.1:8000/health
curl -f http://127.0.0.1:8000/miniapp/api/meta
```

## Build

```bash
npm run typecheck
npm run build
```

Production URL:

```text
https://tracerxbrhd.ru/app
```
