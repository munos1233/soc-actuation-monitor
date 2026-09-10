#!/usr/bin/env python3
"""Probe whether the configured provider can serve the response_plan contract.

The real-planner evaluation arm needs three things from the provider that a
plain liveness ping does not exercise: JSON mode, a response that validates
against ``ResponsePlanLLMResponse``, and a latency the matrix can afford. This
script reports all three and never prints the API key or the raw body.

Usage:
  cd backend && uv run --frozen python ../scripts/llm_planner_probe.py [--trials N]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import statistics

_SYSTEM = (
    "You are a SOC response planner. Propose containment actions for the event "
    "described by the user. Reply with a single JSON object with keys 'actions' "
    "(a list of objects with tool_name, target_type, target, parameters, reason) "
    "and 'strategy_summary'."
)
_USER = (
    "Event: host WKS-4417 shows credential dumping followed by an outbound "
    "transfer to an unrecognised domain. Confidence high. Propose at most two "
    "containment actions."
)


async def _run(trials: int) -> int:
    from app.agents.prompts.response_prompt import ResponsePlanLLMResponse
    from app.core.config import get_settings
    from app.core.llm.base import InMemoryLLMCallAuditRecorder, LLMMessage
    from app.core.llm.diagnostics import classify_llm_error
    from app.core.llm.factory import get_llm_client

    settings = get_settings()
    audit = InMemoryLLMCallAuditRecorder()
    client = get_llm_client(settings=settings, audit_recorder=audit)

    latencies: list[float] = []
    tokens: list[int] = []
    parsed_ok = 0
    action_counts: list[int] = []
    failures: list[str] = []

    try:
        for index in range(trials):
            try:
                response = await client.chat(
                    [
                        LLMMessage(role="system", content=_SYSTEM),
                        LLMMessage(role="user", content=_USER),
                    ],
                    event_id=f"evt-planner-probe-{index}",
                    agent_name="PlannerProbe",
                    prompt_key="response_plan",
                    temperature=0.3,
                    max_tokens=1024,
                    response_model=ResponsePlanLLMResponse,
                )
            except Exception as exc:  # noqa: BLE001 — the probe reports, not raises
                error_class, error_code = classify_llm_error(exc=exc)
                failures.append(f"{type(exc).__name__}:{error_class}:{error_code}")
                continue
            latencies.append(response.latency_ms)
            tokens.append(response.total_tokens)
            if isinstance(response.parsed, ResponsePlanLLMResponse):
                parsed_ok += 1
                action_counts.append(len(response.parsed.actions))
            else:
                failures.append("unparsed")
    finally:
        closer = getattr(client, "aclose", None)
        if closer is not None:
            await closer()

    report = {
        "model": settings.llm_primary_model,
        "trials": trials,
        "json_schema_parsed": f"{parsed_ok}/{trials}",
        "actions_per_plan": action_counts,
        "latency_ms": {
            "min": round(min(latencies)) if latencies else None,
            "median": round(statistics.median(latencies)) if latencies else None,
            "max": round(max(latencies)) if latencies else None,
        },
        "total_tokens": {
            "median": round(statistics.median(tokens)) if tokens else None,
            "sum": sum(tokens),
        },
        "failures": failures,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if parsed_ok == trials else 1


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=3)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(_run(args.trials)))


if __name__ == "__main__":
    main()
