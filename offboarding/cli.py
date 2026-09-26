"""Run an offboarding from the terminal.

Dry run by default. Pass --execute to make real changes.

    python -m offboarding.cli --email alex.test@example.com --ticket IT-123
    python -m offboarding.cli --email alex.test@example.com --ticket IT-123 --execute
"""

import argparse
import sys

from offboarding.config import ConfigError, load_config
from offboarding.offboard import run_offboarding
from offboarding.okta_client import OktaClient

# How each step result is shown in the terminal. Plain text so it works in any console.
RESULT_LABELS = {
    "success": "OK",
    "already_done": "ALREADY DONE",
    "would_do": "WOULD DO",
    "skipped": "SKIPPED",
    "error": "ERROR",
}


def parse_args():
    """Read the command-line options."""
    parser = argparse.ArgumentParser(description="Offboard a user from Okta.")
    parser.add_argument("--email", required=True, help="The user's Okta login email.")
    parser.add_argument("--ticket", required=True, help="Ticket ID, for example IT-123.")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Make real changes. Without this flag nothing is changed (dry run).",
    )
    return parser.parse_args()


def print_summary(summary):
    """Print the summary returned by run_offboarding as a readable report."""
    mode = "DRY RUN" if summary["dry_run"] else "EXECUTE"
    print()
    print(f"Offboarding {summary['email']}   ticket {summary['ticket_id']}   [{mode}]")
    print(f"Run ID: {summary['run_id']}")
    print()

    for step in summary["steps"]:
        label = RESULT_LABELS.get(step["result"], step["result"])
        line = f"  {label:<13} {step['action']}"
        if step["detail"]:
            line += f"   ({step['detail']})"
        print(line)

    print()
    print(f"Overall status: {summary['status']}")
    if summary["dry_run"]:
        print("Nothing was changed. Re-run with --execute to apply.")


def main():
    args = parse_args()

    try:
        config = load_config()
    except ConfigError as e:
        print(e, file=sys.stderr)
        return 2

    client = OktaClient(config)
    # --execute is the only way to turn dry run off.
    summary = run_offboarding(client, args.email, args.ticket, dry_run=not args.execute)
    print_summary(summary)

    # Exit code 0 only on full success, so other scripts can check the result.
    return 0 if summary["status"] == "SUCCESS" else 1


if __name__ == "__main__":
    sys.exit(main())
