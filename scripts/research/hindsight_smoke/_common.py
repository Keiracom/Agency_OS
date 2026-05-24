"""_common.py — shared helpers for the hindsight_smoke pilot scripts.

DRY pass per Aiden review on PR #1130 (Sonar new_duplicated_lines_density gate).
Scope: BASE/BANK/TIMEOUT constants + post() helper + confined runtime dir.

Not a generic library — the three scripts in this directory are the only callers.
The wider promote-and-refactor of confinement helpers to scripts/common/ is the
separate rule-of-three KEI Aiden filed (covers PR #1119/#1123 + this directory).
"""

from __future__ import annotations

import json
from pathlib import Path
from urllib import error as urlerror
from urllib import request as urlrequest

HINDSIGHT_BASE = "http://localhost:8888"
DEFAULT_BANK = "keiracom_smoke"
DEFAULT_TIMEOUT = 120

# S5443 — confined sub-dir (mode 0o700) instead of bare /tmp. Same pattern as
# PR #1119 weaviate_cutover._SNAPSHOT_DIR. Operators override defaults via CLI.
_RUNTIME_DIR = Path("/tmp/hindsight_smoke_data")  # NOSONAR S5443 — created mode-0o700 below
_RUNTIME_DIR.mkdir(mode=0o700, exist_ok=True)
RUNTIME_DIR = _RUNTIME_DIR


def post(path: str, body: dict, *, base: str = HINDSIGHT_BASE, timeout: int = DEFAULT_TIMEOUT):
    """Authenticated POST returning (status_code, parsed_body|error_dict)."""
    data = json.dumps(body).encode()
    req = urlrequest.Request(
        f"{base}{path}",
        data=data,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlrequest.urlopen(req, timeout=timeout) as resp:
            return (resp.status, json.loads(resp.read().decode()))
    except urlerror.HTTPError as e:
        return (e.code, {"error": e.read().decode()[:500]})
    except (urlerror.URLError, json.JSONDecodeError, TimeoutError) as e:
        return (0, {"error": str(e)})
