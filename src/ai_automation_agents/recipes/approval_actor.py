"""Recipe 06 — Approval-gated actor.

The safety pattern as a runnable recipe: an agent turns a plan into
proposals, a human decides each one, and only approved actions execute —
through an injected executor, with a tamper-evident receipt for every step.
Use it directly for batch jobs, or copy the pattern into your own recipe
(the gate lives in :mod:`ai_automation_agents.approval`).
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from ai_automation_agents.approval import ApprovalGate
from ai_automation_agents.providers import Executor


class PlannedAction(BaseModel):
    """One step of a plan the agent wants carried out."""

    action: str
    payload: dict[str, Any] = Field(default_factory=dict)
    reason: str = ""


class PlanRunResult(BaseModel):
    """The outcome of a gated plan run."""

    executed: list[str] = Field(default_factory=list)
    denied: list[str] = Field(default_factory=list)
    results: dict[str, Any] = Field(default_factory=dict)
    receipts_valid: bool


class ApprovalGatedActor:
    """Runs plans through an :class:`ApprovalGate`."""

    def __init__(self, gate: ApprovalGate | None = None) -> None:
        self.gate = gate or ApprovalGate()

    def propose_plan(self, plan: list[PlannedAction], proposed_by: str = "approval-actor"):
        """Turn a plan into pending proposals. Nothing executes yet."""
        return [
            self.gate.propose(step.action, step.payload, step.reason, proposed_by=proposed_by)
            for step in plan
        ]

    def run_plan(
        self,
        plan: list[PlannedAction],
        decide: Any,
        executor: Executor,
    ) -> PlanRunResult:
        """Propose, decide, and execute a plan.

        ``decide`` is a callable taking a proposal and returning True
        (approve) or False (deny) — a human in production, a function in
        tests and demos. Denied proposals never reach the executor.
        """
        proposals = self.propose_plan(plan)
        executed: list[str] = []
        denied: list[str] = []
        results: dict[str, Any] = {}
        for proposal in proposals:
            if decide(proposal):
                self.gate.approve(proposal.id)
                results[proposal.id] = self.gate.execute(proposal.id, executor)
                executed.append(proposal.id)
            else:
                self.gate.deny(proposal.id)
                denied.append(proposal.id)
        return PlanRunResult(
            executed=executed,
            denied=denied,
            results=results,
            receipts_valid=self.gate.log.verify(),
        )
