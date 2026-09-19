---
created_at: 2026-07-10
status: mainline
route: AOGE_AUTOMATIC_ORCHESTRATION_GATE_ENABLEMENT
scope: AOGE0_AOGE1_ONLY
provider_pull_allowed: false
provider_publish_allowed: false
provider_accepted_latest_switch_allowed: false
qlib_accepted_latest_switch_allowed: false
legacy_option_c_latest_signal_switch_allowed: false
openai_call_allowed: false
monitor_write_allowed: false
broker_order_allowed: false
agent_prompt_publish_allowed: false
readonly_snapshot_latest_write_allowed: false
agent_prompt_latest_write_allowed: false
system_crontab_install_allowed: false
---

# AOGE Automatic Orchestration Gate Enablement Mainline

## 1. Goal

AOGE 的目标是为每日自动更新打开 Automatic Orchestration Gate Enablement route：
把 ADOR no-publish orchestration dry-run gate 纳入仓库内 installed cron 的每日观察面。

允许的唯一运行时配置变化是让两条已存在的 daily/full cron job 显式携带：

```text
ENABLE_TW_ADOR_NO_PUBLISH_ORCHESTRATION_DRY_RUN=true
TW_ADOR_NO_PUBLISH_ORCHESTRATION_DRY_RUN=true
TW_AGENT_DAILY_PROMPT_DRY_RUN=true
ENABLE_TW_AGENT_DAILY_PROMPT_PUBLISH=false
TW_AGENT_DAILY_PROMPT_PUBLISH_LATEST=false
```

该 route 只授权 cron 文件中的 no-publish dry-run 观察配置，不授权执行真实日更，也不授权安装系统 crontab。

## 2. Non-goals

AOGE 不做：

```text
publish/latest write
provider pull
provider publish
provider accepted latest switch
qlib accepted latest switch
legacy option_c latest_signal switch
model scoring/training
strategy replay
OpenAI call
monitor scan/config/alert write
broker, quick-trade, order
OrderIntentArtifact or ReplayResult generation
target_position, target_weight, quantity, shares, lots output
system crontab install
daily auto script execution
```

## 3. Forbidden Actions

所有阶段禁止：

```text
--disable-ador-no-publish-orchestration-dry-run
ENABLE_TW_AGENT_DAILY_PROMPT_PUBLISH=true
TW_AGENT_DAILY_PROMPT_PUBLISH_LATEST=true
--enable-legacy-provider-publish
TW_DAILY_AUTO_ENABLE_LEGACY_PROVIDER_PUBLISH=true
provider/accepted latest/OpenAI/monitor/broker/order side effects
```

## 4. Phase Scope

### AOGE0

盘点 installed cron、日更脚本 ADOR gate、安全默认和 audit 可观测性。不得改系统 crontab，不得运行日更。

### AOGE1

在仓库内 installed cron 的 daily/full 两条 job 中显式启用 ADOR no-publish dry-run gate，并扩展 audit/test 证明：

```text
ADOR gate enabled
ADOR dry-run true
Agent prompt dry-run true
Agent prompt publish false
Agent prompt publish latest false
forbidden controls absent
```
