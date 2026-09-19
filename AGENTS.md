# Repository Instructions

These rules apply to the entire repository. Read `docs/CODEX_HANDOFF_CN.md` before changing code, runtime configuration, artifacts, or operations scripts.

## Product Boundary

- This is a Taiwan-stock read-only research product with a simulation-only paper account. It is not a live trading system.
- The only active baseline is Model A, `e4_frozen_qlib_2018_2022`, with strategy `top50_exit_one_worst_sell` and `next_open` execution semantics.
- `modelb_b19r2r_lambdarank_exact50_78f_v2` is a frozen LightGBM LambdaRank research challenger. It reranks Model A's same-day Top50 with 78 PIT-safe features and excludes TW7769 without replacement.
- B19R2R must remain `production_allowed=false`. It may feed readonly comparison, prospective shadow evidence, and review reports. It may not become the frontend default, provider/accepted latest, paper-portfolio input, broker input, or order input without a separate admission decision.

## Sources Of Truth

Use these sources in this order; do not infer current state from an old phase report:

1. Live process state: `GET /api/ready`, daily status, and readonly ops status.
2. Baseline/default identity: `configs/active_baseline_descriptor.yaml`.
3. Module eligibility and consumer boundaries: `configs/tw_modular_registry.yaml`.
4. Product artifact paths and replay policy: `configs/tw_product_artifact_registry.yaml` and `configs/tw_replay_window_policy.yaml`.
5. Immutable manifests, validators, checksums, and run evidence.
6. Current documentation. Historical phase documents explain provenance but do not override the sources above.

The product registry still contains legacy Orthogonal LTR compatibility paths. That model is a legacy research artifact, not the current challenger and not an active baseline.

## Before Editing

- Inspect `git status` and preserve the dirty worktree. Never reset, checkout, overwrite, or revert changes you did not create.
- Classify the change as data, feature, model, adapter, strategy, replay, readonly API, frontend, paper portfolio, Agent, or daily orchestrator work. Follow the existing contract and registry for that module.
- Keep the artifact flow one-way: data -> PIT features -> model signal -> strategy intent -> replay -> readonly API/frontend. Do not make downstream code read private experiment files.
- Read the relevant contract and the task-specific guide linked from `docs/DEVELOPMENT_ONBOARDING_CN.md`.
- Do not read, print, copy, or commit secrets from `backend/.env` or process environments.

## Safety And Operations

- Do not trigger provider refresh/publish, accepted-latest switches, latest-pointer writes, monitor writes/scans, broker/quick-trade/order paths, model training, or production default changes unless the user explicitly authorizes that exact operation.
- Prefer GET-only probes, validators, fixtures, dry-runs, and isolated output directories for diagnosis.
- A weekend or market holiday legitimately keeps `latest_asof` at the previous trading day. Check the Taiwan market calendar before declaring staleness.
- Keep scheduled evidence distinct from manual retries. A manual `READY_RESEARCH_SHADOW` result does not prove the scheduled full lane succeeded.
- A B19R2R `BLOCKED` result is non-blocking for Model A when `mainline_blocking=false`; record and diagnose it without contaminating mainline pending state.
- The model/strategy comparison workbench is read-only. Its `no_apply` contract applies to every selection in that page. Simulation changes belong to the separately gated paper-account flow.

## Files And Deletion

- Do not delete source, documents, tests, scripts, or artifacts merely because they look old. Prove they are outside import, router, test, cron, registry, validator, and artifact rebuild closures.
- Before any physical deletion, create a repository-external backup with an exact manifest and SHA256 values, scan it for credentials, and verify restoration in an isolated directory. Keep the backup and evidence paths in the slimming report.
- Do not replace or regenerate ignored live assets as a health check. A fresh checkout does not contain production market data or frozen model files.
- Generated caches may be removed only after the same backup and secret-scan rules are satisfied. A cache that triggers credential scanning stays in place until a safe handling plan exists.

## Minimum Validation

- Documentation only: verify local links and command/API paths, run `git diff --check`, and use GET-only live probes when describing current state.
- Backend/contracts: run focused pytest for touched modules plus the modular contract regression when a cross-module contract changes.
- Daily orchestration: run its focused unit tests and M3 validator. Do not execute a real update merely to validate code.
- Frontend: run focused static/unit checks and `cd frontend && corepack pnpm build`; use fixture Playwright for user-flow changes.
- Release/readiness changes: run `scripts/verify_tw_stock_research_stack.py`, ARCH-1 validation, modular contract regression, and read-only deployment acceptance as applicable.

Never claim a check passed unless it was run in the current worktree. Record skipped checks and the reason.
