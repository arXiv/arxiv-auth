#
# Counter the error of SQL alchemy losing the connection to MySQL
#
# The log shows this, and it screws up the rest of execution.
# It seems like the connection object either expired, or some sort of connection error killed the
# connection.
# When this happens, purge the connection pool, and start the connection from scratch.
#
# {"asctime": "2024-10-10 14:37:01,040", "name": "arxiv_oauth2.sessions", "levelname": "ERROR", "message": "Setting up Tapir session failed.", "process": 9, "threadName": "MainThread", "exc_info": "Traceback (most recent call last):
#   File \"/opt/venv/lib/python3.11/site-packages/sqlalchemy/engine/base.py\", line 1967, in _exec_single_context
#     self.dialect.do_execute(
#   File \"/opt/venv/lib/python3.11/site-packages/sqlalchemy/engine/default.py\", line 941, in do_execute
#     cursor.execute(statement, parameters)
#   File \"/opt/venv/lib/python3.11/site-packages/MySQLdb/cursors.py\", line 179, in execute
#     res = self._query(mogrified_query)
#           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^
#   File \"/opt/venv/lib/python3.11/site-packages/MySQLdb/cursors.py\", line 330, in _query
#     db.query(q)
#   File \"/opt/venv/lib/python3.11/site-packages/MySQLdb/connections.py\", line 261, in query
#     _mysql.connection.query(self, query)
#
# MySQLdb.OperationalError: (2006, 'Server has gone away')
#
from typing import Callable

import MySQLdb  # type: ignore
import logging

import sqlalchemy.exc
from fastapi import FastAPI, Request
from sqlalchemy.engine import Engine
import asyncio
from starlette.types import Scope, Receive, Send


class MySQLRetryMiddleware:
    def __init__(self, app: FastAPI, engine: Engine = None, retry_attempts: int = 2, retry_delay: int = 1):
        self.app = app
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.engine = engine

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        attempt = 0
        while attempt <= self.retry_attempts:
            attempt += 1
            try:
                await self.app(scope, receive, send)
                return
            except MySQLdb.OperationalError:
                logging.error(f"MySQL OperationalError detected (attempt {attempt}). Disposing engine.")
                if attempt > self.retry_attempts:
                    raise
                pass
            except sqlalchemy.exc.OperationalError:
                logging.error(f"MySQL OperationalError detected (attempt {attempt}). Disposing engine.")
                if attempt > self.retry_attempts:
                    raise

            self.engine.dispose()
            await asyncio.sleep(self.retry_delay)
