"""Runs the offboarding workflow for the user that is inputted."""
import requests
from offboarding import audit


def run_offboarding(client, email, ticket_id, dry_run=True):
    run_id = audit.new_run_id()
    steps = []

    def record(action, result, detail=""):
        steps.append({"action":action, "result":result, "detail":detail})
        audit.log_event(
            run_id=run_id,
            ticket_id=ticket_id,
            target_user=email,
            action=action,
            dry_run=dry_run,
            result=result,
            detail=detail

        )

    def finish(status):
        result = "success" if status == "SUCCESS" else "error"
        record("complete", result, status)
        return {
            "run_id": run_id,
            "email": email,
            "ticket_id": ticket_id,
            "dry_run": dry_run,
            "status": status,
            "steps": steps,
        }

    # Step 1: look up the user
    try:
        user = client.get_user(email)
    except requests.RequestException as e:
        record("lookup_user", "error", str(e))
        return finish("FAILED")

    if user is None:
        record("lookup_user", "error", "user not found")
        return finish("FAILED")

    record("lookup_user", "success", user["status"])
    user_id = user["id"]

    # Step 2: snapshot status and groups before changing anything
    try:
        groups = client.list_groups(user_id)
    except requests.RequestException as e:
        record("snapshot", "error", str(e))
        return finish("FAILED")

    group_names = [g["profile"]["name"] for g in groups]
    record("snapshot", "success", {"status": user["status"], "groups": group_names})

    already_deactivated = user["status"] == "DEPROVISIONED"
    failed = False       # a critical step failed, so the overall result is FAILED
    had_errors = False   # any other step failed, so the overall result is PARTIAL

    # Step 3: revoke sessions first; it is the most time-sensitive control
    if already_deactivated:
        record("revoke_sessions", "already_done", "user is deactivated")
    elif dry_run:
        record("revoke_sessions", "would_do")
    else:
        try:
            client.revoke_sessions(user_id)
            record("revoke_sessions", "success")
        except requests.RequestException as e:
            record("revoke_sessions", "error", str(e))
            failed = True

    # Step 4: remove Okta groups only; skip BUILT_IN (Everyone) and APP_GROUP
    for group in groups:
        name = group["profile"]["name"]
        action = f"remove_group:{name}"

        if group["type"] != "OKTA_GROUP":
            record(action, "skipped", f"{group['type']} group")
        elif dry_run:
            record(action, "would_do")
        else:
            try:
                client.remove_from_group(group["id"], user_id)
                record(action, "success")
            except requests.RequestException as e:
                record(action, "error", str(e))
                had_errors = True

    # Step 5: deactivate, unless it is already done
    if already_deactivated:
        record("deactivate", "already_done")
    elif dry_run:
        record("deactivate", "would_do")
    else:
        try:
            client.deactivate(user_id)
            record("deactivate", "success")
        except requests.RequestException as e:
            record("deactivate", "error", str(e))
            had_errors = True

    # Step 6: overall status
    if failed:
        return finish("FAILED")
    if had_errors:
        return finish("PARTIAL")
    return finish("SUCCESS")
