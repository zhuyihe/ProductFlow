"""Health probes exposed to external SSO orchestrators.

The `/api/health/sso` endpoint is invoked by the new-api admin dashboard when
operators click "Test Connection". It returns a tiny JSON payload with the
ProductFlow version and a `supports_sso` flag derived from the runtime
configuration, so the dashboard can categorise the probe outcome without
spelunking through unrelated endpoints.

The endpoint is intentionally unauthenticated so admins can verify network
reachability before exchanging shared secrets. To discourage scanning it is
rate-limited via slowapi to 6 requests per minute per client IP.
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from productflow_backend.application.new_api_sso import is_new_api_sso_configured
from productflow_backend.config import get_settings

# Module-level limiter so the wiring code in presentation/api.py can attach
# the same instance to app.state. Sharing one limiter across modules keeps
# the per-IP counters consistent regardless of which router serves the probe.
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()


@router.get("/api/health/sso")
@limiter.limit("6/minute")
async def health_sso(request: Request) -> dict[str, object]:
    """Return the SSO readiness snapshot consumed by new-api Test Connection."""
    settings = get_settings()
    return {
        "ok": True,
        "version": "0.1.0",
        "supports_sso": is_new_api_sso_configured(settings),
    }
