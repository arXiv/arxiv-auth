"""Tests for :mod:`accounts.controllers.registration`."""

from unittest import TestCase, mock
import hashlib
from base64 import b64encode
import os
import unittest

from werkzeug.datastructures import MultiDict
from flask import Flask

from arxiv import status

from arxiv_auth.legacy import util, models

from accounts.factory import create_web_app

from ..registration import register, edit_profile, view_profile
from ...stateless_captcha import InvalidCaptchaValue, InvalidCaptchaToken


class TestRegister(TestCase):
    """Tests for :func:`register`."""


    @classmethod
    def setUpClass(self):
        self.secret = 'bazsecret'
        self.db = 'db.sqlite'
        self.expiry = 500

    def setUp(self):
        self.ip_address = '10.1.2.3'
        self.environ_base = {'REMOTE_ADDR': self.ip_address}
        self.app = create_web_app()
        self.app.config['CLASSIC_COOKIE_NAME'] = 'foo_tapir_session'
        self.app.config['AUTH_SESSION_COOKIE_NAME'] = 'baz_session'
        self.app.config['AUTH_SESSION_COOKIE_SECURE'] = '0'
        self.app.config['SESSION_DURATION'] = self.expiry
        self.app.config['JWT_SECRET'] = self.secret
        self.app.config['CLASSIC_DATABASE_URI'] = f'sqlite:///{self.db}'
        self.app.config['CLASSIC_SESSION_HASH'] = 'xyz1234'
        self.app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{self.db}'
        self.app.config['REDIS_FAKE'] = True
        self.app.config['SERVER_NAME'] = 'example.com' # to do urls in emails

        with self.app.app_context():
            util.drop_all()
            util.create_all()

            with util.transaction() as session:
                # We have a good old-fashioned user.
                db_user = models.DBUser(
                    user_id=1,
                    first_name='first',
                    last_name='last',
                    suffix_name='iv',
                    email='first@last.iv',
                    policy_class=2,
                    flag_edit_users=1,
                    flag_email_verified=1,
                    flag_edit_system=0,
                    flag_approved=1,
                    flag_deleted=0,
                    flag_banned=0,
                    tracking_cookie='foocookie',
                )
                db_nick = models.DBUserNickname(
                    nick_id=1,
                    nickname='foouser',
                    user_id=1,
                    user_seq=1,
                    flag_valid=1,
                    role=0,
                    policy=0,
                    flag_primary=1
                )
                db_demo = models.DBProfile(
                    user_id=1,
                    country='US',
                    affiliation='Cornell U.',
                    url='http://example.com/bogus',
                    rank=2,
                    original_subject_classes='cs.OH',
                    )
                salt = b'fdoo'
                password = b'thepassword'
                hashed = hashlib.sha1(salt + b'-' + password).digest()
                encrypted = b64encode(salt + hashed)
                db_password = models.DBUserPassword(
                    user_id=1,
                    password_storage=2,
                    password_enc=encrypted
                )
                session.add(db_user)
                session.add(db_password)
                session.add(db_nick)
                session.add(db_demo)

    def tearDown(self):
        with self.app.app_context():
            util.drop_all()
        try:
            os.remove(self.db)
        except FileNotFoundError:
            pass


    def test_post_no_data(self):
        """POST request with no data."""
        params = MultiDict({})
        data, code, headers = register('POST', params, '', '10.10.10.10',
                                       '/foo')
        self.assertEqual(code, status.HTTP_400_BAD_REQUEST,
                         "Returns 400 response")

    @mock.patch('accounts.controllers.registration.accounts')
    @mock.patch('accounts.controllers.registration.stateless_captcha.check')
    def test_post_minimum(self, captcha, users):
        """POST request with minimum required data."""
        captcha.return_value = None     # No exception -> OK.
        users.does_username_exist.return_value = False
        users.does_email_exist.return_value = False
        users.register.return_value = (mock.MagicMock(), mock.MagicMock())

        registration_data = {
            'email': 'foo@bar.edu',
            'username': 'foouser',
            'password': 'fdsafdsa',
            'password2': 'fdsafdsa',
            'forename': 'Bob',
            'surname': 'Bob',
            'affiliation': 'Bob Co.',
            'country': 'RU',
            'status': '1',
            'default_category': 'astro-ph.CO',
            'captcha_value': 'asdf1234'
        }
        params = MultiDict(registration_data)

        with self.app.app_context():
            data, code, headers = register('POST', params, '', '10.10.10.10',
                                       '/foo')
        self.assertEqual(code, status.HTTP_201_CREATED, "Returns 201 response")

        args, kwargs = users.register.call_args
        user, password, ip, host = args
        self.assertIsNone(user.user_id)
        self.assertEqual(user.username, registration_data['username'])
        self.assertEqual(user.email, registration_data['email'])
        self.assertEqual(password, registration_data['password'])
        self.assertEqual(user.name.forename,
                         registration_data['forename'])
        self.assertEqual(user.name.surname,
                         registration_data['surname'])

        self.assertEqual(user.profile.affiliation,
                         registration_data['affiliation'])
        self.assertEqual(user.profile.country,
                         registration_data['country'])
        self.assertEqual(user.profile.rank,
                         int(registration_data['status']))
        self.assertEqual(user.profile.default_category.archive,
                         'astro-ph')
        self.assertEqual(user.profile.default_category.subject, 'CO')

    @mock.patch('accounts.controllers.registration.accounts')
    def test_missing_data(self, users):
        """POST request missing a required field."""
        users.does_username_exist.return_value = False
        users.does_email_exist.return_value = False

        registration_data = {
            'email': 'foo@bar.edu',
            'username': 'foouser',
            'password': 'fdsafdsa',
            'password2': 'fdsafdsa',
            'forename': 'Bob',
            'surname': 'Bob',
            'affiliation': 'Bob Co.',
            'country': 'RU',
            'status': '1',
            'default_category': 'astro-ph.CO',
            'captcha_value': 'asdf1234'
        }
        for key in registration_data.keys():
            to_post = dict(registration_data)
            to_post.pop(key)    # Drop this one.
            params = MultiDict(to_post)
            with self.app.app_context():
                data, code, headers = register('POST', params, '', '10.10.10.10',
                                               '/foo')
            self.assertEqual(code, status.HTTP_400_BAD_REQUEST,
                             "Returns 400 response")

    @mock.patch('accounts.controllers.registration.accounts')
    def test_password_mismatch(self, users):
        """POST with all required data, but passwords don't match."""
        users.does_username_exist.return_value = False
        users.does_email_exist.return_value = False
        registration_data = {
            'email': 'foo@bar.edu',
            'username': 'foouser',
            'password': 'fdsafdsa',
            'password2': 'notthesamepassword',
            'forename': 'Bob',
            'surname': 'Bob',
            'affiliation': 'Bob Co.',
            'country': 'RU',
            'status': '1',
            'default_category': 'astro-ph.CO',
            'captcha_value': 'asdf1234'
        }
        params = MultiDict(registration_data)
        with self.app.app_context():
            data, code, headers = register('POST', params, '', '10.10.10.10',
                                       '/foo')
        self.assertEqual(code, status.HTTP_400_BAD_REQUEST,
                         "Returns 400 response")

    @mock.patch('accounts.controllers.registration.accounts')
    @mock.patch('accounts.controllers.registration.stateless_captcha.check')
    def test_existing_username(self, captcha, users):
        """POST valid data, but username already exists."""
        captcha.return_value = None     # No exception -> OK.
        users.does_username_exist.return_value = True
        users.does_email_exist.return_value = False
        users.register.return_value = (mock.MagicMock(), mock.MagicMock())

        registration_data = {
            'email': 'foo@bar.edu',
            'username': 'foouser',
            'password': 'fdsafdsa',
            'password2': 'fdsafdsa',
            'forename': 'Bob',
            'surname': 'Bob',
            'affiliation': 'Bob Co.',
            'country': 'RU',
            'status': '1',
            'default_category': 'astro-ph.CO',
            'captcha_value': 'asdf1234'
        }
        params = MultiDict(registration_data)

        with self.app.app_context():
            data, code, headers = register('POST', params, '', '10.10.10.10',
                                       '/foo')
        self.assertEqual(code, status.HTTP_400_BAD_REQUEST,
                         "Returns 400 response")

    @mock.patch('accounts.controllers.registration.accounts')
    @mock.patch('accounts.controllers.registration.stateless_captcha.check')
    @unittest.skip("not in use and not ready to use")
    def test_existing_email(self, captcha, users):
        """POST valid data, but email already exists."""
        captcha.return_value = None     # No exception -> OK.
        users.does_username_exist.return_value = False
        users.does_email_exist.return_value = True
        users.register.return_value = (mock.MagicMock(), mock.MagicMock())

        registration_data = {
            'email': 'foo@bar.edu',
            'username': 'foouser',
            'password': 'fdsafdsa',
            'password2': 'fdsafdsa',
            'forename': 'Bob',
            'surname': 'Bob',
            'affiliation': 'Bob Co.',
            'country': 'RU',
            'status': '1',
            'default_category': 'astro-ph.CO',
            'captcha_value': 'asdf1234'
        }
        params = MultiDict(registration_data)
        with self.app.app_context():
            data, code, headers = register('POST', params, '', '10.10.10.10',
                                           '/foo')
            self.assertEqual(code, status.HTTP_400_BAD_REQUEST,
                             "Returns 400 response")

    @mock.patch('accounts.controllers.registration.accounts')
    @mock.patch('accounts.controllers.registration.stateless_captcha.check')
    @unittest.skip("not in use and not ready to use")
    def test_captcha_mismatch(self, captcha, users):
        """POST valid data, but captcha value is incorrect."""
        def raise_invalid_value(*args, **kwargs):
            raise InvalidCaptchaValue('Nope')

        captcha.side_effect = raise_invalid_value
        users.does_username_exist.return_value = False
        users.does_email_exist.return_value = False
        users.register.return_value = (mock.MagicMock(), mock.MagicMock())

        registration_data = {
            'email': 'foo@bar.edu',
            'username': 'foouser',
            'password': 'fdsafdsa',
            'password2': 'fdsafdsa',
            'forename': 'Bob',
            'surname': 'Bob',
            'affiliation': 'Bob Co.',
            'country': 'RU',
            'status': '1',
            'default_category': 'astro-ph.CO',
            'captcha_value': 'asdf1234'
        }
        params = MultiDict(registration_data)

        with self.app.app_context():
            data, code, headers = register('POST', params, '', '10.10.10.10',
                                       '/foo')
        self.assertEqual(code, status.HTTP_400_BAD_REQUEST,
                         "Returns 400 response")

    @mock.patch('accounts.controllers.registration.accounts')
    @mock.patch('accounts.controllers.registration.stateless_captcha.check')
    def test_captcha_expired(self, captcha, users):
        """POST valid data, but captcha token has expired."""
        def raise_invalid_token(*args, **kwargs):
            raise InvalidCaptchaToken('Nope')

        captcha.side_effect = raise_invalid_token
        users.does_username_exist.return_value = False
        users.does_email_exist.return_value = False
        users.register.return_value = (mock.MagicMock(), mock.MagicMock())

        registration_data = {
            'email': 'foo@bar.edu',
            'username': 'foouser',
            'password': 'fdsafdsa',
            'password2': 'fdsafdsa',
            'forename': 'Bob',
            'surname': 'Bob',
            'affiliation': 'Bob Co.',
            'country': 'RU',
            'status': '1',
            'default_category': 'astro-ph.CO',
            'captcha_value': 'asdf1234'
        }
        params = MultiDict(registration_data)

        with self.app.app_context():
            data, code, headers = register('POST', params, '', '10.10.10.10',
                                           '/foo')
        self.assertEqual(code, status.HTTP_400_BAD_REQUEST,
                         "Returns 400 response")


    def test_post_no_data(self):
        """POST request with no data."""
        current_session = mock.MagicMock(session_id='52')

        params = MultiDict({})
        with self.app.app_context():
            data, code, headers = edit_profile('POST', 1, current_session, params,
                                           '10.10.10.10')
        self.assertEqual(code, status.HTTP_400_BAD_REQUEST,
                         "Returns 400 response")

    @mock.patch('accounts.controllers.registration.sessions.invalidate_by_id')
    @mock.patch('accounts.controllers.registration.accounts')
    @unittest.skip("not in use and not ready to use")
    def test_post_minimum(self, users, create, invalidate):
        """POST request with minimum required data."""
        users.get_user_by_id.return_value = mock.MagicMock(user_id=1)
        users.does_username_exist.return_value = False
        users.does_email_exist.return_value = False
        users.update.return_value = (mock.MagicMock(), mock.MagicMock())
        current_session = mock.MagicMock(session_id='52')

        profile_data = {
            'user_id': 1,
            'email': 'foo@bar.edu',
            'username': 'foouser',
            'forename': 'Bob',
            'surname': 'Bob',
            'affiliation': 'Bob Co.',
            'country': 'RU',
            'status': '1',
            'default_category': 'astro-ph.CO',
        }
        params = MultiDict(profile_data)

        with self.app.app_context():
            data, code, headers = edit_profile('POST', 1, current_session,
                                           params, '10.10.10.10')
        self.assertEqual(code, status.HTTP_303_SEE_OTHER,
                         "Returns 303 redirect")

        args, kwargs = users.update.call_args
        user = args[0]
        self.assertEqual(user.username, profile_data['username'])
        self.assertEqual(user.email, profile_data['email'])
        self.assertEqual(user.name.forename,
                         profile_data['forename'])
        self.assertEqual(user.name.surname,
                         profile_data['surname'])

        self.assertEqual(user.profile.affiliation,
                         profile_data['affiliation'])
        self.assertEqual(user.profile.country,
                         profile_data['country'])
        self.assertEqual(user.profile.rank,
                         int(profile_data['status']))
        self.assertEqual(user.profile.default_category.archive,
                         'astro-ph')
        self.assertEqual(user.profile.default_category.subject, 'CO')

    @mock.patch('accounts.controllers.registration.accounts')
    @unittest.skip("not in use and not ready to use")
    def test_missing_data(self, users):
        """POST request missing a required field."""
        users.get_user_by_id.return_value = mock.MagicMock(user_id=1)
        current_session = mock.MagicMock(session_id='52')

        profile_data = {
            'user_id': 1,
            'email': 'foo@bar.edu',
            'username': 'foouser',
            'forename': 'Bob',
            'surname': 'Bob',
            'affiliation': 'Bob Co.',
            'country': 'RU',
            'status': '1',
            'default_category': 'astro-ph.CO',
        }
        for key in profile_data.keys():
            to_post = dict(profile_data)
            to_post.pop(key)    # Drop this one.
            params = MultiDict(to_post)
            with self.app.app_context():
                data, code, headers = edit_profile('POST', 1, current_session,
                                                   params, '10.10.10.10')
            self.assertEqual(code, status.HTTP_400_BAD_REQUEST,
                             "Returns 400 response")

    @mock.patch('accounts.controllers.registration.accounts')
    @unittest.skip("not in use and not ready to use")
    def test_existing_username(self, users):
        """POST valid data, but username already exists."""
        users.get_user_by_id.return_value = mock.MagicMock(user_id=1)
        users.does_username_exist.return_value = True
        users.does_email_exist.return_value = False
        users.update.return_value = (mock.MagicMock(), mock.MagicMock())
        current_session = mock.MagicMock(session_id='52')

        profile_data = {
            'user_id': 1,
            'email': 'foo@bar.edu',
            'username': 'foouser',
            'forename': 'Bob',
            'surname': 'Bob',
            'affiliation': 'Bob Co.',
            'country': 'RU',
            'status': '1',
            'default_category': 'astro-ph.CO',
        }
        params = MultiDict(profile_data)

        with self.app.app_context():
            data, code, headers = edit_profile('POST', 1, current_session, params,
                                               '10.10.10.10')
        self.assertEqual(code, status.HTTP_400_BAD_REQUEST,
                         "Returns 400 response")

    @mock.patch('accounts.controllers.registration.accounts')
    @unittest.skip("not in use and not ready to use")
    def test_existing_email(self, users):
        """POST valid data, but email already exists."""
        users.get_user_by_id.return_value = mock.MagicMock(user_id=1)
        users.does_username_exist.return_value = False
        users.does_email_exist.return_value = True
        users.update.return_value = (mock.MagicMock(), mock.MagicMock())
        current_session = mock.MagicMock(session_id='52')

        profile_data = {
            'user_id': 1,
            'email': 'foo@bar.edu',
            'username': 'foouser',
            'forename': 'Bob',
            'surname': 'Bob',
            'affiliation': 'Bob Co.',
            'country': 'RU',
            'status': '1',
            'default_category': 'astro-ph.CO'
        }
        params = MultiDict(profile_data)

        with self.app.app_context():
            data, code, headers = edit_profile('POST', 1, current_session,
                                           params, '10.10.10.10')
        self.assertEqual(code, status.HTTP_400_BAD_REQUEST,
                         "Returns 400 response")
