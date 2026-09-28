# Clean 开发入口

先读 [接手指南](CODEX_HANDOFF_CN.md)、[架构](ARCHITECTURE_CN.md) 和 [运维](OPERATIONS_CN.md)。旧单体文档目录不再是运行依赖，本页列出当前合同与入口。

| 工作类别 | 合同 / 配置 | 最小验证 |
| --- | --- | --- |
| 数据 / 日更 | product.yaml；tw_product_artifact_registry.yaml | data_governance、provider_refresh、daily_isolation、release 测试；M3 |
| 模型 / 特征 | active_baseline_descriptor.yaml；tw_modular_registry.yaml | signal_integrity；ARCH-1；modules |
| 策略 / 回放 | tw_replay_window_policy.yaml；strategy.py | correctness、product 测试；真实隔离回放 |
| readonly API / Agent | service.py、agent.py、validation.py | api_validation、readiness、agent_completion；stack |
| 模拟账户 | paper.py、routes/paper.py | paper 测试；预览/确认、幂等、并发 |
| 运维 / 部署 | maintenance.py；ops/；deploy_clean_product.py | maintenance、deployment、release测试；隔离恢复与ready |
| 前端 | frontend/src、frontend/tests | Node、pnpm build、三视口浏览器验收 |

测试文件名为 `tests/test_clean_<名称>.py`。信号包含 date、instrument、score、rank、candidate_rank、full_qlib_rank；READY 必须有唯一键、有限分数、连续排名和可验证来源。Model A 是唯一 baseline，B19R2R 保持 production_allowed=false / mainline_blocking=false。

daily --publish 保存完整批次后切换 active.json；candidate / dry-run 不发布。GET 不采集数据、不写账户。模拟账户的 POST 独立认证和确认，比较页保持 no_apply。开发先检查 git status，保留未提交修改和本机资产。
