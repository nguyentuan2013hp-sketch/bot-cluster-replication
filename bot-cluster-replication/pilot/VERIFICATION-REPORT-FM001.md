# Pilot 001 Verification Report

验证对象：`TASK-FM001-PILOT-001`

验证方式：独立回读任务、证据回传和回读文件，检查必需字段与状态语义；不把文件存在误判为真实 Bot 执行成功。

## 正常路径

结果：通过。

- Task 字段齐全。
- 输入引用和输出引用存在。
- Evidence Return 包含来源、产物、观察结果、验证状态和返回时间。
- Readback 明确标记了执行模式和限制。

## 缺资料/权限路径

结果：通过规则检查。

如果缺少输入资料、在线权限或测试环境，任务必须转为：

```text
TASK_BLOCKED
```

并填写 `blocked_reason`、补充材料和恢复点；本试点没有伪造缺口已解除。

## 证据不足路径

结果：通过规则检查。

如果只有 Bot 自述或只有启动结果，没有可读产物和可复现检查，任务必须保持：

```text
validation_status: pending
```

不能推进为 `passed`。

## Gate 结果

- KG-01 Evidence：通过，本地证据可读。
- KG-02 Validation：通过，字段和状态规则满足。
- 业务 Gate：未运行，当前试点不代表业务功能上线。
- QA：未运行，当前没有真实站点或外部环境。

## 回退条件

任何证据文件不可读、来源冲突或验证失败时，回退到 `TASK_REWORK` 或 `TASK_BLOCKED`，不得继续推进状态。
