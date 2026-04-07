# Web Shell

Minimal React + Vite + TypeScript shell. Run with:

```bash
cd apps/web-shell
pnpm install
pnpm dev   # http://localhost:5173, proxies /api → http://localhost:8000
```

Each lane should add its own page module under `src/lanes/{plm|mfg|scm|mgmt}/`.
