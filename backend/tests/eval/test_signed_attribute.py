"""Signed request attributes still cannot carry a database join."""

from __future__ import annotations

import pytest

from app.eval_suite.configs import (
    ALL_CONFIGS,
    LATTICE_CONFIGS,
    PLAYBOOK_SEMANTIC,
    SIGNED_ATTRIBUTE,
)
from app.eval_suite.policy_engine import (
    FORBIDDEN_JOIN_KEYS,
    PolicyEngineUnavailable,
    SignedAttributeEngine,
    close_document,
)


def test_signed_attribute_not_in_frozen_matrix() -> None:
    assert SIGNED_ATTRIBUTE.name not in {cfg.name for cfg in ALL_CONFIGS}
    assert PLAYBOOK_SEMANTIC.name not in {cfg.name for cfg in ALL_CONFIGS}
    assert SIGNED_ATTRIBUTE.signed_attribute is True
    assert SIGNED_ATTRIBUTE.external_policy is True
    assert PLAYBOOK_SEMANTIC.playbook_semantic is True
    assert len(ALL_CONFIGS) == 17
    assert {cfg.name for cfg in LATTICE_CONFIGS}.isdisjoint({cfg.name for cfg in ALL_CONFIGS})


def test_hmac_roundtrip_and_no_join_keys() -> None:
    engine = SignedAttributeEngine(url="http://127.0.0.1:9/v1/data/actuation")
    doc = close_document(
        pending_approved_actions=0,
        has_report=True,
        terminal_writeback_planned=True,
        disposition_mode="mock_xdr",
        receipt_simulated=False,
    )
    sig = engine.sign(doc)
    assert engine.verify(doc, sig)
    blob = str(doc)
    for key in FORBIDDEN_JOIN_KEYS:
        assert key not in blob


def test_join_key_is_refused() -> None:
    engine = SignedAttributeEngine(url="http://127.0.0.1:9/v1/data/actuation")
    with pytest.raises(PolicyEngineUnavailable, match="approval_row"):
        engine._assert_attribute_only({"approval_row": {"fingerprint": "x"}})
