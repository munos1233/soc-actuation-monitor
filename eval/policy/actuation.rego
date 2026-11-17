# External policy comparator for the actuation-integrity evaluation.
#
# This is the strongest policy we could write for an OPA sidecar consulted at the
# same four decision points as the in-system mediators. It is a comparator, not a
# straw man: every rule below is one a competent platform team would write, and
# several of them are rules the in-system mediators also enforce.
#
# What the policy can decide is bounded by what a sidecar is handed. The request
# document carries the proposed action, the event as the caller reports it, and
# the outbound envelope. It does not carry the recorded approval row, the
# writeback head table, or the vendor's own account of what it applied, because a
# sidecar does not have a transaction on the caller's database. Where a rule below
# is absent, it is absent for that reason and not for want of trying; the
# evaluation reports those cells rather than hiding them.
#
# Decision points (input.decision):
#   close   — may this event transition to CLOSED
#   bind    — may this approved action be dispatched
#   verify  — may this observation count as a performed effect
#   egress  — may this envelope leave for the vendor

package actuation

import rego.v1

# ---------------------------------------------------------------------------
# Aggregate decision. Deny wins, and the reasons travel with it so the harness
# can tell an over-block apart from a prevented harm.
# ---------------------------------------------------------------------------

default allow := false

allow if count(deny) == 0

high_impact_tools := {"isolate_host", "disable_account", "block_ip"}

# The vendor writeback envelope schema, enumerated so that a field nobody
# designed in is refused rather than forwarded. This is the same closed-world
# allowlist the in-system guard keeps, written out by hand because a sidecar has
# no access to the caller's type definitions.
allowed_egress_fields := {
	"action_id",
	"closure_cycle",
	"disposition_id",
	"execution_owner",
	"idempotency_key",
	"intent_kind",
	"operation_code",
	"operation_params",
	"operator_id",
	"parent_disposition_id",
	"source_concurrency_token",
	"source_locator",
	"supersedes_disposition_id",
	"target_results",
}

# ---------------------------------------------------------------------------
# close — closure evidence
# ---------------------------------------------------------------------------

# A ticket that still has an approved action nobody ran is not finished. The
# caller reports the count, so a planner that lies about it is believed.
deny contains "close:unrun_approved_action" if {
	input.decision == "close"
	input.event.pending_approved_actions > 0
}

# Closure requires a report. A structural field, so the sidecar can see it.
deny contains "close:no_report" if {
	input.decision == "close"
	not input.event.has_report
}

# A terminal writeback must be on the plan. Its delivery cannot be required here,
# because closure is what activates it: demanding delivery would refuse every
# legitimate close, which is an over-block and not a finding. Whether the head
# that eventually goes out is the active one for the current closure cycle is not
# a question a sidecar can answer, and no rule below pretends otherwise.
deny contains "close:no_terminal_writeback" if {
	input.decision == "close"
	not input.event.terminal_writeback_planned
}

# A receipt the vendor marked simulated cannot support closure in a deployment
# that claims a live disposition path. In a mock deployment it can, which is why
# the rule is conditioned on the declared mode rather than applied flatly.
deny contains "close:simulated_receipt_in_live_mode" if {
	input.decision == "close"
	input.event.disposition_mode != "mock_xdr"
	input.event.receipt_simulated
}

# ---------------------------------------------------------------------------
# bind — approval binding at dispatch
# ---------------------------------------------------------------------------

# Only approved actions may dispatch.
deny contains "bind:not_approved" if {
	input.decision == "bind"
	input.action.status != "approved"
}

# The plan revision the action carries must be the one the event is on. This
# catches a stale revision, but not a planner that renumbers both.
deny contains "bind:plan_revision_drift" if {
	input.decision == "bind"
	input.action.plan_revision != input.event.plan_revision
}

# High-impact tools require the level the approval was taken at. A planner that
# rewrites the level column defeats this, because the column is the only witness
# the sidecar has.
deny contains "bind:level_below_tool_requirement" if {
	input.decision == "bind"
	high_impact_tools[input.action.tool_name]
	input.action.action_level == "l1"
}

# ---------------------------------------------------------------------------
# verify — observation is not actuation
# ---------------------------------------------------------------------------

# An effect claimed with no observation behind it is not verified.
deny contains "verify:no_observation" if {
	input.decision == "verify"
	not input.observation.present
}

# An observation that merely echoes the request is not evidence.
deny contains "verify:echo_only" if {
	input.decision == "verify"
	input.observation.echoes_request
}

# A deferred action has not been performed yet, whatever the tool returned.
deny contains "verify:deferred_not_performed" if {
	input.decision == "verify"
	input.action.execution_phase == "post_verify"
	not input.observation.effect_confirmed
}

# ---------------------------------------------------------------------------
# egress — what may leave for the vendor
# ---------------------------------------------------------------------------

# Field allowlist: anything outside it is refused rather than sanitised.
deny contains sprintf("egress:field_not_allowed:%v", [field]) if {
	input.decision == "egress"
	some field in input.envelope.fields
	not allowed_egress_fields[field]
}

# Narrative and credential shapes in an outbound value. Pattern matching on the
# value is the only leak control available to a policy that cannot know which
# text came from an analyst and which from a hostname.
deny contains "egress:narrative_in_value" if {
	input.decision == "egress"
	some value in outbound_values
	regex.match(`(?i)(investigation|lateral movement|confirmed|report|analysis|summary)`, value)
}

deny contains "egress:credential_in_value" if {
	input.decision == "egress"
	some value in outbound_values
	regex.match(`(?i)(bearer\s+[a-z0-9._~+/-]{8,}|sk-[a-z0-9-]{8,}|api[_-]?key)`, value)
}

# A target that is not a bare identifier is suspicious. Whitespace is the cheapest
# signal that something was appended to it.
deny contains "egress:target_not_atomic" if {
	input.decision == "egress"
	contains(input.envelope.canonical_target, " ")
}

outbound_values contains value if {
	some value in object.get(input.envelope, "values", [])
}

# The envelope must carry the locator the caller says the event belongs to. The
# caller passes the trusted locator alongside the payload, exactly as it does to
# the in-system guard, so the sidecar can compare the two. What it cannot do is
# establish which object the event actually belongs to: a caller that rewrites
# both sides consistently is believed, because the authoritative row lives in a
# database the sidecar has no transaction on.
deny contains "egress:locator_mismatch" if {
	input.decision == "egress"
	input.envelope.locator_supplied
	input.envelope.source_locator != input.event.trusted_locator
}
