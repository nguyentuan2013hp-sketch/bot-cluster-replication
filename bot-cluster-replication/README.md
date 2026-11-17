# Lauren 方法验证系统 v0.2

状态：控制面第一版已可在本地运行；未修改现有 Bot 配置，未创建新 Bot，未启用新执行器。

## 目标

把公开资料中的 Agent 工作方法转化为本集群可执行的协作协议：角色清晰、任务可追踪、证据可回读、结果可验证、失败可回退、经验可复用。

## 已核对的依据

- Cursor Compile London 官方议程：Lauren Tan 的主题为 “I Shipped 2,000 PRs Last Month”。
- pstack 官方 setup：按角色配置模型，并将模型规则写入统一规则文件。
- Grok Bot Galaxy Session Book：可作为 workshop 方法参考；原文明确不是官方 xAI 出版物。
- 内部自动化开发站状态闸口登记表：已定义状态命名空间、BG/KG 闸口、Evidence、Validation、Authorization、Activity 和 M15-A/B 回读边界。

## 核心原则

1. 先设计可验证的环境，再增加 Bot 数量。
2. 每个 Bot 只承担明确角色，不把“模型聪明”当作流程控制。
3. 产出与证据同时返回；没有来源或验证结果就保持 pending。
4. 业务完成、QA 通过、Kernel Validation 通过分别记录。
5. 高风险动作停在 Authorization，不由普通任务自动执行。
6. Readback 只能回读事实源，不能创建第二套状态事实。
7. 复盘中只把重复、稳定、已验证的经验沉淀为规则或 Skill。

## 工作流

```mermaid
flowchart TD
    A[用户目标] --> B[总控建立 Task]
    B --> C[角色 Bot 执行]
    C --> D[Evidence Return]
    D --> E[独立 Verification]
    E -->|通过| F[更新 Gate / 状态]
    E -->|失败| G[REWORK / BLOCKED]
    F --> H[Readback 汇总]
    H --> I[复盘与规则沉淀]
    I --> B
```

## 当前试点顺序

1. 总控、研究、开发、测试、知识管理五类角色。
2. 一个小型海外站页面或模块流程。
3. 先验证任务协议、证据回传、失败阻塞和回读。
4. 三类评测：正常、缺资料/权限、证据不足。
5. 通过后再扩展 SEO、增长、内容、商业分析等角色。

## 暂不做

- 不创建或修改 Bot 配置。
- 不绑定未核实的 owner。
- 不注册平台正式状态枚举。
- 不部署、发布、付款、改 DNS 或操作外部账号。
- 不把未读取的外部资料写成已确认事实。

## v0.2 可运行控制面

本仓库现在包含一个本地可运行的控制面第一版。它把 Lauren Tan 公开可核对的工作原则和当前“自动化开发站”闸口登记表连接成一个可追踪的状态机；没有声称复刻任何未公开的内部实现。

```mermaid
flowchart LR
    A[Lauren 公开方法原则] --> B[本地适配层]
    B --> B1[角色边界]
    B --> B2[Task / Evidence 契约]
    B --> B3[独立 QA 与 Kernel Validation]
    B --> B4[失败回退与人工授权]
    B1 --> C[控制面状态机]
    B2 --> C
    B3 --> C
    B4 --> C
    C --> D[唯一事实源 state.json]
    D --> E[Readback 投影]
    E --> F[评测与复盘]
    F --> B
```

一次任务在系统中的顺序是：

```mermaid
sequenceDiagram
    participant C as Coordinator
    participant B as Specialist Bot
    participant E as Evidence Registry
    participant T as Independent Tester
    participant K as Kernel Gates
    C->>C: 建立 Task、依赖、验收和风险
    C->>B: 在边界内执行
    B-->>E: 返回产物、来源、观察结果
    T->>E: 独立回读 Evidence
    E-->>K: KG-02 证据完整性
    K->>K: KG-03 Validation
    K->>K: 必要时 KG-04 Authorization
    K->>K: Persist -> Activity -> Event
    K-->>C: Gate 通过、返工或阻塞
    C->>C: 从唯一事实源 Readback
```

`control_plane/` 已实现：

- Task 契约与登记字段检查；
- Task 状态机和非法流转拒绝；
- Evidence Registry、独立证据核验和 KG-03 Validation；
- 高风险任务的 Authorization 闸口；
- Activity / Event 审计链；
- 从 `state.json` 实时生成的 Readback 投影；
- 不需要第三方依赖的命令行入口。

业务完成、QA 和 Kernel Validation 是三个独立状态；系统不会把其中一个自动改写成另外两个。

快速验证：

```powershell
python -m unittest discover -s tests -v
python -m control_plane.cli demo
```

`demo` 会演示 `TASK_PENDING -> TASK_IN_PROGRESS -> TASK_ACCEPTANCE_PENDING`，先得到 `KG-03 pending`，完成独立证据核验后才得到 `KG-03 passed` 并进入 `TASK_PASSED`。

真实运行时可使用 `runtime/control-plane.json` 作为唯一事实源；该目录已被 Git 忽略，不能写入密码、API Key、Cookie、验证码或私钥。
