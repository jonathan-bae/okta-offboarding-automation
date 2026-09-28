# Okta Offboarding Automation

A Python tool that safely offboards an employee in Okta from a ticket. It looks up the user, records their current state for the audit trail, revokes their active sessions, removes their Okta group memberships, and deactivates the account.

It is **safe by default**: every run is a dry run unless you explicitly pass `--execute`, and every step is written to an append-only audit log keyed to the ticket ID.

## What it does

Given an employee email and a ticket ID, the workflow runs these steps in order:

1. **Look up the user** by their Okta login. If the user doesn't exist, the run stops and reports `FAILED`.
2. **Snapshot current state.** The user's status and group names are written to the audit log *before* anything changes, so an offboarding can be reviewed or reversed by hand later.
3. **Revoke all active sessions.** This runs first because it is the most time-sensitive security control: it ends any logged-in session immediately.
4. **Remove group memberships.** Only groups of type `OKTA_GROUP` are removed. The built-in `Everyone` group (`BUILT_IN`) and app-managed groups (`APP_GROUP`) are skipped, because they can't or shouldn't be removed directly.
5. **Deactivate the user.**
6. **Report an overall status:**
   - `SUCCESS`: every step worked.
   - `PARTIAL`: sessions were revoked, but a group removal or the deactivation failed.
   - `FAILED`: the user couldn't be found or looked up, or revoking sessions failed.

### Safety design

| Feature | How it works |
|---|---|
| **Dry run by default** | Steps 1 and 2 are read-only and always run. Steps 3 to 5 only record what they *would* do, unless `--execute` is passed. |
| **Safe to re-run** | If the user is already deactivated (`DEPROVISIONED`), revoking sessions and deactivating are recorded as `already done` instead of failing. |
| **Keeps going on errors** | Each step catches its own errors, so one failed group removal doesn't stop the remaining steps. The failure is recorded and the run ends as `PARTIAL`. |
| **Audit trail** | Every step is appended to `logs/audit.jsonl` (JSON Lines). The file is only ever appended to, never rewritten. |
| **Secrets stay secret** | Credentials come from environment variables or a gitignored `.env` file. The config object hides secrets if it is ever printed or logged. |
| **Fail fast on bad config** | Missing or placeholder settings stop the program with one clear message listing every problem. |
| **Timeouts** | Every Okta API call uses a request timeout, so a hung connection can't stall a run. |

## Requirements

- Python 3.10+
- An Okta org and an API token (a free Okta developer tenant works for testing)

## Setup

```bash
git clone https://github.com/jonathan-bae/okta-offboarding-automation.git
cd okta-offboarding-automation

python -m venv .venv
# Windows:        .venv\Scripts\activate
# macOS / Linux:  source .venv/bin/activate

pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in real values. `.env` is gitignored and must never be committed.

| Variable | What it is |
|---|---|
| `OKTA_DOMAIN` | Your Okta org URL, for example `https://integrator-1234567.okta.com` (no trailing slash, no `-admin`) |
| `OKTA_API_TOKEN` | An Okta API token (Security > API > Tokens in the Admin Console). Use an admin account with only the permissions offboarding needs. |
| `SLACK_WEBHOOK_URL` | Slack incoming webhook, for the planned Slack summary |
| `WEBHOOK_SHARED_SECRET` | Shared secret for the planned webhook endpoint. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(32))"` |

All four are required by the config loader today, including the two used by planned features.

## Usage

Dry run (the default; nothing is changed):

```bash
python -m offboarding.cli --email alex.test@example.com --ticket IT-123
```

Real run:

```bash
python -m offboarding.cli --email alex.test@example.com --ticket IT-123 --execute
```

Example dry-run output:

```
Offboarding alex.test@example.com   ticket IT-123   [DRY RUN]
Run ID: 3f1c...

  OK            lookup_user   (ACTIVE)
  OK            snapshot   ({'status': 'ACTIVE', 'groups': ['Everyone', 'Engineering', 'VPN-Users']})
  WOULD DO      revoke_sessions
  SKIPPED       remove_group:Everyone   (BUILT_IN group)
  WOULD DO      remove_group:Engineering
  WOULD DO      remove_group:VPN-Users
  WOULD DO      deactivate
  OK            complete   (SUCCESS)

Overall status: SUCCESS
Nothing was changed. Re-run with --execute to apply.
```

**Exit codes**, so other scripts can check the result:

| Code | Meaning |
|---|---|
| `0` | `SUCCESS` |
| `1` | `PARTIAL` or `FAILED` |
| `2` | Configuration error |

## Audit log

Each step writes one JSON record to `logs/audit.jsonl`:

```json
{"timestamp": "2026-09-27T20:15:04.123456+00:00", "run_id": "3f1c...", "ticket_id": "IT-123", "target_user": "alex.test@example.com", "action": "revoke_sessions", "dry_run": false, "result": "success", "detail": ""}
```

All records from one run share a `run_id`. `result` is one of `success`, `skipped`, `already_done`, `would_do` or `error`. `logs/` is gitignored because it contains user data.

## Okta API calls

All requests send `Authorization: SSWS {token}` and `Accept: application/json`.

| Action | Method and path |
|---|---|
| Find user | `GET /api/v1/users/{login}` |
| List the user's groups | `GET /api/v1/users/{userId}/groups` |
| Revoke sessions | `DELETE /api/v1/users/{userId}/sessions` |
| Remove from group | `DELETE /api/v1/groups/{groupId}/users/{userId}` |
| Deactivate user | `POST /api/v1/users/{userId}/lifecycle/deactivate` |

## Project structure

```
offboarding/
  config.py        loads and validates environment variables
  okta_client.py   all Okta API calls
  audit.py         append-only JSON Lines audit log
  offboard.py      the offboarding workflow
  cli.py           command-line entry point
```

## Roadmap

Not built yet:

- **Slack summary** posted to `#it-offboarding` after each run, clearly labeled `DRY RUN` when applicable
- **Webhook endpoint** (Flask) so a ticketing or HR system can trigger offboarding, authenticated with the shared secret
- **Rate-limit handling**: on HTTP 429, wait for the `X-Rate-Limit-Reset` time and retry, up to 3 times
- **Tests** with `pytest` and `responses`, so the workflow is tested against mocked HTTP without touching a real Okta org

## How it was built

Built with Claude Code as an AI pair programmer.
