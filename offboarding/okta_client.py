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






    
        
