# Project Agents Guide

This is a TanStack Start + React + TypeScript frontend styled with Tailwind CSS.

- Vite config lives in `vite.config.ts` and uses `@tanstack/react-start/plugin/vite`
  directly (no external build wrapper).
- Routes live under `src/routes` and are generated into `src/routeTree.gen.ts`.
- The dev server proxies `/api/*` to the FastAPI backend at `http://localhost:8000`.
- Commands: `npm run dev`, `npm run build`, `npm run lint`, `npm run format`.
