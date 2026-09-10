"""The model check is a claim in the paper, so CI has to be able to fail on it.

Two directions matter equally. The full configuration must hold every invariant
over every interleaving, which is the claim. And at least one ablation must still
produce a counterexample, which is the guard against the model quietly becoming
vacuous — a model that proves everything safe because it no longer models the
race would pass the first assertion forever.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

MODEL_PATH = Path(__file__).resolve().parents[3] / "eval" / "model" / "head_invariants.py"


def _load() -> ModuleType:
    spec = importlib.util.spec_from_file_location("head_invariants", MODEL_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


model = _load()


def _by_name(name: str) -> object:
    for mech in model.LADDER:
        if mech.name == name:
            return mech
    raise AssertionError(f"no such configuration in the ladder: {name}")


@pytest.mark.parametrize("scenario_name", [model.SHARED_ACTION, model.DISTINCT_ACTIONS])
@pytest.mark.parametrize("workers", [2, 3])
def test_full_configuration_holds_every_invariant(scenario_name: str, workers: int) -> None:
    result = model.check(_by_name("full"), model.scenario(scenario_name, workers))
    assert result.violations == {}, (
        f"the full configuration violated {sorted(result.violations)} "
        f"under {scenario_name} with K={workers}"
    )
    assert result.states > 1


def test_dropping_the_index_alone_still_breaks_the_single_head_invariant() -> None:
    """The arm the sequential ablation reported as making no difference.

    If this ever stops finding a counterexample, the model has lost the race it
    exists to describe, not the system.
    """
    result = model.check(
        _by_name("minus_head_index"),
        model.scenario(model.DISTINCT_ACTIONS, 2),
    )
    trace = result.violations.get("single_active_head")
    assert trace is not None
    assert any("insert head 1" in step for step in trace)


def test_dropping_the_claim_cas_alone_still_duplicates_the_effect() -> None:
    result = model.check(_by_name("minus_claim_cas"), model.scenario(model.SHARED_ACTION, 2))
    assert "single_effect_per_action" in result.violations
    assert "single_claim" in result.violations
