"""Demo administration routes (``API_CONTRACT.md`` §2.6).

Only ``POST /api/v1/demo/reset`` is implemented in P2. ``GET /demo/status`` is
deferred to P5 (``OQ-P2-01``) because the accepted response schema requires a
drafting-provider status that does not exist before P5.
"""

from __future__ import annotations

__all__: list[str] = []
