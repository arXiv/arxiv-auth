"""Provides a unified API for sending arXiv email."""

import smtplib
from flask import current_app, g


class MailSession(object):
    """An open session with an SMTP service."""

    def __init__(self, host: str = "", port: int = 0) -> None:
        self._host = host
        self._port = port
        self._conn = self._new_connection()

    def _new_connection(self) -> smtplib.SMTP:
        return smtplib.SMTP(
            host=self._host,
            port=self._port
        )

    def send_message(self, message: Message) -> None:
