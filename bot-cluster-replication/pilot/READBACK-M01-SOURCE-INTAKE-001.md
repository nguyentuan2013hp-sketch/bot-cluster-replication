# M01 Readback

```yaml
task_id: TASK-M01-SOURCE-INTAKE-001
project_id: PROJECT-BOT-CLUSTER-REPLICATION
execution_mode: current_group_direct_source_read
task_state: TASK_QA_PENDING
evidence_state: K_EVIDENCE_VALID
validation_state: K_VALIDATION_PENDING
business_gate_state: not_run
qa_state: not_run
kernel_gate_state: KG-01=passed, KG-02=pending
owner_binding_status: bound_to_fin_current_group
latest_evidence: EV-M01-SOURCE-INTAKE-001
source_commit: e1cc03121a0e71129a4fb730d7c5528a0a3e43c8
staleness: current_for_checked_commit
next_action: 独立 QA 复现来源读取、证据行号和三类阻塞规则后再决定是否通过
rollback_state: TASK_REWORK or TASK_BLOCKED
```

说明：这是源对象的只读投影，不创建第二事实源；当前不表示已安装或配置 pstack。本轮没有调用其他群组 Bot。
