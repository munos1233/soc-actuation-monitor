"""Executable semantics of eval/model/TEI.tla.

Action names, variables, and invariants are the TLA+ names. TLC (Java) is
the required checker for `make paper-eval-tla`; this module is the same
transition relation so traces can be emitted without a third semantics.
write_path_invariants.check remains a regression slice of the SOC four.

AttrView / CloseOK / BindOK match TEI.tla. HonestAdvance is an environment
action, not a mediation knob. See eval/model/view_lemma.md.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, replace
from typing import Any, Callable, Iterator


@dataclass(frozen=True)
class Mechanisms:
    """TLA+ CONSTANTS. True means the TEI construction is loaded."""

    CloseRebuild: bool = True
    BindRecompute: bool = True
    VerifySplit: bool = True
    EgressWitness: bool = True
    RoleRevoke: bool = True
    HeadUnique: bool = True
    ClaimCAS: bool = True
    AttributeOnly: bool = False

    @property
    def name(self) -> str:
        if self.AttributeOnly:
            return "attribute_only"
        missing = [
            label
            for flag, label in (
                (self.CloseRebuild, "close"),
                (self.BindRecompute, "bind"),
                (self.VerifySplit, "verify"),
                (self.EgressWitness, "egress"),
                (self.RoleRevoke, "role"),
                (self.HeadUnique, "head"),
                (self.ClaimCAS, "cas"),
            )
            if not flag
        ]
        return "full" if not missing else "minus_" + "+".join(missing)

    def as_json(self) -> dict[str, bool]:
        return {
            "CloseRebuild": self.CloseRebuild,
            "BindRecompute": self.BindRecompute,
            "VerifySplit": self.VerifySplit,
            "EgressWitness": self.EgressWitness,
            "RoleRevoke": self.RoleRevoke,
            "HeadUnique": self.HeadUnique,
            "ClaimCAS": self.ClaimCAS,
            "AttributeOnly": self.AttributeOnly,
        }


@dataclass(frozen=True)
class State:
    callerCycle: int
    rebuiltCycle: int
    plannerFp: str
    recomputedFp: str
    cmdLocator: str
    eventSource: str
    plannerWrotePriv: bool
    closed: bool
    dispatched: bool
    submitted: bool
    isolateApplied: bool
    observedIsolate: bool
    observeMutated: bool
    dualHeads: bool
    claimCount: int
    lostEffect: bool
    closedOnStale: bool
    dispatchedOnForged: bool
    submittedOnSelfLocator: bool
    isolatedWithoutObserve: bool
    ackWithoutObject: bool
    signedOk: bool
    attachedApprovalCopy: str
    reportedReceipt: str

    def key(self) -> tuple[object, ...]:
        return (
            self.callerCycle,
            self.rebuiltCycle,
            self.plannerFp,
            self.recomputedFp,
            self.cmdLocator,
            self.eventSource,
            self.plannerWrotePriv,
            self.closed,
            self.dispatched,
            self.submitted,
            self.isolateApplied,
            self.observedIsolate,
            self.observeMutated,
            self.dualHeads,
            self.claimCount,
            self.lostEffect,
            self.closedOnStale,
            self.dispatchedOnForged,
            self.submittedOnSelfLocator,
            self.isolatedWithoutObserve,
            self.ackWithoutObject,
            self.signedOk,
            self.attachedApprovalCopy,
            self.reportedReceipt,
        )


START = State(
    callerCycle=1,
    rebuiltCycle=1,
    plannerFp="true",
    recomputedFp="true",
    cmdLocator="ingest",
    eventSource="ingest",
    plannerWrotePriv=False,
    closed=False,
    dispatched=False,
    submitted=False,
    isolateApplied=False,
    observedIsolate=False,
    observeMutated=False,
    dualHeads=False,
    claimCount=0,
    lostEffect=False,
    closedOnStale=False,
    dispatchedOnForged=False,
    submittedOnSelfLocator=False,
    isolatedWithoutObserve=False,
    ackWithoutObject=False,
    signedOk=True,
    attachedApprovalCopy="copy-true",
    reportedReceipt="strong",
)


# TLA+ action names. Keep these identical to TEI.tla.
ACTION_PLANNER_FORGE = "PlannerForgeFingerprint"
ACTION_PLANNER_REPOINT = "PlannerRepointLocator"
ACTION_PLANNER_SELF_NAME = "PlannerSelfName"
ACTION_PLANNER_STALE = "PlannerStaleCycle"
ACTION_HONEST_ADVANCE = "HonestAdvance"
ACTION_PLANNER_WRITE_CLOSED = "PlannerWriteClosed"
ACTION_PLANNER_WRITE_REFUSED = "PlannerWriteClosedRefused"
ACTION_PLANNER_PRIVILEGE = "PlannerCreatePrivilege"
ACTION_PLANNER_PRIVILEGE_REFUSED = "PlannerCreatePrivilegeRefused"
ACTION_CLOSE_OK = "CloseAccepted"
ACTION_CLOSE_REFUSED = "CloseRefused"
ACTION_DISPATCH_OK = "DispatchAccepted"
ACTION_DISPATCH_REFUSED = "DispatchRefused"
ACTION_SUBMIT = "VendorSubmit"
ACTION_BLOCKED = "VendorBlocked"
ACTION_WEAK_ACK = "WeakReceiptAck"
ACTION_OBSERVE = "ObserveIsolate"
ACTION_ECHO = "EchoObserve"
ACTION_OBSERVER_MUTATE = "ObserverMutate"
ACTION_ISOLATE = "IsolateApplied"
ACTION_ISOLATE_WITHOUT = "IsolateWithoutObserve"
ACTION_SECOND_CLAIM = "SecondClaim"
ACTION_SECOND_HEAD = "SecondHead"

# AttrView members. rebuiltCycle / recomputedFp / observe / locator are not.
ATTR_VIEW_FIELDS: tuple[str, ...] = (
    "callerCycle",
    "plannerFp",
    "signedOk",
    "attachedApprovalCopy",
    "reportedReceipt",
)


def attr_view(state: State) -> tuple[object, ...]:
    """Request-visible projection. Same tuple as TEI!AttrView."""
    return (
        state.callerCycle,
        state.plannerFp,
        state.signedOk,
        state.attachedApprovalCopy,
        state.reportedReceipt,
    )


def close_ok(state: State) -> bool:
    """Store cycle alignment. Not a function of AttrView."""
    return state.rebuiltCycle == state.callerCycle


def bind_ok(state: State) -> bool:
    """Store fingerprint alignment. recomputedFp is not in AttrView."""
    return state.plannerFp == state.recomputedFp


def view_consistent(state: State) -> bool:
    """AttributeOnly close/bind gate: AttrView self-consistency only."""
    expected_copy = {
        "true": "copy-true",
        "forged": "copy-forged",
        "forged-b": "copy-forged-b",
        "forged-c": "copy-forged-c",
    }.get(state.plannerFp, "copy-forged")
    return (
        state.signedOk
        and state.attachedApprovalCopy == expected_copy
        and state.reportedReceipt in {"strong", "weak"}
    )


def reads_s_close(mech: Mechanisms) -> bool:
    return mech.CloseRebuild and not mech.AttributeOnly


def reads_s_bind(mech: Mechanisms) -> bool:
    return mech.BindRecompute and not mech.AttributeOnly


def successors(state: State, mech: Mechanisms) -> list[tuple[str, State]]:
    """Next relation. Each pair is a TLA+ action name and the successor."""
    out: list[tuple[str, State]] = []

    out.append(
        (
            ACTION_PLANNER_FORGE,
            replace(state, plannerFp="forged", attachedApprovalCopy="copy-forged"),
        )
    )
    out.append(
        (
            ACTION_PLANNER_FORGE,
            replace(state, plannerFp="forged-b", attachedApprovalCopy="copy-forged-b"),
        )
    )
    out.append(
        (
            ACTION_PLANNER_FORGE,
            replace(state, plannerFp="forged-c", attachedApprovalCopy="copy-forged-c"),
        )
    )
    out.append((ACTION_PLANNER_REPOINT, replace(state, cmdLocator="foreign")))
    out.append((ACTION_PLANNER_REPOINT, replace(state, cmdLocator="foreign-b")))
    out.append((ACTION_PLANNER_REPOINT, replace(state, cmdLocator="foreign-c")))
    out.append((ACTION_PLANNER_SELF_NAME, replace(state, cmdLocator="self-name")))
    for cycle in (2, 3, 4, 5):
        out.append((ACTION_PLANNER_STALE, replace(state, callerCycle=cycle, rebuiltCycle=1)))
        out.append((ACTION_HONEST_ADVANCE, replace(state, callerCycle=cycle, rebuiltCycle=cycle)))

    if mech.RoleRevoke:
        out.append((ACTION_PLANNER_WRITE_REFUSED, state))
        out.append((ACTION_PLANNER_PRIVILEGE_REFUSED, state))
    else:
        out.append(
            (
                ACTION_PLANNER_WRITE_CLOSED,
                replace(state, plannerWrotePriv=True, closed=True),
            )
        )
        out.append(
            (
                ACTION_PLANNER_PRIVILEGE,
                replace(state, plannerWrotePriv=True, isolateApplied=True),
            )
        )

    cycles_match = close_ok(state)
    close_gate = view_consistent(state) if mech.AttributeOnly else (
        cycles_match if mech.CloseRebuild else True
    )
    if close_gate and not state.closed:
        out.append(
            (
                ACTION_CLOSE_OK,
                replace(state, closed=True, closedOnStale=not cycles_match),
            )
        )
    else:
        out.append((ACTION_CLOSE_REFUSED, state))

    fingerprints_match = bind_ok(state)
    bind_gate = view_consistent(state) if mech.AttributeOnly else (
        fingerprints_match if mech.BindRecompute else True
    )
    if bind_gate and not state.dispatched:
        out.append(
            (
                ACTION_DISPATCH_OK,
                replace(
                    state,
                    dispatched=True,
                    claimCount=max(state.claimCount, 1),
                    dispatchedOnForged=not fingerprints_match,
                ),
            )
        )
    else:
        out.append((ACTION_DISPATCH_REFUSED, state))

    locators_match = state.cmdLocator == state.eventSource
    egress_ok = locators_match if mech.EgressWitness else True
    if state.dispatched and egress_ok and not state.submitted:
        out.append(
            (
                ACTION_SUBMIT,
                replace(
                    state,
                    submitted=True,
                    submittedOnSelfLocator=not locators_match,
                ),
            )
        )
    elif state.dispatched:
        out.append((ACTION_BLOCKED, state))

    if not state.ackWithoutObject:
        persisted = not mech.CloseRebuild
        out.append(
            (
                ACTION_WEAK_ACK,
                replace(
                    state,
                    ackWithoutObject=True,
                    reportedReceipt="weak",
                    isolateApplied=persisted or state.isolateApplied,
                    isolatedWithoutObserve=persisted,
                ),
            )
        )

    if not state.observedIsolate:
        out.append((ACTION_OBSERVE, replace(state, observedIsolate=True)))
    out.append((ACTION_ECHO, state))

    if mech.VerifySplit:
        out.append((ACTION_OBSERVER_MUTATE, state))
    elif not state.observeMutated:
        out.append(
            (
                ACTION_OBSERVER_MUTATE,
                replace(
                    state,
                    observeMutated=True,
                    isolateApplied=True,
                    isolatedWithoutObserve=not state.observedIsolate,
                ),
            )
        )

    if state.observedIsolate and not state.isolateApplied:
        out.append((ACTION_ISOLATE, replace(state, isolateApplied=True)))
    if not mech.CloseRebuild and not state.isolateApplied:
        out.append(
            (
                ACTION_ISOLATE_WITHOUT,
                replace(
                    state,
                    isolateApplied=True,
                    isolatedWithoutObserve=True,
                ),
            )
        )

    if state.dispatched:
        if mech.ClaimCAS:
            out.append(
                (
                    ACTION_SECOND_CLAIM,
                    replace(state, lostEffect=True),
                )
            )
        else:
            out.append(
                (
                    ACTION_SECOND_CLAIM,
                    replace(state, claimCount=min(state.claimCount + 1, 3)),
                )
            )
        if mech.HeadUnique:
            out.append((ACTION_SECOND_HEAD, state))
        else:
            out.append((ACTION_SECOND_HEAD, replace(state, dualHeads=True)))

    return out


def InvClose(state: State) -> bool:
    return not state.closedOnStale


def InvBind(state: State) -> bool:
    return not state.dispatchedOnForged


def InvEgress(state: State) -> bool:
    return not state.submittedOnSelfLocator


def InvRole(state: State) -> bool:
    return not state.plannerWrotePriv


def InvVerify(state: State) -> bool:
    return not state.observeMutated


def InvHead(state: State) -> bool:
    return not state.dualHeads


def InvK8sClose(state: State) -> bool:
    # A weak ACK is not itself a close. CloseRebuild keeps it from becoming
    # isolateApplied / isolatedWithoutObserve.
    return not state.isolatedWithoutObserve


def InvCAS(state: State) -> bool:
    """Unconditional status-layer bound. minus_cas must violate this."""
    return state.claimCount <= 1


def InvCASStatusLayer(state: State, mech: Mechanisms) -> bool:
    """Head-layer uniqueness is not this invariant.

    Claim-CAS is the status layer: at most one successful claim of the
    action row. When CAS is on, a second claim is a lost effect
    (claimCount stays 1). Dual active heads are InvHead / HeadUnique.
    """
    if mech.ClaimCAS:
        return state.claimCount <= 1
    return True


INVARIANTS: tuple[tuple[str, str, Callable[[State], bool]], ...] = (
    ("close", "closure uses rebuilt cycle", InvClose),
    ("bind", "dispatch recomputes fingerprint", InvBind),
    ("egress", "egress witnesses ingest identity", InvEgress),
    ("role", "planner cannot write privilege", InvRole),
    ("verify", "observe cannot mutate", InvVerify),
    ("head", "at most one active head", InvHead),
    ("k8s_close", "isolate requires observe re-read", InvK8sClose),
    ("cas", "at most one successful claim", InvCAS),
)


# Ablations the paper reports. Each must have a shortest CE except full.
LADDER: tuple[Mechanisms, ...] = (
    Mechanisms(),
    Mechanisms(CloseRebuild=False),
    Mechanisms(BindRecompute=False),
    Mechanisms(EgressWitness=False),
    Mechanisms(RoleRevoke=False),
    Mechanisms(VerifySplit=False),
    Mechanisms(HeadUnique=False),
    Mechanisms(ClaimCAS=False),
    Mechanisms(AttributeOnly=True),
)


# Abstract TLA+ steps → Injection knobs already implemented on a chain.
STEP_INJECTION: dict[str, dict[str, Any]] = {
    ACTION_PLANNER_FORGE: {"mutate_after_approval": "target_forged_fingerprint"},
    ACTION_PLANNER_REPOINT: {"locator_swap": True},
    ACTION_PLANNER_SELF_NAME: {"self_witness_name": True},
    ACTION_PLANNER_STALE: {"bump_revision_after_activation": True},
    ACTION_PLANNER_WRITE_CLOSED: {"sql_bypass": "close"},
    ACTION_PLANNER_PRIVILEGE: {"planner_privilege": "create_networkpolicy"},
    ACTION_WEAK_ACK: {"weak_ack": True},
    ACTION_ISOLATE_WITHOUT: {"isolate_without_observe": True},
    ACTION_OBSERVER_MUTATE: {"observer_mutate": True},
    ACTION_ECHO: {"echo_observe": True},
    ACTION_SECOND_CLAIM: {"duplicate_entity_dispatch": True},
    ACTION_SECOND_HEAD: {"race_terminal_heads": True},
}


def explore(mech: Mechanisms) -> dict[str, Any]:
    seen: dict[tuple[object, ...], tuple[tuple[object, ...] | None, str]] = {
        START.key(): (None, "Init")
    }
    queue: deque[State] = deque([START])
    violations: dict[str, list[str]] = {}
    cas_status_ok = True
    states = 0
    transitions = 0
    while queue:
        state = queue.popleft()
        states += 1
        for inv_key, _label, holds in INVARIANTS:
            if inv_key not in violations and not holds(state):
                violations[inv_key] = _trace(seen, state.key())
        if cas_status_ok and not InvCASStatusLayer(state, mech):
            cas_status_ok = False
        for label, nxt in successors(state, mech):
            transitions += 1
            key = nxt.key()
            if key in seen:
                continue
            seen[key] = (state.key(), label)
            queue.append(nxt)
    return {
        "mechanisms": mech.name,
        "constants": mech.as_json(),
        "states": states,
        "transitions": transitions,
        "violations": {key: trace for key, trace in violations.items()},
        "cas_status_layer_holds": cas_status_ok,
        "cas_lemma": _cas_lemma(mech, cas_status_ok, violations),
    }


def _cas_lemma(
    mech: Mechanisms, cas_status_ok: bool, violations: dict[str, list[str]]
) -> dict[str, Any]:
    """Layered claim, not a model/implementation disagreement.

    Spec: HeadUnique is the head layer (dual active heads). ClaimCAS is the
    status layer (a second claim is a lost effect). The multi-process probe
    observing a lost effect under CAS is the status layer; it is not a
    dual-write at the head layer.
    """
    return {
        "head_layer": "HeadUnique prevents dualHeads (InvHead)",
        "status_layer": "ClaimCAS keeps claimCount<=1; second claim is lostEffect",
        "head_holds": "head" not in violations,
        "status_holds": cas_status_ok,
        "claim_cas_loaded": mech.ClaimCAS,
        "head_unique_loaded": mech.HeadUnique,
    }


def _trace(
    seen: dict[tuple[object, ...], tuple[tuple[object, ...] | None, str]],
    key: tuple[object, ...],
) -> list[str]:
    steps: list[str] = []
    cursor: tuple[object, ...] | None = key
    while cursor is not None:
        parent, label = seen[cursor]
        if parent is None:
            break
        steps.append(label)
        cursor = parent
    return list(reversed(steps))


def emit_tlc_seeds() -> list[dict[str, Any]]:
    """Shortest TLC (engine) counterexamples as chain-instantiable knobs."""
    seeds: list[dict[str, Any]] = []
    for mech in LADDER:
        result = explore(mech)
        for inv_key, _label, _holds in INVARIANTS:
            trace = result["violations"].get(inv_key)
            if not trace:
                continue
            knobs: dict[str, Any] = {}
            for step in trace:
                knobs.update(STEP_INJECTION.get(step, {}))
            seeds.append(
                {
                    "source": "TEI.tla/TLC",
                    "invariant": inv_key,
                    "mechanisms": result["mechanisms"],
                    "constants": result["constants"],
                    "trace": list(trace),
                    "injection": knobs,
                }
            )
    return seeds


def iter_action_alphabet() -> Iterator[str]:
    yield from (
        ACTION_PLANNER_FORGE,
        ACTION_PLANNER_REPOINT,
        ACTION_PLANNER_SELF_NAME,
        ACTION_PLANNER_STALE,
        ACTION_HONEST_ADVANCE,
        ACTION_PLANNER_WRITE_CLOSED,
        ACTION_PLANNER_PRIVILEGE,
        ACTION_CLOSE_OK,
        ACTION_DISPATCH_OK,
        ACTION_SUBMIT,
        ACTION_WEAK_ACK,
        ACTION_OBSERVE,
        ACTION_ECHO,
        ACTION_OBSERVER_MUTATE,
        ACTION_ISOLATE_WITHOUT,
        ACTION_SECOND_CLAIM,
        ACTION_SECOND_HEAD,
    )


def masking_pairs() -> tuple[tuple[str, str], ...]:
    """2-gate pairs the spec says can hide a class the other two leave open.

    close+verify hides A5-echo while leaving A2/A4; bind+egress hides A2/A4
    while leaving A1. The four missing pairs are the rest of C(4,2).
    """
    return (
        ("close", "verify"),
        ("bind", "egress"),
        ("close", "bind"),
        ("close", "egress"),
        ("bind", "verify"),
        ("verify", "egress"),
    )


def step(state: State, mech: Mechanisms, action: str) -> State | None:
    for label, nxt in successors(state, mech):
        if label == action:
            return nxt
    return None


def close_witness_pair(mech: Mechanisms | None = None) -> dict[str, Any]:
    """HonestAdvance vs PlannerStaleCycle: same AttrView, different CloseOK."""
    mech = mech or Mechanisms()
    honest = step(START, mech, ACTION_HONEST_ADVANCE)
    stale = step(START, mech, ACTION_PLANNER_STALE)
    if honest is None or stale is None:
        raise RuntimeError("HonestAdvance / PlannerStaleCycle must be enabled")
    return {
        "honest_action": ACTION_HONEST_ADVANCE,
        "stale_action": ACTION_PLANNER_STALE,
        "honest": honest,
        "stale": stale,
        "attr_view": list(attr_view(honest)),
        "same_view": attr_view(honest) == attr_view(stale),
        "close_ok_honest": close_ok(honest),
        "close_ok_stale": close_ok(stale),
    }


def explore_view_pair(mech: Mechanisms | None = None) -> dict[str, Any]:
    """Product BFS of TEIPair Next: one side steps, the other is unchanged.

    InvViewClose is (AttrView(A)=AttrView(B)) => (CloseOK(A)=CloseOK(B)).
    The shortest violation is HonestAdvance on one side and PlannerStaleCycle
    on the other. InvClose scoring is not used here.
    """
    mech = mech or Mechanisms()
    start = (START, START)
    seen: dict[tuple[tuple[object, ...], tuple[object, ...]], tuple[object, str]] = {
        (START.key(), START.key()): (None, "Init")
    }
    queue: deque[tuple[State, State]] = deque([start])
    violation: list[str] | None = None
    states = 0
    transitions = 0
    while queue:
        left, right = queue.popleft()
        states += 1
        same_view = attr_view(left) == attr_view(right)
        if same_view and close_ok(left) != close_ok(right) and violation is None:
            violation = _pair_trace(seen, (left.key(), right.key()))
            break
        for side, state, other in (("A", left, right), ("B", right, left)):
            for label, nxt in successors(state, mech):
                transitions += 1
                successor = (nxt, other) if side == "A" else (other, nxt)
                key = (successor[0].key(), successor[1].key())
                if key in seen:
                    continue
                seen[key] = ((left.key(), right.key()), f"{side}_{label}")
                queue.append(successor)
    return {
        "states": states,
        "transitions": transitions,
        "inv_view_close_ce": violation,
        "inv_view_close_holds": violation is None,
    }


def _pair_trace(
    seen: dict[tuple[tuple[object, ...], tuple[object, ...]], tuple[object, str]],
    key: tuple[tuple[object, ...], tuple[object, ...]],
) -> list[str]:
    steps: list[str] = []
    cursor: object = key
    while cursor is not None:
        parent, label = seen[cursor]  # type: ignore[index]
        if parent is None:
            break
        steps.append(label)
        cursor = parent
    return list(reversed(steps))


__all__ = [
    "ATTR_VIEW_FIELDS",
    "INVARIANTS",
    "LADDER",
    "Mechanisms",
    "START",
    "STEP_INJECTION",
    "State",
    "attr_view",
    "bind_ok",
    "close_ok",
    "close_witness_pair",
    "emit_tlc_seeds",
    "explore",
    "explore_view_pair",
    "iter_action_alphabet",
    "masking_pairs",
    "reads_s_bind",
    "reads_s_close",
    "step",
    "successors",
    "view_consistent",
]
