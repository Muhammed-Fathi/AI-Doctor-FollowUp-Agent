"""P5 agent package — typed shared-state contract only (P5-S0).

This package currently contains the strict, JSON-round-trippable shared-state
models in :mod:`app.agents.state`. It deliberately contains **no** graph,
checkpointer, node, tool adapter, model client, HTTP route, task or
notification implementation; those are later, separately authorized P5 scopes.

Validation of these models proves *shape* only — never authentication,
authorization, clinical grounding, execution permission or policy approval.

EDUCATIONAL / SYNTHETIC DATA / NOT FOR CLINICAL USE.
"""

__all__ = ["state"]
