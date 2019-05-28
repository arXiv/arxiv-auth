"""Mock endpoint for Vault secrets."""

from flask import Flask, send_file, jsonify, request
from datetime import datetime
from pytz import UTC

application = Flask(__name__)

TOK_ID = 0
KV_ID = 0
AWS_ID = 0

tokens = {}


@application.route('/v1/auth/kubernetes/login', methods=['POST'])
def log_in():
    global TOK_ID
    TOK_ID += 1
    tokens[TOK_ID] = datetime.now(UTC)
    request.data, request.get_json()
    return jsonify({'auth': {'client_token': f'{TOK_ID}'}})


@application.route('/v1/secret/data/<path>')
def get_kv_secret(path):
    global KV_ID
    KV_ID += 1
    request.data
    return jsonify({
        "request_id": f"foo-request-{KV_ID}",
        "lease_id": "",
        "renewable": False,
        "lease_duration": 0,
        "data": {
            "data": {
                "jwt-secret": "foosecret"
            },
            "metadata": {
                "created_time": "2019-04-18T12:58:32.820693897Z",
                "deletion_time": "",
                "destroyed": False,
                "version": 1
            }
        },
        "wrap_info": None,
        "warnings": None,
        "auth": None
    })


@application.route('/v1/aws/creds/<role>')
def get_aws_secret(role):
    """Get an AWS credential."""
    global AWS_ID
    AWS_ID += 1
    request.data
    return jsonify({
        "request_id": f"a-request-id-{AWS_ID}",
        "lease_id": f"aws/creds/{role}/a-lease-id-{AWS_ID}",
        "renewable": True,
        "lease_duration": 3600,
        "data": {
            "access_key": "ASDF1234",
            "secret_key": "xljadslklk3mlkmlkmxklmx09j3990j",
            "security_token": None
        },
        "wrap_info": None,
        "warnings": None,
        "auth": None
    })


@application.route('/v1/database/creds/<role>', methods=['GET', 'POST'])
def get_database_creds(role):
    return jsonify({
        "request_id": "303d63bd-e2f3-cfcd-75c1-1c18af2d26a8",
        "lease_id": f"database/creds/{role}/4544a565-6946-20e7-d407-2c7dfc9ea779",
        "renewable": True,
        "lease_duration": 1800,
        "data": {
            "password": "foo-USr5K5e3KyXOSDfB",
            "username": "v-root-filemanage-annxS09rxJIaWu"
        },
        "wrap_info": None,
        "warnings": [
            "TTL of \"1h0m0s\" exceeded the effective max_ttl of \"30m0s\"; TTL value is capped accordingly"
        ],
        "auth": None
    })


@application.route('/v1/auth/token/lookup-self', methods=['GET', 'POST'])
@application.route('/v1/auth/token/lookup', methods=['GET', 'POST'])
def look_up_a_token():
    """Look up an auth token."""
    try:
        data = request.get_json(force=True)
    except Exception:
        data = None
    if data:
        tok = data['token']
    else:
        tok = request.headers.get('TOK_ID')
    request.data

    try:
        creation_time = int(round(datetime.timestamp(tokens[tok]), 0))
        issue_time = tokens[tok].isoformat()
    except Exception:
        _now = datetime.now(UTC)
        creation_time = int(round(datetime.timestamp(_now)))
        issue_time = _now.isoformat()
        tokens[tok] = _now
    expire_time = datetime.fromtimestamp(creation_time + 2764790)

    return jsonify({
      "data": {
        "accessor": "8609694a-cdbc-db9b-d345-e782dbb562ed",
        "creation_time": creation_time,
        "creation_ttl": 2764800,
        "display_name": "fooname",
        "entity_id": "7d2e3179-f69b-450c-7179-ac8ee8bd8ca9",
        "expire_time": expire_time.isoformat(),
        "explicit_max_ttl": 0,
        "id": tok,
        "identity_policies": [
          "dev-group-policy"
        ],
        "issue_time": issue_time,
        "meta": {
          "username": "tesla"
        },
        "num_uses": 0,
        "orphan": True,
        "path": "auth/kubernetes/login",
        "policies": [
          "default"
        ],
        "renewable": True,
        "ttl": 2764790
      }
    })
