"""Actuation-integrity evaluation suite.

The suite drives adversaries at the system boundary — planner proposals, vendor
receipts, and outbound envelopes — through the production service chain
(``ActionExecutionService`` / ``DispositionSyncService`` /
``EventDispositionService`` / ``VerifyAgent`` / ``StateMachineService``) and
scores harm from database and vendor-side facts rather than from a gate's own
return value.

Modules
-------
``configs``
    Mediator configurations (single-gate, full, leave-one-out) and the vendor
    columns / planner baselines each run is reported under.
``vendor``
    In-process vendor stub that records what actually crossed the boundary and
    can return weak or dishonest receipts.
``world``
    Builds a real event world in PostgreSQL and wires the production services.
``attacks``
    Adversary implementations A0–A5.
``gold``
    Suite A: golden-path closure rate and over-block accounting.
``runner``
    Suite orchestration and result aggregation.
``component``
    Appendix-only predicate-level switch checks; never a headline table.
"""

from __future__ import annotations
