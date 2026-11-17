# Pilot 001：资料到可验证开发任务

状态：控制面试运行样例；已完成本地文档链路验证，尚未连接真实在线 Bot 派单。

本试点验证一件事：一个功能是否可以从输入资料建立 Task，经过角色执行、证据回传、独立验证，最后形成可读的状态回读。

## 链路

```text
输入资料
  -> TASK-FM001.yaml
  -> EVIDENCE-RETURN-FM001.yaml
  -> VERIFICATION-REPORT-FM001.md
  -> READBACK-FM001.md
```

## 结论

- 正常路径：通过。
- 缺资料/权限路径：能够进入 BLOCKED，并记录恢复条件。
- 证据不足路径：保持 pending，不推进为 passed。
- 当前 Gate：控制面试运行通过；真实 Bot 集群接入仍待下一阶段。

## M01：资料入库与来源登记

M01 使用 pstack 官方 setup 文档作为真实资料，已完成专业 Bot 的来源读取与登记，并由总控按固定提交核对正文和证据行号。

- 任务卡：`TASK-M01-SOURCE-INTAKE-001.yaml`
- 证据回传：`EVIDENCE-RETURN-M01-SOURCE-INTAKE-001.yaml`
- 验证报告：`VERIFICATION-REPORT-M01-SOURCE-INTAKE-001.md`
- 状态回读：`READBACK-M01-SOURCE-INTAKE-001.md`
- 可重复检查：`scripts/validate-m01-source.ps1`

当前状态：来源证据可读，证据状态通过；独立 QA 尚未运行，因此任务整体仍保持 `pending`，没有推进为业务通过。
