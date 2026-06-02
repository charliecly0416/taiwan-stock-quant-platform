# Publishing Checklist

Before pushing this project to GitHub:

- Confirm `.env`, `.env.*`, generated data, qlib binary artifacts, caches, `node_modules`, and `frontend/dist` are absent.
- Confirm `.env.example` contains placeholders only.
- Run a secret scan for API keys, database passwords, and broker credentials.
- Run backend focused tests.
- Run frontend static checks and `pnpm build`.
- Review licenses and keep attribution in `NOTICE.md`.
- Keep the safety boundary clear: research only, no automatic broker orders.
