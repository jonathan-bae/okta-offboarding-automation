"""Load and validate settings from environment variables.

Values come from the real environment first, then from the .env file in the
project root. Missing or invalid values stop the program with a clear error.
"""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

REQUIRED_VARS = [
    "OKTA_DOMAIN",
    "OKTA_API_TOKEN",
    "SLACK_WEBHOOK_URL",
    "WEBHOOK_SHARED_SECRET",
]

# Values that mean "copied from .env.example but never filled in".
PLACEHOLDERS = {"", "replace-me"}


class ConfigError(Exception):
    """Raised when required settings are missing or invalid."""


# frozen=True makes the object read-only after creation.
# repr=False because we define our own __repr__ below that hides secrets.
@dataclass(frozen=True, repr=False)
class Config:
    okta_domain: str
    okta_api_token: str
    slack_webhook_url: str
    webhook_shared_secret: str

    def __repr__(self):
        # If this object is ever printed or logged, secrets stay hidden.
        return f"Config(okta_domain={self.okta_domain!r}, secrets=<hidden>)"


def load_config():
    """Read settings, validate them, and return a Config.

    Collects every problem before raising, so all of them can be fixed in one pass.
    """
    # Reads .env into os.environ. Variables already set in the real
    # environment win, so production can inject secrets without a .env file.
    load_dotenv()

    values = {}
    problems = []

    for name in REQUIRED_VARS:
        value = os.environ.get(name, "").strip()
        if value in PLACEHOLDERS:
            problems.append(f"{name} is missing or still a placeholder")
        values[name] = value

    # The API lives at the org URL: https, no trailing slash, no "-admin".
    domain = values["OKTA_DOMAIN"].rstrip("/")
    if domain and not domain.startswith("https://"):
        problems.append("OKTA_DOMAIN must start with https://")
    if domain.endswith("-admin.okta.com"):
        problems.append("OKTA_DOMAIN must be the org URL, without -admin")

    if problems:
        raise ConfigError("Configuration problems:\n  " + "\n  ".join(problems))

    return Config(
        okta_domain=domain,
        okta_api_token=values["OKTA_API_TOKEN"],
        slack_webhook_url=values["SLACK_WEBHOOK_URL"],
        webhook_shared_secret=values["WEBHOOK_SHARED_SECRET"],
    )
