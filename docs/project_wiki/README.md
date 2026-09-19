---
title: Project Wiki Vault
category: reference
tags: [wiki, setup]
sources: []
summary: 项目本地 Obsidian-compatible vault 的使用说明和配置入口。
provenance:
  extracted: 1.0
  inferred: 0.0
  ambiguous: 0.0
base_confidence: 0.5
lifecycle: draft
lifecycle_changed: 2026-06-20
tier: supporting
created: 2026-06-20T00:00:00Z
updated: 2026-06-20T00:00:00Z
---

# Project Wiki Vault

This directory is a project-local Obsidian-compatible LLM wiki for the Taiwan stock quant platform.

Use it as the compiled knowledge layer for architecture, contracts, safety boundaries, daily data flow, Agent route, frontend route, and new model/strategy onboarding decisions.

Suggested local config if an external wiki runner is later installed:

```env
OBSIDIAN_VAULT_PATH=docs/project_wiki
OBSIDIAN_LINK_FORMAT=wikilink
```

Current status: seed vault. It was created from selected project docs and skills, not from a full automated repository ingest.

## Maintenance

- [[hot|Hot Cache]] tracks recent activity and active threads.
- [[_meta/taxonomy|Wiki Tag Taxonomy]] lists project-local tag conventions.
