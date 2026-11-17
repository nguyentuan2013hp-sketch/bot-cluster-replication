# Pilot 001 Readback

```yaml
task_id: TASK-FM001-PILOT-001
project_id: PROJECT-BOT-CLUSTER-REPLICATION
execution_mode: local_control_plane_simulation
task_state: TASK_ACCEPTANCE_PENDING
evidence_state: K_EVIDENCE_VALID
validation_state: K_VALIDATION_PASSED
business_gate_state: not_run
qa_state: not_run
kernel_gate_state: KG-01=passed, KG-02=passed
owner_binding_status: unbound_for_simulation
latest_evidence: EV-FM001-PILOT-DOCS
staleness: current_for_local_files
next_action: 选择一个真实小功能，接入一个专业 Bot，复现正常/阻塞/证据不足三条路径
rollback_state: TASK_REWORK or TASK_BLOCKED
```

说明：这是只读回读，不创建第二事实源，也不修改业务状态。
