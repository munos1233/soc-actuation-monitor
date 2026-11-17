"""Activities for the Temporal portability instance.

Unsandboxed worker-side code. The workflow never calls the vendor stub
directly; dispatch and read-back go through activities whose results the
engine records in history — those results are the non-proposer facts the
TEI arm's predicates read.
"""

from __future__ import annotations

from temporalio import activity

from vendor_stub import STUB


@activity.defn
async def dispatch_activity(cmd: dict) -> dict:
    return STUB.submit(cmd)


@activity.defn
async def verify_activity(req: dict) -> dict:
    return STUB.readback(req["disposition_id"])
