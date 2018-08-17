"""Tests for :mod:`accounts.controllers.registration`."""

from unittest import TestCase, mock
from werkzeug import MultiDict
from arxiv import status
from ..registration import register, edit_profile, view_profile
from ...stateless_captcha import InvalidCaptchaValue, InvalidCaptchaToken


class TestRegister(TestCase):
    """Tests for :func:`register`."""

    def test_post_no_data(self):
        """POST request with no data."""
        params = MultiDict({})
        data, code, headers = register('POST', params, '', '10.10.10.10',
                                       '/foo')
        self.assertEqual(code, status.HTTP_400_BAD_REQUEST,
                         "Returns 400 response")

    @mock.patch('accounts.controllers.registration.users')
    @mock.patch('accounts.controllers.registration.legacy')
    @mock.patch('accounts.controllers.registration.sessions')
    @mock.patch('accounts.controllers.registration.stateless_captcha.check')
    def test_post_minimum(self, captcha, sessions, legacy, users):
        """POST request with minimum required data."""
        captcha.return_value = None     # No exception -> OK.
        users.username_exists.return_value = False
        users.email_exists.return_value = False
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

    @mock.patch('accounts.controllers.registration.users')
    def test_missing_data(self, users):
        """POST request missing a required field."""
        users.username_exists.return_value = False
        users.email_exists.return_value = False

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
            data, code, headers = register('POST', params, '', '10.10.10.10',
                                           '/foo')
            self.assertEqual(code, status.HTTP_400_BAD_REQUEST,
                             "Returns 400 response")

    @mock.patch('accounts.controllers.registration.users')
    def test_password_mismatch(self, users):
        """POST with all required data, but passwords don't match."""
        users.username_exists.return_value = False
        users.email_exists.return_value = False
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
        data, code, headers = register('POST', params, '', '10.10.10.10',
                                       '/foo')
        self.assertEqual(code, status.HTTP_400_BAD_REQUEST,
                         "Returns 400 response")

    @mock.patch('accounts.controllers.registration.users')
    @mock.patch('accounts.controllers.registration.legacy')
    @mock.patch('accounts.controllers.registration.sessions')
    @mock.patch('accounts.controllers.registration.stateless_captcha.check')
    def test_existing_username(self, captcha, sessions, legacy, users):
        """POST valid data, but username already exists."""
        captcha.return_value = None     # No exception -> OK.
        users.username_exists.return_value = True
        users.email_exists.return_value = False
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

        data, code, headers = register('POST', params, '', '10.10.10.10',
                                       '/foo')
        self.assertEqual(code, status.HTTP_400_BAD_REQUEST,
                         "Returns 400 response")

    @mock.patch('accounts.controllers.registration.users')
    @mock.patch('accounts.controllers.registration.legacy')
    @mock.patch('accounts.controllers.registration.sessions')
    @mock.patch('accounts.controllers.registration.stateless_captcha.check')
    def test_existing_email(self, captcha, sessions, legacy, users):
        """POST valid data, but email already exists."""
        captcha.return_value = None     # No exception -> OK.
        users.username_exists.return_value = False
        users.email_exists.return_value = True
        users.register.return_value = (mock.MagicMock(), mock.MagicMock())
        legacy.return_value = (mock.MagicMock(), mock.MagicMock())
        sessions.return_value = (mock.MagicMock(), mock.MagicMock())

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

        data, code, headers = register('POST', params, '', '10.10.10.10',
                                       '/foo')
        self.assertEqual(code, status.HTTP_400_BAD_REQUEST,
                         "Returns 400 response")

    @mock.patch('accounts.controllers.registration.users')
    @mock.patch('accounts.controllers.registration.legacy')
    @mock.patch('accounts.controllers.registration.sessions')
    @mock.patch('accounts.controllers.registration.stateless_captcha.check')
    def test_captcha_mismatch(self, captcha, sessions, legacy, users):
        """POST valid data, but captcha value is incorrect."""
        def raise_invalid_value(*args, **kwargs):
            raise InvalidCaptchaValue('Nope')

        captcha.side_effect = raise_invalid_value
        users.username_exists.return_value = False
        users.email_exists.return_value = False
        users.register.return_value = (mock.MagicMock(), mock.MagicMock())
        legacy.return_value = (mock.MagicMock(), mock.MagicMock())
        sessions.return_value = (mock.MagicMock(), mock.MagicMock())

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

        data, code, headers = register('POST', params, '', '10.10.10.10',
                                       '/foo')
        self.assertEqual(code, status.HTTP_400_BAD_REQUEST,
                         "Returns 400 response")

    @mock.patch('accounts.controllers.registration.users')
    @mock.patch('accounts.controllers.registration.legacy')
    @mock.patch('accounts.controllers.registration.sessions')
    @mock.patch('accounts.controllers.registration.stateless_captcha.check')
    def test_captcha_expired(self, captcha, sessions, legacy, users):
        """POST valid data, but captcha token has expired."""
        def raise_invalid_token(*args, **kwargs):
            raise InvalidCaptchaToken('Nope')

        captcha.side_effect = raise_invalid_token
        users.username_exists.return_value = False
        users.email_exists.return_value = False
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

        data, code, headers = register('POST', params, '', '10.10.10.10',
                                       '/foo')
        self.assertEqual(code, status.HTTP_400_BAD_REQUEST,
                         "Returns 400 response")


class TestEditProfile(TestCase):
    """Tests for :func:`edit_profile`."""

    def test_post_no_data(self):
        """POST request with no data."""
        current_session = mock.MagicMock(session_id='52')

        params = MultiDict({})
        data, code, headers = edit_profile('POST', 1, current_session, params,
                                           '10.10.10.10')
        self.assertEqual(code, status.HTTP_400_BAD_REQUEST,
                         "Returns 400 response")

    @mock.patch('accounts.controllers.registration.sessions.invalidate_by_id')
    @mock.patch('accounts.controllers.registration.sessions')
    @mock.patch('accounts.controllers.registration.users')
    def test_post_minimum(self, users, create, invalidate):
        """POST request with minimum required data."""
        users.get_user_by_id.return_value = mock.MagicMock(user_id=1)
        users.username_exists.return_value = False
        users.email_exists.return_value = False
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

    @mock.patch('accounts.controllers.registration.users')
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
            data, code, headers = edit_profile('POST', 1, current_session,
                                               params, '10.10.10.10')
            self.assertEqual(code, status.HTTP_400_BAD_REQUEST,
                             "Returns 400 response")

    @mock.patch('accounts.controllers.registration.users')
    def test_existing_username(self, users):
        """POST valid data, but username already exists."""
        users.get_user_by_id.return_value = mock.MagicMock(user_id=1)
        users.username_exists.return_value = True
        users.email_exists.return_value = False
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

        data, code, headers = edit_profile('POST', 1, current_session, params,
                                           '10.10.10.10')
        self.assertEqual(code, status.HTTP_400_BAD_REQUEST,
                         "Returns 400 response")

    @mock.patch('accounts.controllers.registration.users')
    def test_existing_email(self, users):
        """POST valid data, but email already exists."""
        users.get_user_by_id.return_value = mock.MagicMock(user_id=1)
        users.username_exists.return_value = False
        users.email_exists.return_value = True
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

        data, code, headers = edit_profile('POST', 1, current_session,
                                           params, '10.10.10.10')
        self.assertEqual(code, status.HTTP_400_BAD_REQUEST,
                         "Returns 400 response")
