This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project self-hosts [Pretendard](https://github.com/orioncactus/pretendard) (한글+라틴) via `next/font/local` in `src/app/layout.tsx` — the font binary and its OFL license live in `src/app/fonts/`. Do not reintroduce a CDN `<link>` for fonts (see `docs/tech-debt.md` #40/#127). Design tokens (color/typography/shadow/radius) are centralized in `src/app/globals.css` (Tailwind v4 `@theme`).

## Running E2E Tests (Playwright)

`web/e2e/*.spec.ts` (Story 11.5) drives a real Chromium browser against a production build of this app. It is not wired into CI (see `docs/tech-debt.md` #168) — it must be run locally, and needs a running, seeded local Supabase stack. Prerequisites, from the repo root:

1. Start the local Supabase stack: `npx supabase start`.
2. Point `web/.env.local` at it: `bash scripts/use-env.sh local` (this file is gitignored, so it must be regenerated after a fresh checkout).
3. Seed demo data: `bash scripts/seed-local.sh` — this also creates the account the specs log in with (`buyer@test.com` / `seller123`, see `web/e2e/helpers.ts`).
4. Install the browser Playwright drives (once, from `web/`): `npx playwright install chromium`.

Then, from `web/`:

```bash
npm run test:e2e
```

Port 3000 is often already taken in this repo — override it with `E2E_PORT` if needed (e.g. `E2E_PORT=3020 npm run test:e2e`).

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.
