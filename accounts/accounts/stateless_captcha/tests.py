"""Tests for :mod:`accounts.captcha`."""

from unittest import TestCase
import io
from datetime import datetime, timedelta
from pytz import timezone, UTC
import jwt
from . import new, unpack, render, check, InvalidCaptchaToken, \
    InvalidCaptchaValue

EASTERN = timezone('US/Eastern')


class TestCaptcha(TestCase):
    """Tests for :mod:`accounts.captcha`."""

    def test_new_captcha(self):
        """Generate and render a new captcha token."""
        secret = 'foo'
        ip_address = '127.0.0.1'
        token = new(secret, ip_address)
        value = unpack(token, secret, ip_address)

        self.assertIsInstance(value, str, "The captcha value is returned")
        self.assertGreater(len(value), 0)

        data = render(token, secret, ip_address)
        self.assertIsInstance(data, io.BytesIO, "Bytes data are returned")
        self.assertTrue(data.read().startswith(b"\x89PNG"),
                        "Returns a PNG image")

    def test_not_a_token(self):
        """Something other than a captcha token is passed."""
        secret = 'foo'
        ip_address = '127.0.0.1'

        with self.assertRaises(InvalidCaptchaToken):
            unpack('nope', secret, ip_address)

        with self.assertRaises(InvalidCaptchaToken):
            check('nope', 'nada', secret, ip_address)

        with self.assertRaises(InvalidCaptchaToken):
            render('nope', secret, ip_address)

    def test_forged_captcha(self):
        """The captcha token cannot be decrypted."""
        secret = 'foo'
        ip_address = '127.0.0.1'

        forged_token = jwt.encode({
            'value': 'foo',
            'expires': (datetime.now(tz=UTC) + timedelta(seconds=3600)).isoformat()
        }, 'notthesecret').decode('ascii')

        with self.assertRaises(InvalidCaptchaToken):
            unpack(forged_token, secret, ip_address)

    def test_ip_address_changed(self):
        """The captcha token cannot be decrypted."""
        secret = 'foo'
        ip_address = '127.0.0.1'
        token = new(secret, ip_address)

        with self.assertRaises(InvalidCaptchaToken):
            render(token, secret, '10.10.10.10')

    def test_malformed_captcha(self):
        """The captcha token cannot be decrypted."""
        secret = 'foo'
        ip_address = '127.0.0.1'

        malformed_token = jwt.encode({
            'expires': (datetime.now(tz=UTC) + timedelta(seconds=3600)).isoformat()
        }, secret).decode('ascii')

        with self.assertRaises(InvalidCaptchaToken):
            unpack(malformed_token, secret, ip_address)

        malformed_token = jwt.encode({'value': 'foo'}, secret).decode('ascii')

        with self.assertRaises(InvalidCaptchaToken):
            unpack(malformed_token, secret, ip_address)

    def test_check_valid(self):
        """The correct value is passed."""
        secret = 'foo'
        ip_address = '127.0.0.1'
        token = new(secret, ip_address)
        value = unpack(token, secret, ip_address)
        self.assertIsNone(check(token, value, secret, ip_address))

    def test_check_invalid(self):
        """An incorrect value is passed."""
        secret = 'foo'
        ip_address = '127.0.0.1'
        token = new(secret, ip_address)
        with self.assertRaises(InvalidCaptchaValue):
            check(token, 'nope', secret, ip_address)
