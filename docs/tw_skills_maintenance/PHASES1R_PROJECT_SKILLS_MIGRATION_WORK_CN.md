# Phase S1R 工作文档：项目内 Skills 落点权限修复与全局 tw-stock Skills 迁入

生成日期：2026-06-19

## 1. 工作结论

Phase S1 因权限阻塞未完成。用户已明确后续台股 skills 应迁到当前项目：

```text
.agents/skills/
```

新增 skills 也应放在该项目目录下。

本阶段是 S1 的修复阶段，目标不是修改 skill 内容，而是修复落点和迁移旧版本：

```text
修复 .agents 权限
-> 将全局用户级 tw-stock-* skills 迁入当前项目 .agents/skills
-> 处理全局旧版本，避免同名触发歧义
-> 输出迁移报告
```

完成 S1R 后，才能恢复 S1：在项目内版本化 skills 上进行内容更新。

## 2. 本阶段范围

源目录：

```text
/home/chuliyang/.agents/skills/tw-stock-safety-boundary-review
/home/chuliyang/.agents/skills/tw-stock-readonly-e2e-acceptance
/home/chuliyang/.agents/skills/tw-stock-research-context-analyst
/home/chuliyang/.agents/skills/tw-stock-data-freshness-diagnosis
```

目标目录：

```text
.agents/skills/tw-stock-safety-boundary-review
.agents/skills/tw-stock-readonly-e2e-acceptance
.agents/skills/tw-stock-research-context-analyst
.agents/skills/tw-stock-data-freshness-diagnosis
```

允许修改：

```text
.agents/
.agents/skills/
docs/tw_skills_maintenance/PHASES1R_PROJECT_SKILLS_MIGRATION_EXECUTION_REPORT_CN.md
```

本阶段不修改 skill 内容，只迁移文件和修复权限。

## 3. 权限处理策略

当前问题：

```text
.agents 和 .agents/skills 由 root:root 拥有，当前用户无写权限。
```

允许使用 sudo，但只用于权限修复和必要的文件迁移，不用于编辑 skill 内容。

推荐命令：

```bash
sudo chown -R chuliyang:chuliyang .agents
```

完成后确认：

```bash
stat -c '%U:%G %a %n' .agents .agents/skills .agents/skills/frontend-design
```

期望：

```text
chuliyang:chuliyang
```

如果统筹希望保留 root ownership，也可以改为 ACL 或 group write，但必须保证当前用户能在 `.agents/skills` 下创建 repo 内台股 skill 目录。

## 4. 迁入策略

推荐使用复制而不是直接移动：

```text
先复制用户级 tw-stock-* 到 repo 内
确认 repo 内完整
再处理用户级旧版本
```

原因：

- 复制保留回滚路径。
- 避免当前会话或其他运行时立即失去用户级旧 skill。
- repo 内版本需要先接受审查。

复制必须保留：

```text
SKILL.md
references/
scripts/
其他已有资源
```

示例：

```bash
cp -a /home/chuliyang/.agents/skills/tw-stock-safety-boundary-review .agents/skills/
cp -a /home/chuliyang/.agents/skills/tw-stock-readonly-e2e-acceptance .agents/skills/
cp -a /home/chuliyang/.agents/skills/tw-stock-research-context-analyst .agents/skills/
cp -a /home/chuliyang/.agents/skills/tw-stock-data-freshness-diagnosis .agents/skills/
```

如果目标目录已存在，必须停止并报告，不得覆盖。

## 5. 全局旧版本处理策略

用户倾向是“把原先全局里的 `tw-stock*` skills 都移动到当前项目 `.agents/skills` 中”。为了避免破坏当前运行时和保留回滚，推荐分两步：

### 5.1 S1R 推荐动作

完成 repo 内复制后，将用户级旧版本归档到：

```text
/home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/
```

归档方式：

```bash
mkdir -p /home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619
mv /home/chuliyang/.agents/skills/tw-stock-safety-boundary-review /home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/
mv /home/chuliyang/.agents/skills/tw-stock-readonly-e2e-acceptance /home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/
mv /home/chuliyang/.agents/skills/tw-stock-research-context-analyst /home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/
mv /home/chuliyang/.agents/skills/tw-stock-data-freshness-diagnosis /home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619/
```

归档不是删除。这样可以：

- 避免同名触发冲突。
- 保留旧版本回滚。
- 让 repo 内版本成为后续权威来源。

### 5.2 如果 mv 需要权限

如果移动用户级目录遇到权限问题，允许请求 sudo，但必须只对上述四个 `tw-stock-*` 目录和归档目录操作。不得影响其他用户级 skills：

```text
pptx
skill-creator
latex-paper-en
其他非台股 skills
```

### 5.3 不允许

不得直接删除：

```text
rm -rf /home/chuliyang/.agents/skills/tw-stock-*
```

不得归档非台股 skills。

不得把全局旧版本留在原路径同时创建 repo 内同名版本，除非执行报告明确说明运行时仍会同名冲突且等待审查处理。

## 6. 必须检查的文件完整性

执行后运行：

```bash
find .agents/skills/tw-stock-* -maxdepth 3 -type f | sort
```

必须包含至少：

```text
.agents/skills/tw-stock-safety-boundary-review/SKILL.md
.agents/skills/tw-stock-safety-boundary-review/references/forbidden-actions.md
.agents/skills/tw-stock-safety-boundary-review/references/network-audit-rules.md

.agents/skills/tw-stock-readonly-e2e-acceptance/SKILL.md
.agents/skills/tw-stock-readonly-e2e-acceptance/references/readonly-boundary.md
.agents/skills/tw-stock-readonly-e2e-acceptance/references/acceptance-report-template.md

.agents/skills/tw-stock-research-context-analyst/SKILL.md
.agents/skills/tw-stock-research-context-analyst/references/qlib-cross-analysis-semantics.md
.agents/skills/tw-stock-research-context-analyst/references/research-report-template.md

.agents/skills/tw-stock-data-freshness-diagnosis/SKILL.md
.agents/skills/tw-stock-data-freshness-diagnosis/references/data-source-boundary.md
.agents/skills/tw-stock-data-freshness-diagnosis/references/freshness-status-fields.md
```

如果已有 scripts，也必须保留。

## 7. 必须检查全局状态

执行后运行：

```bash
find /home/chuliyang/.agents/skills -maxdepth 2 -name SKILL.md -print | sort
find /home/chuliyang/.agents/skills/_archived_tw_stock_skills_20260619 -maxdepth 3 -type f | sort
```

期望：

- `/home/chuliyang/.agents/skills` 原路径下不再有四个 `tw-stock-*` 目录。
- 四个旧版本存在于 `_archived_tw_stock_skills_20260619/`。
- 非台股 skills 保持原样。

## 8. 必须更新主线文档口径

完成 S1R 后，执行报告必须明确当前策略：

```text
项目内 .agents/skills/tw-stock-* 是后续权威版本。
全局 /home/chuliyang/.agents/skills/tw-stock-* 已归档，不再作为主维护位置。
新增五个台股 skills 也全部放入 .agents/skills。
```

如果归档失败，只能写：

```text
repo 内已复制，但用户级旧版本仍存在，存在同名触发冲突风险。
```

这种情况不得恢复 S1 内容修改，必须先复审。

## 9. 本阶段不得做的事

不得修改四个 skill 的内容，例如：

```text
description
Workflow
Forbidden Actions
references 内容
scripts 内容
```

不得新增五个新 skills。

不得运行 skill eval。

不得修改台股业务代码、前端代码、模型/策略代码。

## 10. 执行报告要求

完成后写：

```text
docs/tw_skills_maintenance/PHASES1R_PROJECT_SKILLS_MIGRATION_EXECUTION_REPORT_CN.md
```

报告必须包含：

```text
本阶段目标
权限修复命令与结果
迁入来源与目标
repo 内文件完整性清单
用户级旧版本归档位置
全局非台股 skills 未受影响确认
是否仍存在同名 tw-stock skills 冲突
未修改 skill 内容确认
未修改业务/前端/模型/策略代码确认
未解决问题
是否建议恢复 S1 内容更新
```

## 11. 审查通过标准

S1R 只有同时满足以下条件才可通过：

1. `.agents/skills` 当前用户可写。
2. 四个 `tw-stock-*` skills 已完整存在于 `.agents/skills/`。
3. `references/` 和 `scripts/` 保留完整。
4. 用户级原路径下不再存在同名四个 `tw-stock-*` skills，或已明确归档。
5. 归档版本可回滚。
6. 非台股用户级 skills 未被移动或修改。
7. 未修改 skill 内容。
8. 未修改业务/前端/模型/策略代码。

## 12. 停止条件

遇到以下任一情况必须停止：

- `sudo chown` 或权限修复失败。
- 目标 repo 内 `tw-stock-*` 目录已存在且内容不明。
- 复制后文件数量或关键文件缺失。
- 归档用户级旧版本会影响非台股 skills。
- 无法确认用户级旧版本是否成功归档。
- 需要删除文件才能继续。
- 需要修改 skill 内容才能完成迁移。
