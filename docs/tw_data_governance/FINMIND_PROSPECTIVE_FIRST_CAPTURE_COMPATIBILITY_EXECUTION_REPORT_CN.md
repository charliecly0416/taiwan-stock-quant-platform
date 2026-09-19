# Prospective First-Successful-Capture 兼容性执行报告

## 1. 范围

在不修改既有 legacy 数据、模型、策略、provider、latest 或 cron 的前提下，为未来
daily capture 增加明确的 availability evidence 表达，并接入 HSA8 严格 handoff。

## 2. 实现

- backend FinMind adapter 新增可选 `availability_evidence` tagged object：
  `method=first_successful_capture`、`observed_at`、`observation_scope`。
- 新采集将首次成功捕获时间作为 observed availability lower bound；不会将其写成
  provider publication time。
- HSA8 保留旧 publication-time 模式；新模式要求 `source_published_at=null`、
  `available_at=observed_at<=fetched_at`，并继续要求 validator PASS、scope closure、
  same-run、path/checksum 完整。
- adapter canonical digest 对新字段做条件绑定；旧 fixture 无该字段时保持原 digest
  和原验证行为。

## 3. 验证

- HSA8、logical acquisition、runner recovery：`45 passed`。
- backend FinMind capture/status：`28 passed`。
- 新增 first-successful-capture 正向兼容测试，旧模式回归保持通过。

## 4. 安全结论

该改动只建立未来证据的表达与验证能力，不会将当前 8/28 的 unknown scope、缺失
publication evidence 或 TWII schema 问题放行。真实生产 adapter 仍需在 scope/validator
达到 PASS 后才可生成 PIT-safe downstream；当前 latest 和 legacy 结果不变。
