# VERIFICATION

## 验证顺序

1. 检查来源和版本是否可读。
2. 检查 Task 的输入、依赖、owner 和验收标准。
3. 检查产物是否在声明位置生成。
4. 运行与目标行为相关的测试或检查。
5. 保存日志、截图、测试结果或可回读链接。
6. 分别记录业务结果、QA 结果和 Kernel Validation 结果。
7. 失败时记录失败原因、回退状态和恢复条件。

## 最小证据包

```yaml
source_refs: []
input_refs: []
output_refs: []
command_or_action: ''
observed_result: ''
validation_status: pending
blocker_reason: null
rollback_state: null
verified_at: ''
```

## 禁止的捷径

- 启动成功不等于功能通过。
- QA 通过不等于 Kernel Validation 通过。
- Bot 自述完成不等于可验证完成。
- 缺来源时不得补猜流量、价格、用户数据或平台状态。
