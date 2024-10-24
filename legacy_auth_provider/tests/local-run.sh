#!/bin/bash
cd "$(dirname "${BASH_SOURCE[0]}")/../src"
export CLASSIC_DB_URI=mysql://readonly:ro99beta@127.0.0.1:6201/arXiv
export SQLALCHEMY_RECORD_QUERIES=true
export TRACKBACK_SECRET=low-risk-secret-s0dkd990.d
PORT=${PORT:-8080}
uvicorn legacy_auth_provider:app --port $PORT --log-config logging.conf
