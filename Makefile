.PHONY: test build check

test:
	pytest -q

build:
	cd frontend && corepack pnpm install --frozen-lockfile=false && corepack pnpm build

check: test build
	git diff --check
