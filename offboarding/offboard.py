"""Runs the offboarding workflow for the user that is inputted."""
import requests
from offboarding import audit


def run_offboarding(client, email, ticket_id, dry_run=True):
    run_id = audit.new_run_id()
    steps = []

    def record(action, result, detail=""):
        steps.append({"action":action, "result":result, "detail": detail})
        audit.log_event(
            run_id=run_id,
            ticket_id=ticket_id,
            target_user=email,
            action=action,
            dry_run=dry_run,
            result=result,
            detail=detail

        )

    return {
        "run_id": run_id,
        "email": email,
        "ticket_id": ticket_id,
        "dry_run": dry_run,
        "status": "SUCCESS",
        "steps": steps,
    }