# FEATURE_MAP

## 功能条目格式

每项功能必须记录：入口、输入、角色、允许动作、禁止动作、输出、证据、验证题、失败回退。

## 试点功能：资料到可验证开发任务

| 字段 | 内容 |
|---|---|
| feature_id | FM-001 |
| 入口 | 用户目标或已登记项目 |
| 输入 | Brief、SourceMaterial、RequirementDoc、已有状态 |
| 主要角色 | 总控、研究、开发、测试、知识管理 |
| 输出 | Task、实现产物、QAReport、EvidenceReturn、ReadbackView |
| 允许动作 | 读取资料、生成草稿、修改试点工作区、运行测试、回传证据 |
| 禁止动作 | 无授权外发、付款、部署、登录、改 DNS、直接写 verified |
| 通过条件 | 输入/输出可回链；测试证据可读；失败状态明确；没有编造数据 |
| 失败回退 | TASK_REWORK、TASK_BLOCKED 或 K_GATE_REVIEW |

## 后续功能条目

- FM-002：需求到 PRD/验收标准
- FM-003：设计到前端交接
- FM-004：开发到 QA 回归
- FM-005：数据/埋点到复盘
- FM-006：复盘到 Skill/规则草稿
