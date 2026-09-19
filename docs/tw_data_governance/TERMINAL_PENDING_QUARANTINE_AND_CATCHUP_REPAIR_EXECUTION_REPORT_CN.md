# Terminal Pending Quarantine / Catch-up 修复执行报告

## 实现

- daily runner 新增严格 terminal pending classifier。
- 新增 no-clobber quarantine archive 和 decision record。
- 新增 weekend-aware next-workday catch-up；当前 `2026-08-28` 后继为
  `2026-08-31`。
- catch-up 若等于台北当天，仍服从当日最早抓取时间；历史 catch-up 可直接处理。
- 修复 status API：任意真实 pending 都显示 scheduled processing，fresh-data wait 保留
  retry 文案。

## 实际迁移

- 8/28 判定：`complete_capture_evidence_gate_terminal`。
- 原 pending 已保存在
  `data_tw/ops/daily_auto_update/terminal_pending_quarantine/`。
- 当前 pending：`2026-08-31 / terminal_pending_catchup`。
- backend 已受控重启；frontend、ngrok 保持在线。

## 验证

- 专项与相关回归：`89 passed`。
- API 已返回 8/31 catch-up 和正确 next retry hint。
- Qlib accepted、legacy、signal、readonly snapshot、Agent latest 的前后 SHA256 全部一致。
- 未手动触发 daily job、provider pull/publish、Qlib refresh、latest switch、训练、评分、
  OpenAI、DB 或交易动作。
