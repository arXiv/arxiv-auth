"""Tests for :mod:`accounts.services.foo`."""

from unittest import mock, TestCase
from functools import partial
import json
import requests
from accounts.services import baz
from accounts.domain import Baz

from typing import Any, Optional


class TestBazServiceStatus(TestCase):
    """The method :meth:`.status` indicates the status of the Baz service."""

    @mock.patch('accounts.services.baz.requests.Session')
    def test_status_true_when_remote_is_ok(self, mock_session: Any) -> None:
        """If the remote baz service is OK, :meth:`.status` returns True."""
        mock_get_response = mock.MagicMock(status_code=200, ok=True)
        mock_get = mock.MagicMock(return_value=mock_get_response)
        mock_session_instance = mock.MagicMock()
        type(mock_session_instance).get = mock_get
        mock_session.return_value = mock_session_instance

        bazSession = baz.BazServiceSession('foo')
        self.assertTrue(bazSession.status())

    @mock.patch('accounts.services.baz.requests.Session')
    def test_status_false_when_remote_not_ok(self, mock_session: Any) -> None:
        """If the remote baz service isn't ok :meth:`.status` returns False."""
        mock_head_response = mock.MagicMock(status_code=503, ok=False)
        mock_head = mock.MagicMock(return_value=mock_head_response)
        mock_session_instance = mock.MagicMock()
        type(mock_session_instance).head = mock_head
        mock_session.return_value = mock_session_instance

        bazSession = baz.BazServiceSession('foo')
        self.assertFalse(bazSession.status())

    @mock.patch('accounts.services.baz.requests.Session')
    def test_status_false_when_error_occurs(self, mock_session: Any) -> None:
        """If there is a problem calling baz :meth:`.status` returns False."""
        mock_head = mock.MagicMock(side_effect=requests.exceptions.HTTPError)
        mock_session_instance = mock.MagicMock()
        type(mock_session_instance).head = mock_head
        mock_session.return_value = mock_session_instance

        bazSession = baz.BazServiceSession('foo')
        self.assertFalse(bazSession.status())


class TestBazServiceRetrieve(TestCase):
    """The method :meth:`.retrieve_baz` is for getting baz."""

    @mock.patch('accounts.services.baz.requests.Session')
    def test_returns_none_when_not_found(self, mock_session: Any) -> None:
        """If there is no such baz, returns None."""
        mock_get_response = mock.MagicMock(status_code=404, ok=False)
        mock_get = mock.MagicMock(return_value=mock_get_response)
        mock_session_instance = mock.MagicMock()
        type(mock_session_instance).get = mock_get
        mock_session.return_value = mock_session_instance

        bazSession = baz.BazServiceSession('foo')
        self.assertIsNone(bazSession.retrieve_baz(4))

    @mock.patch('accounts.services.baz.requests.Session')
    def test_returns_baz_when_valid_json(self, mock_session: Any) -> None:
        """If there is a baz, returns a :class:`.Baz`."""
        mock_json = mock.MagicMock(return_value={
            'city': 'fooville',
            'ip_decimal': 12346
        })
        mock_get_response = mock.MagicMock(status_code=200, ok=True,
                                           json=mock_json)
        mock_get = mock.MagicMock(return_value=mock_get_response)
        mock_session_instance = mock.MagicMock()
        type(mock_session_instance).get = mock_get
        mock_session.return_value = mock_session_instance

        bazSession = baz.BazServiceSession('foo')
        thebaz = bazSession.retrieve_baz(4)
        self.assertIsInstance(thebaz, Baz)
        if isinstance(thebaz, Baz):
            self.assertEqual(thebaz.foo, 'fooville')
            self.assertEqual(thebaz.mukluk, 12346)

    @mock.patch('accounts.services.baz.requests.Session')
    def test_raise_ioerror_when_status_not_ok(self, mock_session: Any) -> None:
        """If the the baz service returns a bad status, raises IOError."""
        mock_get_response = mock.MagicMock(status_code=500, ok=False)
        mock_get = mock.MagicMock(return_value=mock_get_response)
        mock_session_instance = mock.MagicMock()
        type(mock_session_instance).get = mock_get
        mock_session.return_value = mock_session_instance

        bazSession = baz.BazServiceSession('foo')
        with self.assertRaises(IOError):
            bazSession.retrieve_baz(4)

    @mock.patch('accounts.services.baz.requests.Session')
    def test_raises_ioerror_when_data_is_bad(self, mock_session: Any) -> None:
        """If the the baz service retrieves non-JSON data, raises IOError."""
        def raise_decoderror() -> None:
            raise json.decoder.JSONDecodeError('msg', 'doc', 0)

        mock_json = mock.MagicMock(side_effect=raise_decoderror)
        mock_get_response = mock.MagicMock(status_code=200, ok=True,
                                           json=mock_json)
        mock_get = mock.MagicMock(return_value=mock_get_response)
        mock_session_instance = mock.MagicMock()
        type(mock_session_instance).get = mock_get
        mock_session.return_value = mock_session_instance

        bazSession = baz.BazServiceSession('foo')
        with self.assertRaises(IOError):
            bazSession.retrieve_baz(4)
