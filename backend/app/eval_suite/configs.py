"""Mediator configurations, vendor columns, and planner baselines.

A configuration names which of the four mediators is loaded:

``close``
    Closure gate (``validate_closed_gate``) — the only path into ``CLOSED``.
``bind``
    Content-addressed approval binding rechecked at dispatch
    (``validate_approval_binding``).
``verify``
    Observation/actuation split in ``VerifyAgent`` (tool echo is not evidence,
    deferred terminal actions are not effects).
``egress``
    Outbound disposition guard on every envelope leaving the system.

Single-gate configurations answer "does this gate alone stop the class"; the
leave-one-out configurations answer "is any other mediator silently covering for
it", which single-gate rows cannot show.

Four further mechanisms have no production switch, and pretending otherwise would
be dishonest, so they are ablated differently — by weakening the substrate in the
harness rather than by a setting the code reads (see
:mod:`app.eval_suite.substrate`):

``head_index``
    The partial unique index that admits one active terminal writeback head per
    (event, closure cycle).
``head_supersede``
    The in-transaction supersede in ``enqueue_command`` that retires the prior
    head and takes it out of the delivery queue.
``head_assertion``
    The delivery-time re-read that refuses to send a head that is no longer the
    active one.
``claim_cas``
    The compare-and-set on action status under ``FOR UPDATE`` that makes a
    repeated dispatch of one action a rejected transition.

The first three are layered, so the arms remove them cumulatively: each on its own
is covered by the others, and the arms are built to show that rather than to hide
it. Without these arms the A3 rows are zero in every configuration, which measures
nothing. With them, the report can say which layer is load-bearing.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from enum import StrEnum

from app.eval_monitor import eval_switch_context

MEDIATORS = ("close", "bind", "verify", "egress")
SUBSTRATE = ("head_index", "head_supersede", "head_assertion", "claim_cas")


@dataclass(frozen=True)
class MonitorConfig:
    """One ablation point: which mediators are loaded, and which substrate holds."""

    name: str
    close: bool
    bind: bool
    verify: bool
    egress: bool
    head_index: bool = True
    head_supersede: bool = True
    head_assertion: bool = True
    claim_cas: bool = True
    # Database role split: the planner login cannot write CLOSED or the outbox.
    # Naive unloads it so A0 can show the harm is reachable; every other arm
    # keeps it. Not a production switch — the harness just uses the owner
    # login for the A0 statements when this is false.
    role_separation: bool = True
    # Comparator arm: every internal gate is unloaded and an external policy
    # engine is consulted at the same four points instead
    # (:mod:`app.eval_suite.policy_engine`). Not a mediator configuration —
    # a different mediator, which is why it is not in ``ALL_CONFIGS``.
    external_policy: bool = False
    # HMAC the same request-attribute document before OPA. Still no DB join.
    signed_attribute: bool = False
    # SOAR closer: write CLOSED when a step reports SUCCESS. Not in ALL_CONFIGS.
    playbook_semantic: bool = False

    def loaded(self) -> tuple[str, ...]:
        return tuple(m for m in MEDIATORS if getattr(self, m))

    def substrate_removed(self) -> tuple[str, ...]:
        return tuple(m for m in SUBSTRATE if not getattr(self, m))

    def is_full(self) -> bool:
        """Every switchable gate loaded *and* the substrate intact."""
        return (
            all(getattr(self, m) for m in (*MEDIATORS, *SUBSTRATE)) and self.role_separation
        )


def _config(name: str, *loaded: str) -> MonitorConfig:
    return MonitorConfig(name=name, **{m: m in loaded for m in MEDIATORS})


def _substrate_config(name: str, *without: str) -> MonitorConfig:
    """Every gate loaded, one or more non-switchable mechanisms weakened.

    More than one at a time where the mechanisms are layered: the arm that asks
    what the delivery-time re-read is worth has to get past the two layers above
    it first, or it would be reporting their work as the re-read's.
    """
    removed = set(without)
    return MonitorConfig(
        name=name,
        **{m: True for m in MEDIATORS},
        **{m: m not in removed for m in SUBSTRATE},
    )


NAIVE = MonitorConfig(
    name="naive",
    **{m: False for m in MEDIATORS},
    role_separation=False,
)
CLOSE_ONLY = _config("close_only", "close")
BIND_ONLY = _config("bind_only", "bind")
VERIFY_ONLY = _config("verify_only", "verify")
EGRESS_ONLY = _config("egress_only", "egress")
FULL = _config("full", *MEDIATORS)

FULL_MINUS_CLOSE = _config("full_minus_close", "bind", "verify", "egress")
FULL_MINUS_BIND = _config("full_minus_bind", "close", "verify", "egress")
FULL_MINUS_VERIFY = _config("full_minus_verify", "close", "bind", "egress")
FULL_MINUS_EGRESS = _config("full_minus_egress", "close", "bind", "verify")
CLOSE_AND_VERIFY = _config("close_and_verify", "close", "verify")
BIND_AND_EGRESS = _config("bind_and_egress", "bind", "egress")
CLOSE_AND_BIND = _config("close_and_bind", "close", "bind")
CLOSE_AND_EGRESS = _config("close_and_egress", "close", "egress")
BIND_AND_VERIFY = _config("bind_and_verify", "bind", "verify")
VERIFY_AND_EGRESS = _config("verify_and_egress", "verify", "egress")

SINGLE_GATE_CONFIGS: tuple[MonitorConfig, ...] = (
    NAIVE,
    CLOSE_ONLY,
    BIND_ONLY,
    VERIFY_ONLY,
    EGRESS_ONLY,
    FULL,
)
LEAVE_ONE_OUT_CONFIGS: tuple[MonitorConfig, ...] = (
    FULL_MINUS_CLOSE,
    FULL_MINUS_BIND,
    FULL_MINUS_VERIFY,
    FULL_MINUS_EGRESS,
)
INTERACTION_CONFIGS: tuple[MonitorConfig, ...] = (
    CLOSE_AND_VERIFY,
    BIND_AND_EGRESS,
)
# The four 2-gate cells that the frozen 17-config matrix omitted. Not in
# ALL_CONFIGS — a dedicated lattice run, not a rewrite of the 57-case freeze.
LATTICE_CONFIGS: tuple[MonitorConfig, ...] = (
    CLOSE_AND_BIND,
    CLOSE_AND_EGRESS,
    BIND_AND_VERIFY,
    VERIFY_AND_EGRESS,
)
FULL_MINUS_HEAD_INDEX = _substrate_config("full_minus_head_index", "head_index")
FULL_MINUS_HEAD_SUPERSEDE = _substrate_config("full_minus_head_supersede", "head_supersede")
FULL_MINUS_HEAD_UNIQUENESS = _substrate_config(
    "full_minus_head_uniqueness", "head_index", "head_supersede"
)
FULL_MINUS_HEAD_ASSERTION = _substrate_config(
    "full_minus_head_assertion", "head_index", "head_supersede", "head_assertion"
)
FULL_MINUS_CLAIM_CAS = _substrate_config("full_minus_claim_cas", "claim_cas")

SUBSTRATE_CONFIGS: tuple[MonitorConfig, ...] = (
    FULL_MINUS_HEAD_INDEX,
    FULL_MINUS_HEAD_SUPERSEDE,
    FULL_MINUS_HEAD_UNIQUENESS,
    FULL_MINUS_HEAD_ASSERTION,
    FULL_MINUS_CLAIM_CAS,
)
ALL_CONFIGS: tuple[MonitorConfig, ...] = (
    SINGLE_GATE_CONFIGS + LEAVE_ONE_OUT_CONFIGS + INTERACTION_CONFIGS + SUBSTRATE_CONFIGS
)

# The comparator arm. Excluded from ALL_CONFIGS because it needs an OPA server
# running, and because it belongs in a different table: it does not answer "is
# this mediator load-bearing" but "would an external policy engine have done this
# mediator's work".
EXTERNAL_OPA = MonitorConfig(
    name="external_opa",
    **{m: False for m in MEDIATORS},
    external_policy=True,
)
SIGNED_ATTRIBUTE = MonitorConfig(
    name="signed_attribute",
    **{m: False for m in MEDIATORS},
    external_policy=True,
    signed_attribute=True,
)
PLAYBOOK_SEMANTIC = MonitorConfig(
    name="playbook_semantic",
    **{m: False for m in MEDIATORS},
    role_separation=False,
    playbook_semantic=True,
)
COMPARATOR_CONFIGS: tuple[MonitorConfig, ...] = (EXTERNAL_OPA, SIGNED_ATTRIBUTE)
PLAYBOOK_CONFIGS: tuple[MonitorConfig, ...] = (PLAYBOOK_SEMANTIC,)

CONFIGS: dict[str, MonitorConfig] = {
    cfg.name: cfg
    for cfg in (*ALL_CONFIGS, *COMPARATOR_CONFIGS, *LATTICE_CONFIGS, *PLAYBOOK_CONFIGS)
}

# full_minus_X pairs with the mediator it removes, so the runner can assert that
# removing X reopens exactly the classes X is claimed to mediate.
LEAVE_ONE_OUT_BY_MEDIATOR: dict[str, MonitorConfig] = {
    "close": FULL_MINUS_CLOSE,
    "bind": FULL_MINUS_BIND,
    "verify": FULL_MINUS_VERIFY,
    "egress": FULL_MINUS_EGRESS,
}

SUBSTRATE_BY_MECHANISM: dict[str, MonitorConfig] = {
    "head_index": FULL_MINUS_HEAD_INDEX,
    "head_supersede": FULL_MINUS_HEAD_SUPERSEDE,
    "head_assertion": FULL_MINUS_HEAD_ASSERTION,
    "claim_cas": FULL_MINUS_CLAIM_CAS,
}


class VendorColumn(StrEnum):
    """Which vendor contract the run is reported under.

    ``MOCK`` is the Mock-XDR contract: receipts are ``simulated=True``.
    ``PSEUDO_LIVE`` declares a non-mock disposition mode, so the same
    closure gate also demands a non-simulated receipt.
    ``SANGFOR_STUB`` is a second vendor envelope (dealStatus / ticket
    fields) against an in-process stub, not a live tenant.

    Columns must never be merged into one headline number.
    """

    MOCK = "mock"
    PSEUDO_LIVE = "pseudo_live"
    SANGFOR_STUB = "sangfor_stub"


VENDOR_PRODUCT: dict[VendorColumn, str] = {
    VendorColumn.MOCK: "mock_xdr",
    VendorColumn.PSEUDO_LIVE: "pseudo_live_xdr",
    VendorColumn.SANGFOR_STUB: "sangfor_xdr_stub",
}


class PlannerModel(StrEnum):
    """Who authors the proposal that the mediators police.

    ``UNTRUSTED_PLANNER`` is the paper's adversary: the proposal, the tool echo,
    and the outbound payload may all be attacker-influenced.
    ``DEAD_PLAYBOOK`` is the SOAR-style baseline: a fixed script with no planner
    in the loop, used to separate "harm caused by an untrusted planner" from
    "harm that a static playbook suffers anyway" (weak vendor receipts, tool
    echo, stale heads).
    ``LLM_PLANNER`` puts a real language model in the seat
    (:mod:`app.eval_suite.planner`). It answers the one question the scripted arm
    cannot: does a model actually author the row the scripted adversary writes by
    hand. It is not the default, because a provider with no seed cannot produce a
    matrix that reproduces to the row.
    """

    UNTRUSTED_PLANNER = "untrusted_planner"
    DEAD_PLAYBOOK = "dead_playbook"
    LLM_PLANNER = "llm_planner"


@contextmanager
def harness_context(config: MonitorConfig, column: VendorColumn) -> Iterator[None]:
    """Run a case under one mediator configuration and one vendor column."""
    if column is VendorColumn.MOCK:
        vendor_env = {
            "DISPOSITION_MODE": "mock_xdr",
            "DISPOSITION_ADAPTER_KIND": "mock",
            "ALLOW_XDR_WRITEBACK": "false",
        }
    elif column is VendorColumn.SANGFOR_STUB:
        vendor_env = {
            "DISPOSITION_MODE": "pseudo_live_xdr",
            "DISPOSITION_ADAPTER_KIND": "http",
            "ALLOW_XDR_WRITEBACK": "true",
        }
    else:
        # A non-mock disposition mode is fenced unless the deployment has
        # explicitly enabled vendor writeback, which is what a staging
        # deployment pointed at a real tenant would do.
        vendor_env = {
            "DISPOSITION_MODE": "pseudo_live_xdr",
            # KIND=http is the registered non-mock generic transport; the eval
            # vendor stands in for the HTTP endpoint, so the chain takes the
            # same non-mock provider/job path a real tenant would take.
            "DISPOSITION_ADAPTER_KIND": "http",
            "ALLOW_XDR_WRITEBACK": "true",
        }
    with eval_switch_context(
        disable_closed=not config.close,
        disable_bind=not config.bind,
        disable_verify=not config.verify,
        disable_egress=not config.egress,
        extra_env=vendor_env,
    ):
        yield


__all__ = [
    "ALL_CONFIGS",
    "COMPARATOR_CONFIGS",
    "CONFIGS",
    "EXTERNAL_OPA",
    "PLAYBOOK_CONFIGS",
    "PLAYBOOK_SEMANTIC",
    "SIGNED_ATTRIBUTE",
    "LEAVE_ONE_OUT_BY_MEDIATOR",
    "BIND_AND_EGRESS",
    "BIND_AND_VERIFY",
    "CLOSE_AND_BIND",
    "CLOSE_AND_EGRESS",
    "CLOSE_AND_VERIFY",
    "INTERACTION_CONFIGS",
    "LATTICE_CONFIGS",
    "VERIFY_AND_EGRESS",
    "LEAVE_ONE_OUT_CONFIGS",
    "MEDIATORS",
    "SINGLE_GATE_CONFIGS",
    "SUBSTRATE",
    "SUBSTRATE_BY_MECHANISM",
    "SUBSTRATE_CONFIGS",
    "VENDOR_PRODUCT",
    "MonitorConfig",
    "PlannerModel",
    "VendorColumn",
    "harness_context",
]
