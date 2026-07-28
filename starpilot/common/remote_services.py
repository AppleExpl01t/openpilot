#!/usr/bin/env python3
"""Kill switch for outbound connections to remote services.

Set REMOTE_SERVICES_DISABLED = False to restore stock behavior.

Covers:
  - log/video uploads (system/loggerd/uploader.py)
  - the athena websocket (system/athena/athenad.py, manage_athenad.py)
  - Sentry crash/error reporting (system/sentry.py)

Device registration against api.comma.ai is deliberately left alone so the
dongle ID still resolves; everything keyed to it keeps working.
"""

REMOTE_SERVICES_DISABLED = True
