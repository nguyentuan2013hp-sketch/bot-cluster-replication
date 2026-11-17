"""控制面命令行入口：python -m control_plane.cli ..."""

from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

from .engine import ControlPlane, ControlPlaneError


def _json_value(value: str) -> Any:
    return json.loads(value)


def _payload_from_args(file_path: str | None, inline: str | None) -> dict[str, Any]:
    if bool(file_path) == bool(inline):
        raise ValueError("provide exactly one of --file or --json")
    if file_path:
        return json.loads(Path(file_path).read_text(encoding="utf-8"))
    return json.loads(inline or "{}")


def demo() -> dict[str, Any]:
    """在临时 store 中跑通一个完整的正常路径，供人工快速查看。"""

    with tempfile.TemporaryDirectory(prefix="lauren-control-plane-") as folder:
        plane = ControlPlane(Path(folder) / "state.json")
        task_id = "TASK_DEMO_001"
        plane.create_task(
            {
                "task_id": task_id,
                "project_id": "PROJECT_DEMO",
                "agent_role_ref": "builder",
                "task_owner_ref": "local-builder",
                "input_refs": ["brief:demo"],
                "acceptance": ["产物可回读", "证据经过独立检查"],
                "depends_on": [],
                "risk_level": "low",
                "human_confirmation_required": False,
                "output_refs": ["artifact:demo-result"],
                "evidence_return_ids": [],
                "blocked_reason": None,
                "retry_count": 0,
            }
        )
        plane.transition_task(task_id, "TASK_IN_PROGRESS", actor="coordinator", reason="开始执行")
        plane.register_evidence(
            {
                "evidence_return_id": "EVIDENCE_DEMO_001",
                "task_id": task_id,
                "source_object_id": "source:demo",
                "artifact_refs": ["artifact:demo-result"],
                "read_status": "readable",
                "observed_result": "demo result is present",
                "validation_status": "pending",
                "returned_at": "2026-11-17T00:00:00+00:00",
                "returned_by": "local-builder",
            }
        )
        plane.transition_task(
            task_id,
            "TASK_ACCEPTANCE_PENDING",
            actor="builder",
            reason="产物和待核验证据已提交",
        )
        pending = plane.run_validation(task_id)
        plane.verify_evidence(
            "EVIDENCE_DEMO_001",
            verifier="independent-tester",
            note="回读产物引用并确认正文可读",
        )
        passed = plane.run_validation(task_id, actor="independent-tester")
        plane.transition_task(task_id, "TASK_PASSED", actor="coordinator", reason="独立验证通过")
        readback = plane.readback(task_id)
        return {"pending_validation": pending, "passed_validation": passed, "readback": readback}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Lauren 方法控制面")
    parser.add_argument(
        "--store",
        default="runtime/control-plane.json",
        help="唯一事实源 JSON 文件路径（默认：runtime/control-plane.json）",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init", help="创建控制面状态文件")
    sub.add_parser("demo", help="在临时状态文件中跑通正常路径")

    create = sub.add_parser("create-task", help="创建任务")
    create.add_argument("--file")
    create.add_argument("--json")

    evidence = sub.add_parser("register-evidence", help="登记证据回传")
    evidence.add_argument("--file")
    evidence.add_argument("--json")

    verify = sub.add_parser("verify-evidence", help="记录独立证据检查")
    verify.add_argument("task_evidence_id")
    verify.add_argument("--verifier", required=True)
    verify.add_argument("--note", required=True)
    verify.add_argument("--result", choices=["pending", "passed", "failed"], default="passed")

    validate = sub.add_parser("validate", help="运行 KG-03 Validation")
    validate.add_argument("task_id")
    validate.add_argument("--actor", default="kernel-validator")

    auth = sub.add_parser("authorize", help="登记高风险任务授权")
    auth.add_argument("task_id")
    auth.add_argument("--action-type", required=True)
    auth.add_argument("--scope", nargs="+", required=True)
    auth.add_argument("--approved-by", required=True)
    auth.add_argument("--reason", required=True)
    auth.add_argument("--expires-at")

    transition = sub.add_parser("transition", help="通过 Gate 流转任务状态")
    transition.add_argument("task_id")
    transition.add_argument("to_state")
    transition.add_argument("--actor", required=True)
    transition.add_argument("--reason", required=True)
    transition.add_argument("--authorization-id")
    transition.add_argument("--blocked-reason")

    qa = sub.add_parser("qa", help="更新独立 QA 状态")
    qa.add_argument("task_id")
    qa.add_argument("status", choices=["not_started", "pending", "passed", "failed", "blocked"])
    qa.add_argument("--actor", required=True)
    qa.add_argument("--note", required=True)

    readback = sub.add_parser("readback", help="从事实源投影当前任务")
    readback.add_argument("task_id")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "demo":
            result = demo()
        else:
            plane = ControlPlane(args.store)
            if args.command == "init":
                result = plane.initialize()
            elif args.command == "create-task":
                result = plane.create_task(_payload_from_args(args.file, args.json))
            elif args.command == "register-evidence":
                result = plane.register_evidence(_payload_from_args(args.file, args.json))
            elif args.command == "verify-evidence":
                result = plane.verify_evidence(
                    args.task_evidence_id,
                    verifier=args.verifier,
                    note=args.note,
                    result=args.result,
                )
            elif args.command == "validate":
                result = plane.run_validation(args.task_id, actor=args.actor)
            elif args.command == "authorize":
                result = plane.authorize_task(
                    args.task_id,
                    action_type=args.action_type,
                    scope=args.scope,
                    approved_by=args.approved_by,
                    reason=args.reason,
                    expires_at=args.expires_at,
                )
            elif args.command == "transition":
                result = plane.transition_task(
                    args.task_id,
                    args.to_state,
                    actor=args.actor,
                    reason=args.reason,
                    authorization_id=args.authorization_id,
                    blocked_reason=args.blocked_reason,
                )
            elif args.command == "qa":
                result = plane.set_qa_status(
                    args.task_id,
                    args.status,
                    actor=args.actor,
                    note=args.note,
                )
            elif args.command == "readback":
                result = plane.readback(args.task_id)
            else:  # pragma: no cover - argparse prevents this branch
                parser.error(f"unknown command: {args.command}")
                return 2
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (ControlPlaneError, ValueError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
