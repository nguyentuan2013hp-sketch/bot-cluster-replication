# 集群级 AGENTS 规则草案

- 默认只读；只在任务范围内修改当前工作区。
- 所有结论区分事实、推断和待确认。
- 没有来源、证据或验证结果时不得标记通过。
- 任务必须携带 input_refs、acceptance、owner_ref、output_refs 和 evidence_return。
- 适配器只能生成待审核任务或 WriteIntent，不能直接写 verified、release 或 external_submitted。
- 高风险动作必须先有人工授权；授权不能替代 QA、Evidence 或 Validation。
- 失败必须保留事实、错误信息和回退状态。
- 不写入密码、API Key、Cookie、验证码或私钥。
- Readback 只能读取源对象投影，不建立第二事实源。
- 只有经过评测并在复盘中确认稳定的规则，才沉淀为 Skill 或长期规范。
