# M01 Source Intake Verification Report

验证对象：`TASK-M01-SOURCE-INTAKE-001`

验证时间：2026-11-17 16:41（Asia/Shanghai）

验证范围：只核对来源是否可读、登记内容是否能回链、事实/推断/待确认是否分开；不把资料读取误判为安装、配置或业务功能通过。

## 来源可回读

结果：通过。

- GitHub 页面和固定提交的 raw 文档均可读取。
- 固定提交：`e1cc03121a0e71129a4fb730d7c5528a0a3e43c8`。
- 文档正文为 53 行；登记中的四组行号均落在正文范围内。

## 事实、推断、待确认

结果：通过。

- 事实包括 `/add-plugin pstack`、Claude Code 的两步安装命令、`/setup-pstack`、规则文件位置、验证 skill 检查和新会话生效要求。
- 推断单独标记为“模型角色配置通过规则文件持久化”“验证 skill 是项目本地文件”。这些是对正文的解释，不冒充原文断言。
- 待确认保留了当前环境是否安装 Cursor/Claude Code、可用模型和本机 verify skill 状态。

## 证据定位

结果：通过。

- 行 0–13：文档用途、Cursor/Claude Code 安装方式和 Claude 规则文件。
- 行 14–26：`/setup-pstack`、模型角色、reasoning budget、规则文件和继承模型语义。
- 行 27–34：验证 skill、formal verification skill 和新会话生效。
- 行 35–51：成本控制和首个小任务示例。

## 状态闸口

- Evidence：`KG-01 passed`，来源和登记可回读。
- Kernel Validation：`KG-02 pending`，等待独立 QA 复现；本次总控核对不替代 QA。
- 业务 Gate：`not_run`，没有执行安装、配置或外部账号操作。
- QA：`not_run`。

## 回退条件

如果固定提交不可读、行号无法回链或后续 QA 发现登记与正文不一致，任务回退到 `TASK_REWORK`；如果源站不可读且没有可替代版本，进入 `TASK_BLOCKED` 并记录恢复条件。
