"""
Tool that is used to interact with the OKTA API.
"""

import requests
TIMEOUT_SECONDS = 10


class OktaClient:
    def __init__(self, config):
        self.base_url = config.okta_domain
        self.session = requests.Session()
        self.session.headers.update({
            "Accept": "application/json",
            "Authorization": f"SSWS {config.okta_api_token}",

        })

    def get_user(self, login):
        url = f"{self.base_url}/api/v1/users/{login}"
        resp = self.session.get(url, timeout=TIMEOUT_SECONDS)

        if resp.status_code ==  404:
            return None
        resp.raise_for_status()
        return resp.json()




    
        
