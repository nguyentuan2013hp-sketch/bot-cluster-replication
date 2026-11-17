"""可审计的 Lauren 方法控制面最小实现。

实现目标不是复刻任何未公开的内部系统，而是把已核对的原则落成一个
可运行、可回读、可测试的本地状态机：

    Task -> Evidence -> independent Validation -> Authorization (if needed)
          -> Persist -> Activity -> Event -> Readback projection

状态文件是唯一事实源。Readback 每次都从状态文件实时投影，不另存一份
可被误认为事实的“汇总状态”。
"""

from __future__ import annotations

import copy
import json
import os
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .registry import (
    QA_STATUSES,
    READ_STATUSES,
    TASK_STATES,
    VALIDATION_STATUSES,
    task_transition_allowed,
)


SCHEMA_VERSION = "0.1"
TASK_REQUIRED_FIELDS = (
    "task_id",
    "project_id",
    "agent_role_ref",
    "task_owner_ref",
    "input_refs",
    "acceptance",
    "depends_on",
    "risk_level",
    "human_confirmation_required",
    "output_refs",
    "evidence_return_ids",
    "blocked_reason",
    "retry_count",
)
EVIDENCE_REQUIRED_FIELDS = (
    "evidence_return_id",
    "source_object_id",
    "artifact_refs",
    "read_status",
    "observed_result",
    "validation_status",
    "returned_at",
)


class ControlPlaneError(Exception):
    """预期中的控制面拒绝。"""


class SchemaError(ControlPlaneError):
    """输入对象不符合控制面契约。"""


class GateError(ControlPlaneError):
    """某个状态或 Gate 不允许继续。"""


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _empty_state() -> dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "tasks": {},
        "evidence": {},
        "validation_runs": {},
        "authorizations": {},
        "activities": [],
        "events": [],
    }


def _ensure_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list):
        raise SchemaError(f"{field} must be a list")
    return value


class ControlPlane:
    """持久化控制面。

    ``store_path`` 可以放在项目的 runtime 目录中。该文件只包含任务、证据
    和审计状态，不应放入密码、Cookie、API Key 或其他凭据。
    """

    def __init__(self, store_path: str | os.PathLike[str]):
        self.store_path = Path(store_path)
        self.state = self._load()

    def _load(self) -> dict[str, Any]:
        if not self.store_path.exists():
            return _empty_state()
        try:
            loaded = json.loads(self.store_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ControlPlaneError(f"invalid state file: {self.store_path}") from exc
        if not isinstance(loaded, dict) or loaded.get("schema_version") != SCHEMA_VERSION:
            raise ControlPlaneError("unsupported or missing control-plane schema_version")
        state = _empty_state()
        state.update(loaded)
        return state

    def _save(self) -> None:
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        payload = json.dumps(self.state, ensure_ascii=False, indent=2) + "\n"
        fd, tmp_name = tempfile.mkstemp(
            prefix=f".{self.store_path.name}.",
            suffix=".tmp",
            dir=str(self.store_path.parent),
            text=True,
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp_name, self.store_path)
        finally:
            if os.path.exists(tmp_name):
                os.unlink(tmp_name)

    def initialize(self) -> dict[str, Any]:
        """Create the store if it does not exist and return its snapshot."""

        if not self.store_path.exists():
            self._save()
        return self.snapshot()

    def snapshot(self) -> dict[str, Any]:
        return copy.deepcopy(self.state)

    def create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        task = self._normalize_task(payload)
        task_id = task["task_id"]
        if task_id in self.state["tasks"]:
            raise SchemaError(f"task already exists: {task_id}")
        self.state["tasks"][task_id] = task
        self._record_activity(
            event_type="task.created",
            target_type="task",
            target_id=task_id,
            before_state=None,
            after_state=task["status"],
            reason="task created",
            actor_id=task.get("task_owner_ref"),
            request_id=task.get("task_id"),
        )
        self._append_event("task.created", "task", task_id, {"status": task["status"]})
        self._save()
        return copy.deepcopy(task)

    def register_evidence(self, payload: dict[str, Any]) -> dict[str, Any]:
        evidence = self._normalize_evidence(payload)
        evidence_id = evidence["evidence_return_id"]
        if evidence_id in self.state["evidence"]:
            raise SchemaError(f"evidence already exists: {evidence_id}")
        task_id = evidence.get("task_id")
        if task_id and task_id not in self.state["tasks"]:
            raise SchemaError(f"evidence references unknown task: {task_id}")
        self.state["evidence"][evidence_id] = evidence
        if task_id and evidence_id not in self.state["tasks"][task_id]["evidence_return_ids"]:
            self.state["tasks"][task_id]["evidence_return_ids"].append(evidence_id)
        self._record_activity(
            event_type="evidence.registered",
            target_type="evidence",
            target_id=evidence_id,
            before_state=None,
            after_state=evidence["validation_status"],
            reason="evidence registered",
            actor_id=evidence.get("returned_by"),
            request_id=evidence_id,
        )
        self._append_event("evidence.registered", "evidence", evidence_id, {"task_id": task_id})
        self._save()
        return copy.deepcopy(evidence)

    def verify_evidence(
        self,
        evidence_id: str,
        verifier: str,
        note: str,
        *,
        result: str = "passed",
    ) -> dict[str, Any]:
        """登记一次独立证据检查。

        这一步只做结构和可回读性检查；它不会把业务 QA 或 Kernel Validation
        混成同一个状态。调用方必须明确给出 verifier 和检查备注。
        """

        evidence = self._get_evidence(evidence_id)
        if result not in VALIDATION_STATUSES:
            raise SchemaError(f"invalid evidence validation result: {result}")
        if not verifier or not note:
            raise SchemaError("verifier and note are required for evidence verification")
        if result == "passed" and (
            evidence["read_status"] != "readable" or not evidence["artifact_refs"]
        ):
            raise GateError("unreadable evidence cannot be independently verified as passed")
        before = evidence["validation_status"]
        evidence["validation_status"] = result
        evidence["verified_by"] = verifier
        evidence["verified_at"] = utc_now()
        evidence["verification_note"] = note
        self._record_activity(
            event_type="evidence.verified",
            target_type="evidence",
            target_id=evidence_id,
            before_state=before,
            after_state=result,
            reason=note,
            actor_id=verifier,
            request_id=evidence_id,
        )
        self._append_event(
            "evidence.verified",
            "evidence",
            evidence_id,
            {"result": result, "verified_by": verifier},
        )
        self._save()
        return copy.deepcopy(evidence)

    def run_validation(self, task_id: str, *, actor: str = "kernel-validator") -> dict[str, Any]:
        """运行 KG-03 的最小规则集并保存 ValidationRun。"""

        task = self._get_task(task_id)
        result, issues = self._evaluate_task(task)
        run = {
            "validation_run_id": new_id("VR"),
            "target_type": "task",
            "target_id": task_id,
            "gate_id": "KG-03_VALIDATION",
            "rule_version": "control-plane-0.1",
            "evidence_ids": list(task["evidence_return_ids"]),
            "result": result,
            "issues": issues,
            "started_at": utc_now(),
            "finished_at": utc_now(),
            "actor_ref": actor,
        }
        self.state["validation_runs"][run["validation_run_id"]] = run
        before = task.get("kernel_validation_status", "pending")
        task["kernel_validation_status"] = result
        self._record_activity(
            event_type="validation.completed",
            target_type="task",
            target_id=task_id,
            before_state=before,
            after_state=result,
            reason="KG-03 validation run",
            actor_id=actor,
            request_id=run["validation_run_id"],
        )
        self._append_event(
            "validation.completed",
            "task",
            task_id,
            {"validation_run_id": run["validation_run_id"], "result": result},
        )
        self._save()
        return copy.deepcopy(run)

    def authorize_task(
        self,
        task_id: str,
        *,
        action_type: str,
        scope: Iterable[str],
        approved_by: str,
        reason: str,
        expires_at: str | None = None,
    ) -> dict[str, Any]:
        """登记一条高风险动作授权，不执行任何外部动作。"""

        self._get_task(task_id)
        scope_list = list(scope)
        if not action_type or not scope_list or not approved_by or not reason:
            raise SchemaError("action_type, scope, approved_by and reason are required")
        authorization = {
            "authorization_id": new_id("AUTH"),
            "target_type": "task",
            "target_id": task_id,
            "action_type": action_type,
            "scope": scope_list,
            "status": "approved",
            "approved_by": approved_by,
            "reason": reason,
            "requested_at": utc_now(),
            "approved_at": utc_now(),
            "expires_at": expires_at,
        }
        self.state["authorizations"][authorization["authorization_id"]] = authorization
        self._record_activity(
            event_type="authorization.approved",
            target_type="task",
            target_id=task_id,
            before_state="pending",
            after_state="approved",
            reason=reason,
            actor_id=approved_by,
            request_id=authorization["authorization_id"],
        )
        self._append_event(
            "authorization.approved",
            "task",
            task_id,
            {"authorization_id": authorization["authorization_id"], "scope": scope_list},
        )
        self._save()
        return copy.deepcopy(authorization)

    def transition_task(
        self,
        task_id: str,
        to_state: str,
        *,
        actor: str,
        reason: str,
        authorization_id: str | None = None,
        blocked_reason: str | None = None,
    ) -> dict[str, Any]:
        """执行统一状态流转闸口。

        失败时不改变任务状态；已经产生的验证记录会保留，便于审计失败原因。
        """

        task = self._get_task(task_id)
        from_state = task["status"]
        if to_state not in TASK_STATES:
            raise GateError(f"unknown task state: {to_state}")
        if not task_transition_allowed(from_state, to_state):
            raise GateError(f"KG-01 rejected transition {from_state} -> {to_state}")
        if not actor or not reason:
            raise SchemaError("actor and reason are required for a state transition")

        if to_state == "TASK_BLOCKED" and blocked_reason:
            task["blocked_reason"] = blocked_reason
        elif from_state == "TASK_BLOCKED" and to_state != "TASK_BLOCKED":
            task["blocked_reason"] = None
        if to_state == "TASK_IN_PROGRESS":
            self._require_task_ready(task)
        if to_state == "TASK_BLOCKED" and not task.get("blocked_reason"):
            raise GateError("TASK_BLOCKED requires task.blocked_reason")
        if to_state == "TASK_REWORK" and not reason:
            raise GateError("TASK_REWORK requires a reason")
        if to_state == "TASK_ACCEPTANCE_PENDING":
            self._require_evidence_refs(task, allow_pending=True)
            if not task["output_refs"]:
                raise GateError("acceptance pending requires output_refs")
        if to_state == "TASK_PASSED":
            self._require_evidence_refs(task, allow_pending=False)
            run = self.run_validation(task_id, actor=actor)
            if run["result"] != "passed":
                raise GateError(
                    "KG-03 rejected TASK_PASSED: "
                    + ", ".join(issue["code"] for issue in run["issues"])
                )
            self._require_authorization_if_needed(
                task,
                to_state=to_state,
                authorization_id=authorization_id,
            )

        before = task["status"]
        task["status"] = to_state
        task["last_updated_at"] = utc_now()
        task["last_transition_reason"] = reason
        task["last_transition_actor"] = actor
        if to_state == "TASK_PASSED":
            task["business_completion_status"] = "complete"
        elif to_state == "TASK_BLOCKED":
            task["business_completion_status"] = "blocked"
        elif to_state in {"TASK_PENDING", "TASK_IN_PROGRESS", "TASK_REWORK"}:
            task["business_completion_status"] = "pending"

        self._record_activity(
            event_type="task.transitioned",
            target_type="task",
            target_id=task_id,
            before_state=before,
            after_state=to_state,
            reason=reason,
            actor_id=actor,
            request_id=new_id("REQ"),
        )
        self._append_event(
            "task.transitioned",
            "task",
            task_id,
            {"from_state": before, "to_state": to_state},
        )
        self._save()
        return copy.deepcopy(task)

    def set_qa_status(self, task_id: str, status: str, *, actor: str, note: str) -> dict[str, Any]:
        """更新业务 QA 状态；不会直接修改 Kernel Validation。"""

        if status not in QA_STATUSES:
            raise SchemaError(f"invalid QA status: {status}")
        task = self._get_task(task_id)
        before = task["qa_status"]
        task["qa_status"] = status
        task["qa_note"] = note
        task["qa_updated_at"] = utc_now()
        self._record_activity(
            event_type="qa.status_changed",
            target_type="task",
            target_id=task_id,
            before_state=before,
            after_state=status,
            reason=note,
            actor_id=actor,
            request_id=new_id("REQ"),
        )
        self._append_event("qa.status_changed", "task", task_id, {"status": status})
        self._save()
        return copy.deepcopy(task)

    def readback(self, task_id: str) -> dict[str, Any]:
        """从唯一事实源投影任务当前状态、Gate 结果和审计链。"""

        task = self._get_task(task_id)
        evidence = [
            copy.deepcopy(item)
            for item in self.state["evidence"].values()
            if item.get("task_id") == task_id or item["evidence_return_id"] in task["evidence_return_ids"]
        ]
        validations = [
            copy.deepcopy(item)
            for item in self.state["validation_runs"].values()
            if item["target_type"] == "task" and item["target_id"] == task_id
        ]
        authorizations = [
            copy.deepcopy(item)
            for item in self.state["authorizations"].values()
            if item["target_type"] == "task" and item["target_id"] == task_id
        ]
        activities = [
            copy.deepcopy(item)
            for item in self.state["activities"]
            if item["target_type"] == "task" and item["target_id"] == task_id
        ]
        events = [
            copy.deepcopy(item)
            for item in self.state["events"]
            if item["target_type"] == "task" and item["target_id"] == task_id
        ]
        return {
            "schema_version": SCHEMA_VERSION,
            "task": copy.deepcopy(task),
            "evidence": evidence,
            "validation_runs": validations,
            "authorizations": authorizations,
            "activities": activities,
            "events": events,
            "gate_summary": {
                "KG-01_STATE_TRANSITION": (
                    "passed"
                    if any(item["event_type"] == "task.transitioned" for item in activities)
                    else "pending"
                ),
                "KG-02_EVIDENCE_INTEGRITY": self._evidence_gate_result(task),
                "KG-03_VALIDATION": task["kernel_validation_status"],
                "KG-04_AUTHORIZATION": self._authorization_gate_result(task_id),
                "KG-05_ACTIVITY_AUDIT": "passed" if activities else "pending",
                "KG-06_EVENT_SYNC": "passed" if events else "pending",
            },
            "separate_statuses": {
                "business_completion": task["business_completion_status"],
                "qa": task["qa_status"],
                "kernel_validation": task["kernel_validation_status"],
            },
        }

    def _normalize_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise SchemaError("task payload must be an object")
        missing = [field for field in TASK_REQUIRED_FIELDS if field not in payload]
        if missing:
            raise SchemaError("missing task fields: " + ", ".join(missing))
        task = copy.deepcopy(payload)
        if not task["task_id"] or not task["project_id"] or not task["agent_role_ref"]:
            raise SchemaError("task_id, project_id and agent_role_ref are required")
        for field in ("input_refs", "acceptance", "depends_on", "output_refs", "evidence_return_ids"):
            _ensure_list(task[field], field)
        if task["risk_level"] not in {"low", "medium", "high"}:
            raise SchemaError("risk_level must be low, medium or high")
        if not isinstance(task["human_confirmation_required"], bool):
            raise SchemaError("human_confirmation_required must be boolean")
        if not isinstance(task["retry_count"], int) or task["retry_count"] < 0:
            raise SchemaError("retry_count must be a non-negative integer")
        if task["risk_level"] == "high" and not task["human_confirmation_required"]:
            raise SchemaError("high-risk tasks must require human confirmation")
        status = task.get("status", "TASK_PENDING")
        if status not in TASK_STATES:
            raise SchemaError(f"invalid initial task status: {status}")
        if status != "TASK_PENDING":
            raise SchemaError("new tasks must start in TASK_PENDING")
        task["status"] = status
        if task.get("blocked_reason") is not None and not isinstance(task["blocked_reason"], str):
            raise SchemaError("blocked_reason must be a string or null")
        task.setdefault("business_completion_status", "blocked" if status == "TASK_BLOCKED" else "pending")
        task.setdefault("qa_status", "not_started")
        task.setdefault("kernel_validation_status", "pending")
        task.setdefault("created_at", utc_now())
        task.setdefault("last_updated_at", task["created_at"])
        return task

    def _normalize_evidence(self, payload: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(payload, dict):
            raise SchemaError("evidence payload must be an object")
        missing = [field for field in EVIDENCE_REQUIRED_FIELDS if field not in payload]
        if missing:
            raise SchemaError("missing evidence fields: " + ", ".join(missing))
        evidence = copy.deepcopy(payload)
        _ensure_list(evidence["artifact_refs"], "artifact_refs")
        if not evidence["evidence_return_id"] or not evidence["source_object_id"]:
            raise SchemaError("evidence_return_id and source_object_id are required")
        if evidence["read_status"] not in READ_STATUSES:
            raise SchemaError(f"invalid read_status: {evidence['read_status']}")
        if evidence["validation_status"] not in VALIDATION_STATUSES:
            raise SchemaError(f"invalid validation_status: {evidence['validation_status']}")
        if evidence["validation_status"] != "pending":
            raise SchemaError("new evidence must start with validation_status=pending")
        if not evidence["observed_result"]:
            raise SchemaError("observed_result is required")
        evidence.setdefault("captured_at", utc_now())
        return evidence

    def _get_task(self, task_id: str) -> dict[str, Any]:
        try:
            return self.state["tasks"][task_id]
        except KeyError as exc:
            raise ControlPlaneError(f"unknown task: {task_id}") from exc

    def _get_evidence(self, evidence_id: str) -> dict[str, Any]:
        try:
            return self.state["evidence"][evidence_id]
        except KeyError as exc:
            raise ControlPlaneError(f"unknown evidence: {evidence_id}") from exc

    def _require_task_ready(self, task: dict[str, Any]) -> None:
        if not task.get("task_owner_ref"):
            raise GateError("KG-01 requires a task_owner_ref before execution")
        for dependency in task["depends_on"]:
            dependency_task = self.state["tasks"].get(dependency)
            if not dependency_task or dependency_task["status"] != "TASK_PASSED":
                raise GateError(f"dependency is not passed: {dependency}")

    def _require_evidence_refs(self, task: dict[str, Any], *, allow_pending: bool) -> None:
        if not task["evidence_return_ids"]:
            raise GateError("KG-02 requires evidence_return_ids")
        for evidence_id in task["evidence_return_ids"]:
            evidence = self.state["evidence"].get(evidence_id)
            if not evidence:
                raise GateError(f"KG-02 missing evidence: {evidence_id}")
            if evidence["read_status"] != "readable":
                raise GateError(f"KG-02 evidence is not readable: {evidence_id}")
            if evidence["validation_status"] == "failed":
                raise GateError(f"KG-02 evidence verification failed: {evidence_id}")
            if not allow_pending and evidence["validation_status"] != "passed":
                raise GateError(f"KG-02 evidence is not independently verified: {evidence_id}")

    def _evaluate_task(self, task: dict[str, Any]) -> tuple[str, list[dict[str, str]]]:
        issues: list[dict[str, str]] = []
        if not task.get("input_refs"):
            issues.append({"code": "INPUT_MISSING", "severity": "failed"})
        if not task.get("acceptance"):
            issues.append({"code": "ACCEPTANCE_MISSING", "severity": "failed"})
        if not task.get("evidence_return_ids"):
            issues.append({"code": "EVIDENCE_MISSING", "severity": "failed"})
        if not task.get("task_owner_ref"):
            issues.append({"code": "OWNER_MISSING", "severity": "pending"})
        if task.get("blocked_reason"):
            issues.append({"code": "TASK_BLOCKED", "severity": "failed"})
        for evidence_id in task.get("evidence_return_ids", []):
            evidence = self.state["evidence"].get(evidence_id)
            if not evidence:
                issues.append({"code": f"EVIDENCE_MISSING:{evidence_id}", "severity": "failed"})
                continue
            if evidence["read_status"] != "readable":
                issues.append({"code": f"EVIDENCE_UNREADABLE:{evidence_id}", "severity": "failed"})
            if evidence["validation_status"] == "pending":
                issues.append({"code": f"EVIDENCE_PENDING:{evidence_id}", "severity": "pending"})
            elif evidence["validation_status"] == "failed":
                issues.append({"code": f"EVIDENCE_FAILED:{evidence_id}", "severity": "failed"})
        if any(issue["severity"] == "failed" for issue in issues):
            return "failed", issues
        if any(issue["severity"] == "pending" for issue in issues):
            return "pending", issues
        return "passed", issues

    def _require_authorization_if_needed(
        self,
        task: dict[str, Any],
        *,
        to_state: str,
        authorization_id: str | None,
    ) -> None:
        if task["risk_level"] != "high" and not task["human_confirmation_required"]:
            return
        if not authorization_id:
            raise GateError("KG-04 requires an approved authorization for this task")
        authorization = self.state["authorizations"].get(authorization_id)
        if not authorization:
            raise GateError(f"unknown authorization: {authorization_id}")
        if authorization["target_id"] != task["task_id"] or authorization["status"] != "approved":
            raise GateError("authorization target or status is invalid")
        if to_state not in authorization["scope"] and "TASK_PASSED" not in authorization["scope"]:
            raise GateError("authorization scope does not include the requested transition")
        expires_at = authorization.get("expires_at")
        if expires_at and expires_at <= utc_now():
            raise GateError("authorization is expired")

    def _evidence_gate_result(self, task: dict[str, Any]) -> str:
        if not task["evidence_return_ids"]:
            return "missing"
        statuses = []
        for evidence_id in task["evidence_return_ids"]:
            evidence = self.state["evidence"].get(evidence_id)
            if not evidence:
                return "missing"
            if evidence["read_status"] != "readable":
                return "failed"
            statuses.append(evidence["validation_status"])
        if "failed" in statuses:
            return "failed"
        if "pending" in statuses:
            return "pending"
        return "passed"

    def _authorization_gate_result(self, task_id: str) -> str:
        authorizations = [
            item
            for item in self.state["authorizations"].values()
            if item["target_type"] == "task" and item["target_id"] == task_id
        ]
        if not authorizations:
            task = self._get_task(task_id)
            return "not_required" if task["risk_level"] != "high" and not task["human_confirmation_required"] else "pending"
        if any(item["status"] == "approved" for item in authorizations):
            return "passed"
        return "failed"

    def _record_activity(
        self,
        *,
        event_type: str,
        target_type: str,
        target_id: str,
        before_state: str | None,
        after_state: str | None,
        reason: str,
        actor_id: str | None,
        request_id: str,
    ) -> dict[str, Any]:
        activity = {
            "activity_id": new_id("ACT"),
            "event_type": event_type,
            "target_type": target_type,
            "target_id": target_id,
            "before_state": before_state,
            "after_state": after_state,
            "reason": reason,
            "actor_id": actor_id,
            "request_id": request_id,
            "occurred_at": utc_now(),
        }
        self.state["activities"].append(activity)
        return activity

    def _append_event(self, event_type: str, target_type: str, target_id: str, data: dict[str, Any]) -> None:
        self.state["events"].append(
            {
                "event_id": new_id("EVT"),
                "event_type": event_type,
                "target_type": target_type,
                "target_id": target_id,
                "data": copy.deepcopy(data),
                "occurred_at": utc_now(),
            }
        )

