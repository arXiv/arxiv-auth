import logging
import subprocess
import json
import requests
from typing import List

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(message)s',
                    handlers=[logging.StreamHandler()])

def find_value(fields: List[dict], id: str) -> str | None:
    for field in fields:
        if field.get('id') == id:
            return field.get('value')
    return None

def get_username_password(op_id: str) -> (str, str):
    entry = subprocess.check_output(['op', 'item', 'get', op_id, '--format=json'], encoding='utf-8')
    cred = json.loads(entry)
    fields = cred['fields']
    return (find_value(fields, "username"), find_value(fields, "password"))

def get_bearer_token(op_id: str, hostname: str, realm: str = 'master', cliend_id="admin-cli") -> str | None:
    token_url = f"{hostname}/realms/{realm}/protocol/openid-connect/token"
    name, pw = get_username_password(op_id)
    payload = {
        'client_id': cliend_id,
        'username': name,
        'password': pw,
        'grant_type': 'password',
        'scope': 'openid'
    }
    response = requests.post(token_url, data=payload,
                             headers={'Content-Type': 'application/x-www-form-urlencoded'})

    if response.status_code == 200:
        logging.debug(f"Bearer token: {response.json()}")
        token_response = response.json()
        return token_response.get("access_token")
    logging.debug("No Bearer token $s", response.text)
    return None


def clear_cache(op_id: str, hostname: str, realm: str = "master", which: List[str] | None = None, **args):
    # which can be "realm", "user", "keys"
    token = get_bearer_token(op_id, hostname, realm=realm, **args)
    if not token:
        logging.info("Jim, he is dead.")
        exit(1)

    if which is None:
        which = ["user"]

    for thing in which:
        logging.debug("clearing %s.", thing)
        keycloak_url = f"{hostname}/admin/realms/{realm}/clear-{thing}-cache"
        response = requests.post(keycloak_url,
                                 headers={'Authorization': 'Bearer ' + token})
        if response.status_code >= 200 and response.status_code < 300:
            logging.info("%s is cleared.", thing)
        else:
            logging.info("%s not cleared. %s", thing, str(response.text))



if __name__ == "__main__":
    clear_cache("bdmmxlepkfsqy5hfgfunpsli2i",
                "https://keycloak-service-6lhtms3oua-uc.a.run.app",
                which=['user', 'realm', 'keys'])
