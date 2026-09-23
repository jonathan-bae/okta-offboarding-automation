# Okta Offboarding Automation

## About this project

A portfolio project built to prepare for an IT Engineering role at Anduril Industries focused on service desk automation and employee self-service. The role calls for REST API and webhook workflow automation, onboarding/offboarding automation at scale, AI in support workflows, and security design thinking. Anduril's IT stack includes Okta, Google Workspace, Slack, Jira Service Management, and Confluence.

The project: when an employee leaves, a webhook triggers a Python service that safely offboards them in Okta and reports the result to Slack, with a dry-run mode and a full audit trail.

**Deadline:** working, documented, and pushed to GitHub by Sunday.

## Instructions for Claude Code (read first)

The developer is an experienced Linux systems engineer, fluent in Bash, PowerShell, and Ansible, but new to Python. He must be able to explain every line of this project in a technical interview. He uses the python-tutor output style. Follow it, with the split below.

### He writes these himself (tutor mode, no implementation)

- `okta_client.py` (user lookup, list groups, revoke sessions, remove from group, deactivate)
- `offboard.py` (the workflow orchestration)

For these files: explain what to build and where, describe the change conceptually, point to the relevant Python concept, and offer a small illustrative example that is NOT the solution. Review his code when he asks, pointing out bugs and improvements by describing them rather than rewriting them. Boundary test: if he could paste your code and be done, don't write it.

### You may write these directly, then explain them

- `config.py`, `audit.py`, `cli.py`, `app.py` (Flask), `slack_notifier.py`
- Retry and rate-limit handling (a helper his `okta_client.py` can call)
- Tests in `tests/`
- `requirements.txt`, `.env.example`, and README scaffolding

These are supporting code. Before writing each one, briefly explain what it does and why. After writing it, walk through it section by section so he can describe it in an interview.

### Always

- Build one milestone at a time, in the order below. Do not generate the whole project at once.
- Explain new Python concepts (dictionaries, exceptions, decorators, imports, virtual environments) using Bash or PowerShell comparisons where helpful.
- Keep code simple and readable over clever. Prefer plain functions and one small client class. Add short comments explaining intent.
- After each milestone, have him run it and confirm it works before moving on. Suggest a git commit with a clear message.
- Never print, log, or commit secrets. Never hardcode tokens or URLs.
- When there is a design choice, name the tradeoff in one or two sentences so he can speak to it in interviews.
- Do not use em dashes or double dashes in any prose, comments, or documentation.
- If he says he is behind schedule and explicitly asks for more help on `offboard.py`, you may give more direct guidance, but still have him write the final code.

## Tech stack

- Python 3.10+
- `requests` for HTTP calls
- `python-dotenv` for loading secrets from `.env`
- `flask` for the webhook endpoint
- `pytest` and `responses` for tests (mocked HTTP, no real API calls in tests)
- Okta free developer tenant (sandbox with fake users and groups)
- Slack incoming webhook posting to `#it-offboarding`

## Project structure

```
okta-offboarding-automation/
  CLAUDE.md
  README.md
  requirements.txt
  .env.example          # placeholder values only, safe to commit
  .env                  # real secrets, gitignored
  logs/                 # audit logs, gitignored
  offboarding/
    __init__.py
    config.py           # loads and validates environment variables
    okta_client.py      # all Okta API calls live here
    slack_notifier.py   # formats and sends the Slack summary
    audit.py            # writes JSON lines audit records
    offboard.py         # orchestrates the full offboarding workflow
    cli.py              # run offboarding from the terminal
    app.py              # Flask webhook endpoint
  tests/
    test_offboard.py
```

## Environment variables

```
OKTA_DOMAIN=https://integrator-XXXXXXX.okta.com
OKTA_API_TOKEN=
SLACK_WEBHOOK_URL=
WEBHOOK_SHARED_SECRET=   # any long random string; generate with: python -c "import secrets; print(secrets.token_urlsafe(32))"
```

`config.py` should fail fast with a clear error if any required variable is missing.

## Offboarding workflow

Given an employee email, a ticket ID, and a dry-run flag, `offboard.py` runs these steps in order:

1. **Look up the user** by login/email. If not found, stop and report "user not found."
2. **Snapshot current state:** record the user's status and group memberships in the audit log before changing anything. This supports audit review and manual rollback.
3. **Revoke all active sessions** so any logged-in sessions end immediately. This comes first because it is the most time-sensitive security control.
4. **Remove group memberships.** Only remove groups of type `OKTA_GROUP`. Skip the built-in `Everyone` group (type `BUILT_IN`), which cannot be removed, and skip `APP_GROUP` types.
5. **Deactivate the user.** If the user is already `DEPROVISIONED`, skip this step and record it as "already done."
6. **Send a Slack summary** with the ticket ID, user, each step's result, and whether it was a dry run.
7. **Write a final audit record** with an overall status.

In **dry-run mode**, steps 1 and 2 run for real (read-only), and steps 3 to 5 only log what *would* happen. The Slack message is clearly labeled `DRY RUN`. Dry run is the default everywhere; making real changes requires explicitly passing `--execute` (CLI) or `"dry_run": false` (webhook).

### Okta API reference

All requests use the header `Authorization: SSWS {OKTA_API_TOKEN}` and `Accept: application/json`.

| Action | Method and path |
|---|---|
| Find user | `GET /api/v1/users/{login}` |
| List user's groups | `GET /api/v1/users/{userId}/groups` |
| Revoke sessions | `DELETE /api/v1/users/{userId}/sessions` |
| Remove from group | `DELETE /api/v1/groups/{groupId}/users/{userId}` |
| Deactivate user | `POST /api/v1/users/{userId}/lifecycle/deactivate` |

Verify these against the current Okta API docs if anything behaves unexpectedly.

## Reliability requirements

- **Idempotent:** running the workflow twice on the same user must not error. Already-removed groups and already-deactivated users are treated as success ("already done").
- **Rate limits:** on HTTP 429, wait until the time in the `X-Rate-Limit-Reset` header (or back off), then retry. Maximum 3 retries.
- **Timeouts:** every HTTP request uses a timeout (for example, 10 seconds).
- **Partial failure:** each step records its own result. Overall status is `SUCCESS`, `PARTIAL` (some steps failed), or `FAILED` (user lookup failed or session revocation failed). A Slack failure must never fail the offboarding; log it and continue.

## Audit log

Append one JSON object per line to `logs/audit.jsonl`. Each record includes:

`timestamp` (UTC ISO 8601), `run_id` (UUID shared across one workflow run), `ticket_id`, `target_user`, `action`, `dry_run`, `result` (`success`, `skipped`, `already_done`, `would_do`, `error`), and `detail` (error message or extra context).

Never write tokens or full API responses containing unnecessary personal data to the log.

## Interfaces

### CLI

```
python -m offboarding.cli --email alex.test@example.com --ticket IT-123
python -m offboarding.cli --email alex.test@example.com --ticket IT-123 --execute
```

Default is dry run. Print a readable step-by-step summary to the terminal.

### Webhook

`POST /webhook/offboard`

Headers: `X-Webhook-Token: {WEBHOOK_SHARED_SECRET}`

Body:
```json
{ "email": "alex.test@example.com", "ticket_id": "IT-123", "dry_run": true }
```

Requirements:
- Reject missing or wrong tokens with 401. Compare using `hmac.compare_digest` to avoid timing attacks.
- Validate the body: email must look like an email, ticket_id required, dry_run defaults to true if missing. Return 400 on bad input.
- Return JSON with `run_id`, overall status, and per-step results.
- Also add `GET /health` returning `{"status": "ok"}`.

Test locally with curl.

## Tests

Use `pytest` with the `responses` library to mock Okta and Slack. Cover at minimum:

1. Dry run makes no write calls (no DELETE or POST to Okta).
2. Running on an already-deactivated user returns success with "already done."
3. The `Everyone` group is never removed.
4. A Slack failure does not change the offboarding result.
5. The webhook rejects a bad token with 401.

## README requirements

The README is part of the deliverable. Include:

- **One-paragraph summary** of the problem and what the tool does.
- **Architecture diagram** as a Mermaid flowchart: trigger (webhook or CLI) to offboarding service to Okta, Slack, and audit log.
- **Setup instructions** anyone could follow.
- **Demo:** example CLI output and a screenshot of the Slack message.
- **Design decisions:** why sessions are revoked first, why dry run is the default, how idempotency works, how partial failures are handled.
- **Security considerations:**
  - Offboarding as a zero-trust control: access ends immediately and every action is auditable.
  - Secrets kept in environment variables, never committed.
  - Webhook authentication with a shared secret and constant-time comparison.
  - Least privilege tradeoff: Okta API tokens inherit the full permissions of the admin who created them. In production, use an OAuth 2.0 service app with only the scopes needed (such as `okta.users.manage` and `okta.groups.manage`).
  - Audit log as evidence for compliance reviews.
- **Next steps / roadmap:** the stretch items below that were not completed.

## Milestones and schedule

| Day | Milestone | Done when |
|---|---|---|
| Wed | Setup | Okta tenant with 3 test users and 2 groups, Slack webhook, repo cloned, venv created, `.env` confirmed gitignored |
| Thu | Python basics and first API call | Claude Code writes `config.py`; he writes the lookup and list-groups functions in `okta_client.py` |
| Fri | Core workflow | He finishes `okta_client.py` and writes `offboard.py`; Claude Code writes `audit.py` and `cli.py`; works end to end in dry run and execute modes |
| Sat | Webhook, Slack, tests | `app.py` and `slack_notifier.py` work via curl; tests pass |
| Sun | Polish | README complete with diagram and screenshot; practice explaining the code out loud |

## Stretch goals (only after the core is done)

1. **LLM ticket triage:** a `/triage` endpoint that sends free-text ticket text to the Claude API and returns structured JSON: `category`, `is_offboarding`, `employee_email`, `summary`, `confidence`. It must never trigger offboarding directly. It posts a suggested action to Slack for human approval. This demonstrates AI with guardrails.
2. **Jira Service Management trigger:** a JSM automation rule that sends the webhook when an offboarding request is approved, using ngrok to expose the local endpoint.
3. **GitHub Actions:** run `pytest` on every push.

## Out of scope for this weekend

Terraform, Google Workspace suspension, a web UI, cloud deployment, a database. List these as roadmap items in the README.
