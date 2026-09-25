"""
Tool that is used to interact with the OKTA API.
"""

import requests
TIMEOUT_SECONDS = 10


class OktaClient:
    """Class used to talk to the OKTA API"""
    def __init__(self, config):
        self.base_url = config.okta_domain
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Authorization": f"SSWS {config.okta_api_token}",
        })

    def get_user(self, login):
        """Returns the user as a dictionary or None if not found"""
        url = f"{self.base_url}/api/v1/users/{login}"
        resp = self.session.get(url, timeout=TIMEOUT_SECONDS)

        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    def list_groups(self, user_id):
        """Returns the list of groups for the user."""
        url = f"{self.base_url}/api/v1/users/{user_id}/groups"
        resp = self.session.get(url, timeout=TIMEOUT_SECONDS)

        resp.raise_for_status()
        return resp.json()

    def revoke_sessions(self, user_id):
        """This method logs the user out of everything."""
        url = f"{self.base_url}/api/v1/users/{user_id}/sessions"
        resp = self.session.delete(url, timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()

    def remove_from_group(self, group_id, user_id):
        """This removes user from ONE group"""
        url = f"{self.base_url}/api/v1/groups/{group_id}/users/{user_id}"
        resp = self.session.delete(url, timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()

    def deactivate(self, user_id):
        """Disables the account"""
        url = f"{self.base_url}/api/v1/users/{user_id}/lifecycle/deactivate"
        resp = self.session.post(url, timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()
