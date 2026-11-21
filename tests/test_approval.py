import pytest

from ai_automation_agents.approval import ApprovalGate
from ai_automation_agents.fakes import FakeExecutor
from ai_automation_agents.recipes.approval_actor import ApprovalGatedActor, PlannedAction


def test_propose_creates_pending_proposal_and_receipt() -> None:
    gate = ApprovalGate()
    proposal = gate.propose("send_report", {"to": "team@example.com"})
    assert proposal.status == "pending"
    assert gate.pending() == [proposal]
    assert gate.log.entries[0].event == "proposed"


def test_approve_then_execute_runs_executor_once() -> None:
    gate = ApprovalGate()
    executor = FakeExecutor()
    proposal = gate.propose("archive_files", {"count": 3})
    gate.approve(proposal.id)
    result = gate.execute(proposal.id, executor)
    assert result["status"] == "ok"
    assert executor.calls == [("archive_files", {"count": 3})]
    assert gate.get(proposal.id).status == "executed"


def test_denied_proposal_can_never_execute() -> None:
    gate = ApprovalGate()
    proposal = gate.propose("delete_records", {"table": "drafts"})
    gate.deny(proposal.id)
    with pytest.raises(ValueError, match="only approved"):
        gate.execute(proposal.id, FakeExecutor())


def test_pending_proposal_cannot_execute() -> None:
    gate = ApprovalGate()
    proposal = gate.propose("send_report")
    with pytest.raises(ValueError, match="only approved"):
        gate.execute(proposal.id, FakeExecutor())


def test_deciding_twice_raises() -> None:
    gate = ApprovalGate()
    proposal = gate.propose("send_report")
    gate.approve(proposal.id)
    with pytest.raises(ValueError, match="only pending"):
        gate.deny(proposal.id)


def test_unknown_proposal_raises_key_error() -> None:
    gate = ApprovalGate()
    with pytest.raises(KeyError):
        gate.get("does-not-exist")


def test_receipt_chain_links_and_verifies() -> None:
    gate = ApprovalGate()
    proposal = gate.propose("send_report")
    gate.approve(proposal.id)
    gate.execute(proposal.id, FakeExecutor())
    entries = gate.log.entries
    assert [entry.event for entry in entries] == ["proposed", "approved", "executed"]
    assert entries[1].prev_hash == entries[0].hash
    assert entries[2].prev_hash == entries[1].hash
    assert gate.log.verify() is True


def test_tampering_with_receipt_history_breaks_verification() -> None:
    gate = ApprovalGate()
    proposal = gate.propose("send_report", {"to": "team@example.com"})
    gate.approve(proposal.id)
    assert gate.log.verify() is True
    gate.log.entries[0].data["action"] = "delete_everything"
    assert gate.log.verify() is False


def test_actor_runs_only_approved_actions() -> None:
    actor = ApprovalGatedActor()
    executor = FakeExecutor()
    plan = [
        PlannedAction(action="send_report"),
        PlannedAction(action="delete_records"),
        PlannedAction(action="archive_files"),
    ]
    result = actor.run_plan(plan, decide=lambda p: p.action != "delete_records", executor=executor)
    assert len(result.executed) == 2
    assert len(result.denied) == 1
    assert [call[0] for call in executor.calls] == ["send_report", "archive_files"]
    assert result.receipts_valid is True
