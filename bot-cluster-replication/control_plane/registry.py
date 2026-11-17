"""候选状态与 Gate 注册表。

这些键来自仓库中的自动化开发站登记表，属于本地控制面候选键，
不是任何外部平台已经注册的正式枚举。
"""

TASK_STATES = {
    "TASK_PENDING",
    "TASK_IN_PROGRESS",
    "TASK_BLOCKED",
    "TASK_ACCEPTANCE_PENDING",
    "TASK_PASSED",
    "TASK_REWORK",
    "TASK_PAUSED",
}

TASK_TRANSITIONS = {
    "TASK_PENDING": {
        "TASK_IN_PROGRESS",
        "TASK_BLOCKED",
        "TASK_PAUSED",
    },
    "TASK_IN_PROGRESS": {
        "TASK_ACCEPTANCE_PENDING",
        "TASK_BLOCKED",
        "TASK_PAUSED",
    },
    "TASK_BLOCKED": {
        "TASK_PENDING",
        "TASK_IN_PROGRESS",
        "TASK_PAUSED",
    },
    "TASK_ACCEPTANCE_PENDING": {
        "TASK_PASSED",
        "TASK_REWORK",
        "TASK_BLOCKED",
    },
    "TASK_PASSED": {
        "TASK_ACCEPTANCE_PENDING",
        "TASK_REWORK",
    },
    "TASK_REWORK": {
        "TASK_IN_PROGRESS",
        "TASK_BLOCKED",
        "TASK_PAUSED",
    },
    "TASK_PAUSED": {
        "TASK_PENDING",
    },
}

READ_STATUSES = {"readable", "partial", "unreadable"}
VALIDATION_STATUSES = {"pending", "passed", "failed"}
QA_STATUSES = {"not_started", "pending", "passed", "failed", "blocked"}

KERNEL_GATES = (
    "KG-01_STATE_TRANSITION",
    "KG-02_EVIDENCE_INTEGRITY",
    "KG-03_VALIDATION",
    "KG-04_AUTHORIZATION",
    "KG-05_ACTIVITY_AUDIT",
    "KG-06_EVENT_SYNC",
)

BUSINESS_GATES = (
    "BG-00_SOURCE_INTAKE",
    "BG-01_OPPORTUNITY",
    "BG-02_PRD_MVP",
    "BG-03_PRICING_COMPLIANCE",
    "BG-04_DESIGN",
    "BG-05_DEVELOPMENT_HANDOFF",
    "BG-06_QA",
    "BG-07_LAUNCH_AUTHORIZATION",
    "BG-08_DATA_RETROSPECTIVE",
)


def task_transition_allowed(from_state: str, to_state: str) -> bool:
    """Return whether a task transition is registered in the local registry."""

    return to_state in TASK_TRANSITIONS.get(from_state, set())
