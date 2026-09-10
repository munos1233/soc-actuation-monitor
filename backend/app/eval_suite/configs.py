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

    def loaded(self) -> tuple[str, ...]:
        return tuple(m for m in MEDIATORS if getattr(self, m))

    def substrate_removed(self) -> tuple[str, ...]:
        return tuple(m for m in SUBSTRATE if not getattr(self, m))

    def is_full(self) -> bool:
        """Every switchable gate loaded *and* the substrate intact."""
        return all(getattr(self, m) for m in (*MEDIATORS, *SUBSTRATE))


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


NAIVE = _config("naive")
CLOSE_ONLY = _config("close_only", "close")
BIND_ONLY = _config("bind_only", "bind")
VERIFY_ONLY = _config("verify_only", "verify")
EGRESS_ONLY = _config("egress_only", "egress")
FULL = _config("full", *MEDIATORS)

FULL_MINUS_CLOSE = _config("full_minus_close", "bind", "verify", "egress")
FULL_MINUS_BIND = _config("full_minus_bind", "close", "verify", "egress")
FULL_MINUS_VERIFY = _config("full_minus_verify", "close", "bind", "egress")
FULL_MINUS_EGRESS = _config("full_minus_egress", "close", "bind", "verify")

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
    SINGLE_GATE_CONFIGS + LEAVE_ONE_OUT_CONFIGS + SUBSTRATE_CONFIGS
)
CONFIGS: dict[str, MonitorConfig] = {cfg.name: cfg for cfg in ALL_CONFIGS}

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

    ``MOCK`` is the Mock-XDR contract: receipts are ``simulated=True`` and the
    closure gate accepts them, because the deployment declares a mock
    disposition mode. ``PSEUDO_LIVE`` declares a non-mock disposition mode, so
    the same closure gate demands a non-simulated receipt with strong
    confirmation evidence.

    Neither column is a live vendor: both talk to an in-process stub. Results
    must never be merged into one column.
    """

    MOCK = "mock"
    PSEUDO_LIVE = "pseudo_live"


VENDOR_PRODUCT: dict[VendorColumn, str] = {
    VendorColumn.MOCK: "mock_xdr",
    VendorColumn.PSEUDO_LIVE: "pseudo_live_xdr",
}


class PlannerModel(StrEnum):
    """Who authors the proposal that the mediators police.

    ``UNTRUSTED_PLANNER`` is the paper's adversary: the proposal, the tool echo,
    and the outbound payload may all be attacker-influenced.
    ``DEAD_PLAYBOOK`` is the SOAR-style baseline: a fixed script with no planner
    in the loop, used to separate "harm caused by an untrusted planner" from
    "harm that a static playbook suffers anyway" (weak vendor receipts, tool
    echo, stale heads).
    """

    UNTRUSTED_PLANNER = "untrusted_planner"
    DEAD_PLAYBOOK = "dead_playbook"


@contextmanager
def harness_context(config: MonitorConfig, column: VendorColumn) -> Iterator[None]:
    """Run a case under one mediator configuration and one vendor column."""
    if column is VendorColumn.MOCK:
        vendor_env = {
            "DISPOSITION_MODE": "mock_xdr",
            "DISPOSITION_ADAPTER_KIND": "mock",
            "ALLOW_XDR_WRITEBACK": "false",
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
    "CONFIGS",
    "LEAVE_ONE_OUT_BY_MEDIATOR",
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
