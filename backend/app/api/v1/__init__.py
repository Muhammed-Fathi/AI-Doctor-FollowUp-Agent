"""Versioned HTTP surface (``API_CONTRACT.md`` §2).

Phase 2 exposed routes live here and nowhere else:

* ``auth`` — login / me / logout (public sign-in, bearer session),
* ``doctor`` — assignment-scoped patient reads,
* ``patient`` — self-scoped check-in writes and reads,
* ``demo`` — admin-only dataset reset (guarded by ``DEMO_MODE``).

``GET /api/v1/demo/status`` is deliberately absent (``OQ-P2-01``, deferred to
P5); no ``/demo/seed`` route exists in any phase — first-run accounts come from
the local ``python -m app.services.seed`` bootstrap.
"""

__all__: list[str] = []
