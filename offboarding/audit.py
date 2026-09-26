"""Write audit records for offboarding runs.

Each record is one JSON object on its own line in logs/audit.jsonl (the
"JSON Lines" format). The file is only ever appended to, never rewritten,
so it doubles as evidence for compliance reviews.
"""

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

# logs/audit.jsonl in the project root, no matter which folder you run from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUDIT_LOG_PATH = PROJECT_ROOT / "logs" / "audit.jsonl"

# The only results a record may have. Catches typos like "sucess".
VALID_RESULTS = {"success", "skipped", "already_done", "would_do", "error"}


def new_run_id():
    """Return a new unique ID that ties together every record from one run."""
    return str(uuid.uuid4())


def log_event(*, run_id, ticket_id, target_user, action, dry_run, result, detail=""):
    """Append one audit record to the log and return it.

    The * makes every argument keyword-only, so each call must name its
    values, for example result="success". With seven similar arguments,
    that stops two of them being swapped by accident.

    Never pass tokens or full API responses in detail.
    """
    if result not in VALID_RESULTS:
        raise ValueError(f"Unknown audit result: {result!r}")

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": run_id,
        "ticket_id": ticket_id,
        "target_user": target_user,
        "action": action,
        "dry_run": dry_run,
        "result": result,
        "detail": detail,
    }

    # Create logs/ the first time. exist_ok=True means "fine if it is already there".
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

    # "a" is append mode: each record goes at the end, nothing is overwritten.
    with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(record) + "\n")

    return record
