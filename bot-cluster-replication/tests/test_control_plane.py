from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from control_plane import ControlPlane, GateError, SchemaError


def task_payload(
    task_id: str = "TASK_001",
    *,
    risk_level: str = "low",
    human_confirmation_required: bool = False,
    evidence_ids: list[str] | None = None,
) -> dict:
    return {
        "task_id": task_id,
        "project_id": "PROJECT_001",
        "agent_role_ref": "builder",
        "task_owner_ref": "builder-01",
        "input_refs": ["brief:001"],
        "acceptance": ["artifact is readable", "evidence is independently checked"],
        "depends_on": [],
        "risk_level": risk_level,
        "human_confirmation_required": human_confirmation_required,
        "output_refs": ["artifact:001"],
        "evidence_return_ids": evidence_ids or [],
        "blocked_reason": None,
        "retry_count": 0,
    }


def evidence_payload(task_id: str, evidence_id: str = "EVIDENCE_001") -> dict:
    return {
        "evidence_return_id": evidence_id,
        "task_id": task_id,
        "source_object_id": "source:001",
        "artifact_refs": ["artifact:001"],
        "read_status": "readable",
        "observed_result": "artifact exists and can be read",
        "validation_status": "pending",
        "returned_at": "2026-11-17T00:00:00+00:00",
        "returned_by": "builder-01",
    }


class ControlPlaneTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.plane = ControlPlane(Path(self.tempdir.name) / "state.json")

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _move_to_acceptance_pending(self, task_id: str = "TASK_001") -> None:
        self.plane.transition_task(task_id, "TASK_IN_PROGRESS", actor="coordinator", reason="start")
        self.plane.register_evidence(evidence_payload(task_id))
        self.plane.transition_task(
            task_id,
            "TASK_ACCEPTANCE_PENDING",
            actor="builder-01",
            reason="submit output",
        )

    def test_normal_path_keeps_business_qa_and_kernel_states_separate(self) -> None:
        self.plane.create_task(task_payload())
        self._move_to_acceptance_pending()
        pending = self.plane.run_validation("TASK_001")
        self.assertEqual(pending["result"], "pending")
        self.assertEqual(self.plane.readback("TASK_001")["separate_statuses"]["qa"], "not_started")

        self.plane.verify_evidence(
            "EVIDENCE_001",
            verifier="tester-01",
            note="read back artifact and source reference",
        )
        passed = self.plane.run_validation("TASK_001", actor="tester-01")
        self.assertEqual(passed["result"], "passed")
        task = self.plane.transition_task(
            "TASK_001",
            "TASK_PASSED",
            actor="coordinator",
            reason="all acceptance evidence passed",
        )
        self.assertEqual(task["status"], "TASK_PASSED")
        self.assertEqual(task["business_completion_status"], "complete")
        self.assertEqual(task["qa_status"], "not_started")
        self.assertEqual(task["kernel_validation_status"], "passed")
        readback = self.plane.readback("TASK_001")
        self.assertEqual(readback["gate_summary"]["KG-02_EVIDENCE_INTEGRITY"], "passed")
        self.assertTrue(readback["activities"])
        self.assertTrue(readback["events"])

    def test_missing_or_pending_evidence_cannot_pass(self) -> None:
        self.plane.create_task(task_payload())
        self.plane.transition_task("TASK_001", "TASK_IN_PROGRESS", actor="coordinator", reason="start")
        with self.assertRaises(GateError):
            self.plane.transition_task(
                "TASK_001",
                "TASK_ACCEPTANCE_PENDING",
                actor="builder-01",
                reason="submit without evidence",
            )

        self.plane.register_evidence(evidence_payload("TASK_001"))
        self.plane.transition_task(
            "TASK_001",
            "TASK_ACCEPTANCE_PENDING",
            actor="builder-01",
            reason="submit with pending evidence",
        )
        with self.assertRaises(GateError):
            self.plane.transition_task(
                "TASK_001",
                "TASK_PASSED",
                actor="coordinator",
                reason="should remain pending",
            )

    def test_high_risk_requires_explicit_authorization(self) -> None:
        self.plane.create_task(
            task_payload(
                "TASK_HIGH",
                risk_level="high",
                human_confirmation_required=True,
            )
        )
        self.plane.transition_task("TASK_HIGH", "TASK_IN_PROGRESS", actor="coordinator", reason="start")
        self.plane.register_evidence(evidence_payload("TASK_HIGH", "EVIDENCE_HIGH"))
        self.plane.transition_task(
            "TASK_HIGH",
            "TASK_ACCEPTANCE_PENDING",
            actor="builder-01",
            reason="submit high-risk output",
        )
        self.plane.verify_evidence(
            "EVIDENCE_HIGH",
            verifier="tester-01",
            note="independent readback",
        )
        with self.assertRaises(GateError):
            self.plane.transition_task(
                "TASK_HIGH",
                "TASK_PASSED",
                actor="coordinator",
                reason="authorization is missing",
            )
        authorization = self.plane.authorize_task(
            "TASK_HIGH",
            action_type="task.acceptance",
            scope=["TASK_PASSED"],
            approved_by="human-owner",
            reason="approved for this bounded task only",
        )
        task = self.plane.transition_task(
            "TASK_HIGH",
            "TASK_PASSED",
            actor="coordinator",
            reason="authorization and validation passed",
            authorization_id=authorization["authorization_id"],
        )
        self.assertEqual(task["status"], "TASK_PASSED")

    def test_illegal_transition_is_rejected_without_mutating_task(self) -> None:
        self.plane.create_task(task_payload())
        with self.assertRaises(GateError):
            self.plane.transition_task("TASK_001", "TASK_PASSED", actor="coordinator", reason="skip gates")
        self.assertEqual(self.plane.readback("TASK_001")["task"]["status"], "TASK_PENDING")

    def test_schema_requires_the_contract_fields(self) -> None:
        with self.assertRaises(SchemaError):
            self.plane.create_task({"task_id": "TASK_BAD"})

        bypass = task_payload("TASK_BYPASS")
        bypass["status"] = "TASK_PASSED"
        with self.assertRaises(SchemaError):
            self.plane.create_task(bypass)

    def test_unreadable_evidence_cannot_be_marked_passed(self) -> None:
        self.plane.create_task(task_payload())
        self.plane.transition_task("TASK_001", "TASK_IN_PROGRESS", actor="coordinator", reason="start")
        unreadable = evidence_payload("TASK_001", "EVIDENCE_UNREADABLE")
        unreadable["read_status"] = "partial"
        self.plane.register_evidence(unreadable)
        with self.assertRaises(GateError):
            self.plane.verify_evidence(
                "EVIDENCE_UNREADABLE",
                verifier="tester-01",
                note="cannot verify a partial source",
            )

    def test_state_is_persisted_and_readback_is_a_projection(self) -> None:
        self.plane.create_task(task_payload())
        reloaded = ControlPlane(Path(self.tempdir.name) / "state.json")
        self.assertEqual(reloaded.readback("TASK_001")["task"]["task_id"], "TASK_001")
        raw = json.loads((Path(self.tempdir.name) / "state.json").read_text(encoding="utf-8"))
        self.assertNotIn("readback", raw)


if __name__ == "__main__":
    unittest.main()
