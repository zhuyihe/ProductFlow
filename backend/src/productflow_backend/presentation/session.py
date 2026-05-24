from __future__ import annotations

import json
import threading
from base64 import b64encode
from collections.abc import Mapping
from typing import Any

from itsdangerous import TimestampSigner
from starlette.middleware.sessions import SessionMiddleware

SESSION_TIMESTAMP_ROLLBACK_TOLERANCE_SECONDS = 5


class MonotonicTimestampSigner(TimestampSigner):
    """Keep session timestamp validation stable if wall-clock time briefly moves backward."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._timestamp_lock = threading.Lock()
        self._last_timestamp = 0

    def get_timestamp(self) -> int:
        current_timestamp = super().get_timestamp()
        with self._timestamp_lock:
            if self._last_timestamp <= current_timestamp:
                self._last_timestamp = current_timestamp
            elif self._last_timestamp - current_timestamp > SESSION_TIMESTAMP_ROLLBACK_TOLERANCE_SECONDS:
                self._last_timestamp = current_timestamp
            return self._last_timestamp


class ClockStableSessionMiddleware(SessionMiddleware):
    """Starlette session middleware with process-local monotonic timestamp signing."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.signer = MonotonicTimestampSigner(self.signer.secret_key)


def build_signed_session_cookie_value(session_data: Mapping[str, Any], *, secret_key: str) -> str:
    """Return the Starlette-compatible signed value for the browser `session` cookie."""

    payload = b64encode(json.dumps(dict(session_data)).encode("utf-8"))
    return MonotonicTimestampSigner(secret_key).sign(payload).decode("utf-8")
