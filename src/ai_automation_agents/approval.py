"""The approval-gate pattern, as a reusable component (Recipe 06).

An agent *proposes* an action. A human approves or denies it. Only an
approved action may execute, and execution happens through an injected
executor — the gate itself causes no side effects. Every step is written to
a hash-chained receipt log (stdlib ``hashlib``): each entry commits to the
previous entry's hash, so editing or deleting history breaks verification.

This module is deliberately dependency-light so any recipe — or your own
Recipe 13 — can gate its side effects with it.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from ai_automation_agents.providers import Executor

ProposalStatus = Literal["pending", "approved", "denied", "executed"]


def _utc_now() -> datetime:
    return datetime.now(UTC)


class ActionProposal(BaseModel):
    """An action an agent wants to perform, awaiting a human decision."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    action: str
    payload: dict[str, Any] = Field(default_factory=dict)
    reason: str = ""
    proposed_by: str = "agent"
    status: ProposalStatus = "pending"
    created_at: datetime = Field(default_factory=_utc_now)
    decided_by: str | None = None
    decided_at: datetime | None = None


class ReceiptEntry(BaseModel):
    """One entry in the hash-chained receipt log."""

    index: int
    timestamp: datetime
    event: str
    data: dict[str, Any] = Field(default_factory=dict)
    prev_hash: str
    hash: str


class ReceiptLog:
    """An append-only, hash-chained log of gate events.

    ``verify()`` recomputes every hash and the chain links; it returns
    ``False`` if any entry was edited, reordered, or removed.
    """

    GENESIS = "GENESIS"

    def __init__(self, clock: Callable[[], datetime] = _utc_now) -> None:
        self._clock = clock
        self.entries: list[ReceiptEntry] = []

    @staticmethod
    def _digest(index: int, timestamp: datetime, event: str, data: dict, prev_hash: str) -> str:
        payload = {
            "index": index,
            "timestamp": timestamp.isoformat(),
            "event": event,
            "data": data,
            "prev_hash": prev_hash,
        }
        canonical = json.dumps(payload, sort_keys=True, default=str)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def append(self, event: str, data: dict[str, Any] | None = None) -> ReceiptEntry:
        """Append ``event`` to the chain and return the new entry."""
        entry_data = data or {}
        index = len(self.entries)
        prev_hash = self.entries[-1].hash if self.entries else self.GENESIS
        timestamp = self._clock()
        digest = self._digest(index, timestamp, event, entry_data, prev_hash)
        entry = ReceiptEntry(
            index=index,
            timestamp=timestamp,
            event=event,
            data=entry_data,
            prev_hash=prev_hash,
            hash=digest,
        )
        self.entries.append(entry)
        return entry

    def verify(self) -> bool:
        """Return True when the chain is intact and untampered."""
        prev_hash = self.GENESIS
        for expected_index, entry in enumerate(self.entries):
            if entry.index != expected_index or entry.prev_hash != prev_hash:
                return False
            digest = self._digest(
                entry.index, entry.timestamp, entry.event, entry.data, entry.prev_hash
            )
            if digest != entry.hash:
                return False
            prev_hash = entry.hash
        return True


class ApprovalGate:
    """Propose → approve/deny → execute, with a receipt for every step."""

    def __init__(
        self,
        log: ReceiptLog | None = None,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self.log = log or ReceiptLog(clock=clock)
        self._clock = clock
        self._proposals: dict[str, ActionProposal] = {}

    def propose(
        self,
        action: str,
        payload: dict[str, Any] | None = None,
        reason: str = "",
        proposed_by: str = "agent",
    ) -> ActionProposal:
        """Register a new pending proposal and log it. Nothing executes."""
        proposal = ActionProposal(
            action=action,
            payload=payload or {},
            reason=reason,
            proposed_by=proposed_by,
        )
        self._proposals[proposal.id] = proposal
        self.log.append(
            "proposed",
            {"proposal_id": proposal.id, "action": action, "proposed_by": proposed_by},
        )
        return proposal

    def get(self, proposal_id: str) -> ActionProposal:
        """Return a proposal by id, raising ``KeyError`` when unknown."""
        if proposal_id not in self._proposals:
            raise KeyError(f"Unknown proposal id: {proposal_id}")
        return self._proposals[proposal_id]

    def pending(self) -> list[ActionProposal]:
        """Return all proposals still awaiting a human decision."""
        return [p for p in self._proposals.values() if p.status == "pending"]

    def _decide(self, proposal_id: str, approved: bool, decided_by: str) -> ActionProposal:
        proposal = self.get(proposal_id)
        if proposal.status != "pending":
            raise ValueError(
                f"Proposal {proposal_id} is {proposal.status}; only pending proposals "
                "can be decided."
            )
        proposal.status = "approved" if approved else "denied"
        proposal.decided_by = decided_by
        proposal.decided_at = self._clock()
        self.log.append(
            "approved" if approved else "denied",
            {"proposal_id": proposal.id, "action": proposal.action, "decided_by": decided_by},
        )
        return proposal

    def approve(self, proposal_id: str, decided_by: str = "human") -> ActionProposal:
        """Approve a pending proposal. Approval alone executes nothing."""
        return self._decide(proposal_id, True, decided_by)

    def deny(self, proposal_id: str, decided_by: str = "human") -> ActionProposal:
        """Deny a pending proposal. A denied proposal can never execute."""
        return self._decide(proposal_id, False, decided_by)

    def execute(self, proposal_id: str, executor: Executor) -> dict[str, Any]:
        """Execute an approved proposal through ``executor`` and log a receipt.

        Raises ``ValueError`` for pending or denied proposals — the gate
        fails closed, like the starter kit's authenticated API.
        """
        proposal = self.get(proposal_id)
        if proposal.status != "approved":
            raise ValueError(
                f"Proposal {proposal_id} is {proposal.status}; only approved proposals can execute."
            )
        result = executor.execute(proposal.action, proposal.payload)
        proposal.status = "executed"
        self.log.append(
            "executed",
            {"proposal_id": proposal.id, "action": proposal.action, "result": result},
        )
        return result
