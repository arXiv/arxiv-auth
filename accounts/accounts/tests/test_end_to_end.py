"""End-to-end tests, via requests to the user interface."""

from unittest import TestCase, mock
from datetime import datetime
from pytz import timezone, UTC, UTC
from dateutil.parser import parse
import os
import subprocess
import time
import hashlib
from base64 import b64encode

from arxiv import status
from accounts.services import legacy, users
from accounts.factory import create_web_app

from accounts import stateless_captcha

EASTERN = timezone('US/Eastern')


def _parse_cookies(cookie_data):
    cookies = {}
    for cdata in cookie_data:
        parts = cdata.split('; ')
        data = parts[0]
        key, value = data[:data.index('=')], data[data.index('=') + 1:]
        extra = {
            part[:part.index('=')]: part[part.index('=') + 1:]
            for part in parts[1:] if '=' in part
        }
        cookies[key] = dict(value=value, **extra)
    return cookies


def stop_container(container):
    subprocess.run(f"docker rm -f {container}",
                   stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                   shell=True)
    from accounts.services import legacy, users


# 2018-07-30 : Disabling everything except login and logout routes for accounts
#  v0.1. - Erick

# class TestRegistration(TestCase):
#     """Test registering new users."""
#
#     __test__ = int(bool(os.environ.get('WITH_INTEGRATION', False)))
#
#     def setUp(self):
#         """Spin up redis."""
#         self.redis = subprocess.run(
#             "docker run -d -p 7000:7000 redis",
#             stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
#         )
#         time.sleep(5)    # In case it takes a moment to start.
#         if self.redis.returncode > 0:
#             raise RuntimeError('Could not start redis. Is Docker running?')
#
#         self.container = self.redis.stdout.decode('ascii').strip()
#         self.secret = 'bazsecret'
#         self.db = 'db.sqlite'
#         self.captcha_secret = 'foocaptcha'
#         self.ip_address = '10.10.10.10'
#         self.environ_base = {'REMOTE_ADDR': self.ip_address}
#         try:
#             self.app = create_web_app()
#             self.app.config['CLASSIC_COOKIE_NAME'] = 'foo_tapir_session'
#             self.app.config['AUTH_SESSION_COOKIE_NAME'] = 'baz_session'
#             self.app.config['CAPTCHA_SECRET'] = self.captcha_secret
#             self.app.config['JWT_SECRET'] = self.secret
#             self.app.config['CLASSIC_DATABASE_URI'] = f'sqlite:///{self.db}'
#             client = self.app.test_client()
#             with self.app.app_context():
#                 from accounts.services import legacy, users
#                 legacy.create_all()
#                 users.create_all()
#         except Exception as e:
#             stop_container(self.container)
#             raise
#
#     def tearDown(self):
#         """Tear down redis."""
#         stop_container(self.container)
#         os.remove(self.db)
#
#     def test_get_registration_form(self):
#         """GET request for the registration form."""
#         response = client.get('/register')
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#         self.assertEqual(response.content_type, 'text/html; charset=utf-8')
#
#     def test_post_minimum(self):
#         """POST request with minimum required data."""
#         captcha_token = stateless_captcha.new(self.captcha_secret,
#                                               self.ip_address)
#         captcha_value = stateless_captcha.unpack(captcha_token,
#                                                  self.captcha_secret,
#                                                  self.ip_address)
#         registration_data = {
#             'email': 'foo@bar.edu',
#             'username': 'foouser',
#             'password': 'fdsafdsa',
#             'password2': 'fdsafdsa',
#             'forename': 'Bob',
#             'surname': 'Bob',
#             'affiliation': 'Bob Co.',
#             'country': 'RU',
#             'status': '1',
#             'default_category': 'astro-ph.CO',
#             'captcha_value': captcha_value,
#             'captcha_token': captcha_token
#         }
#         response = client.post('/register', data=registration_data,
#                                     environ_base=self.environ_base)
#         self.assertEqual(response.status_code, status.HTTP_201_CREATED)
#         self.assertTrue(
#             response.headers['Location'].endswith('/1/profile')
#         )
#         cookies = _parse_cookies(response.headers.getlist('Set-Cookie'))
#
#         self.assertIn(self.app.config['AUTH_SESSION_COOKIE_NAME'], cookies,
#                       "Sets cookie for authn session.")
#         self.assertIn(self.app.config['CLASSIC_COOKIE_NAME'], cookies,
#                       "Sets cookie for classic sessions.")
#
#     def test_cannot_create_twice(self):
#         """After a registration is successful, user cannot access form."""
#         # Create the first user.
#         captcha_token = stateless_captcha.new(self.captcha_secret,
#                                               self.ip_address)
#         captcha_value = stateless_captcha.unpack(captcha_token,
#                                                  self.captcha_secret,
#                                                  self.ip_address)
#         registration_data = {
#             'email': 'foo@bar.edu',
#             'username': 'foouser',
#             'password': 'fdsafdsa',
#             'password2': 'fdsafdsa',
#             'forename': 'Bob',
#             'surname': 'Bob',
#             'affiliation': 'Bob Co.',
#             'country': 'RU',
#             'status': '1',
#             'default_category': 'astro-ph.CO',
#             'captcha_value': captcha_value,
#             'captcha_token': captcha_token
#         }
#         response = client.post('/register', data=registration_data,
#                                     environ_base=self.environ_base)
#
#         # We have to set the cookies manually here.
#         cookies = _parse_cookies(response.headers.getlist('Set-Cookie'))
#         client.set_cookie(
#             'localhost',
#             self.app.config['AUTH_SESSION_COOKIE_NAME'],
#             cookies[self.app.config['AUTH_SESSION_COOKIE_NAME']]['value']
#         )
#         client.set_cookie(
#             'localhost',
#             self.app.config['CLASSIC_COOKIE_NAME'],
#             cookies[self.app.config['CLASSIC_COOKIE_NAME']]['value']
#         )
#
#         # Attempting to access the registration form results in a redirect.
#         response = client.post('/register', data=registration_data,
#                                     environ_base=self.environ_base)
#         self.assertEqual(response.status_code, status.HTTP_303_SEE_OTHER)
#         response = client.get('/register',
#                                    environ_base=self.environ_base)
#         self.assertEqual(response.status_code, status.HTTP_303_SEE_OTHER)
#
#         # Clear session cookies. The user is no longer using an authenticated
#         # session.
#         client.set_cookie('localhost',
#                                self.app.config['AUTH_SESSION_COOKIE_NAME'], '')
#         client.set_cookie('localhost',
#                                self.app.config['CLASSIC_COOKIE_NAME'], '')
#
#         response = client.get('/register',
#                                    environ_base=self.environ_base)
#         self.assertEqual(response.status_code, status.HTTP_200_OK)
#
#     def test_existing_username_email(self):
#         """Valid data, but username or email already exists."""
#         # Create the first user.
#         captcha_token = stateless_captcha.new(self.captcha_secret,
#                                               self.ip_address)
#         captcha_value = stateless_captcha.unpack(captcha_token,
#                                                  self.captcha_secret,
#                                                  self.ip_address)
#         registration_data = {
#             'email': 'foo@bar.edu',
#             'username': 'foouser',
#             'password': 'fdsafdsa',
#             'password2': 'fdsafdsa',
#             'forename': 'Bob',
#             'surname': 'Bob',
#             'affiliation': 'Bob Co.',
#             'country': 'RU',
#             'status': '1',
#             'default_category': 'astro-ph.CO',
#             'captcha_value': captcha_value,
#             'captcha_token': captcha_token
#         }
#         client.post('/register', data=registration_data,
#                          environ_base=self.environ_base)
#         # Clear session cookies.
#         client.set_cookie('localhost',
#                                self.app.config['AUTH_SESSION_COOKIE_NAME'], '')
#         client.set_cookie('localhost',
#                                self.app.config['CLASSIC_COOKIE_NAME'], '')
#
#         # Now we attempt to register the same user.
#         captcha_token = stateless_captcha.new(self.captcha_secret,
#                                               self.ip_address)
#         captcha_value = stateless_captcha.unpack(captcha_token,
#                                                  self.captcha_secret,
#                                                  self.ip_address)
#         registration_data = {
#             'email': 'other@bar.edu',
#             'username': 'foouser',    # <- Same username!
#             'password': 'fdsafdsa',
#             'password2': 'fdsafdsa',
#             'forename': 'Bob',
#             'surname': 'Bob',
#             'affiliation': 'Bob Co.',
#             'country': 'RU',
#             'status': '1',
#             'default_category': 'astro-ph.CO',
#             'captcha_value': captcha_value,
#             'captcha_token': captcha_token
#         }
#         response = client.post('/register', data=registration_data,
#                                     environ_base=self.environ_base)
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
#                          "Returns 400 response")
#
#         # Clear session cookies.
#         client.set_cookie('localhost',
#                                self.app.config['AUTH_SESSION_COOKIE_NAME'], '')
#         client.set_cookie('localhost',
#                                self.app.config['CLASSIC_COOKIE_NAME'], '')
#
#         registration_data = {
#             'email': 'foo@bar.edu',    # <- same email!
#             'username': 'otheruser',
#             'password': 'fdsafdsa',
#             'password2': 'fdsafdsa',
#             'forename': 'Bob',
#             'surname': 'Bob',
#             'affiliation': 'Bob Co.',
#             'country': 'RU',
#             'status': '1',
#             'default_category': 'astro-ph.CO',
#             'captcha_value': captcha_value,
#             'captcha_token': captcha_token
#         }
#         response = client.post('/register', data=registration_data,
#                                     environ_base=self.environ_base)
#         self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
#                          "Returns 400 response")
#
#     def test_missing_data(self):
#         """POST request missing a required field."""
#         captcha_token = stateless_captcha.new(self.captcha_secret,
#                                               self.ip_address)
#         captcha_value = stateless_captcha.unpack(captcha_token,
#                                                  self.captcha_secret,
#                                                  self.ip_address)
#
#         registration_data = {
#             'email': 'foo@bar.edu',
#             'username': 'foouser',
#             'password': 'fdsafdsa',
#             'password2': 'fdsafdsa',
#             'forename': 'Bob',
#             'surname': 'Bob',
#             'affiliation': 'Bob Co.',
#             'country': 'RU',
#             'status': '1',
#             'default_category': 'astro-ph.CO',
#             'captcha_value': captcha_value,
#             'captcha_token': captcha_token
#         }
#         for key in registration_data.keys():
#             to_post = dict(registration_data)
#             to_post.pop(key)    # Drop this one.
#             response = client.post('/register', data=to_post,
#                                         environ_base=self.environ_base)
#
#             self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST,
#                              "Returns 400 response")


class TestLoginLogoutRoutes(TestCase):
    """Test logging in and logging out."""

    __test__ = int(bool(os.environ.get('WITH_INTEGRATION', False)))

    @classmethod
    def setUpClass(self):
        """Spin up redis."""
        self.redis = subprocess.run(
            "docker run -d -p 7000:7000 -p 7001:7001 -p 7002:7002 -p 7003:7003"
            " -p 7004:7004 -p 7005:7005 -p 7006:7006 -e \"IP=0.0.0.0\""
            " --hostname=server grokzen/redis-cluster:4.0.9",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        time.sleep(15)    # In case it takes a moment to start.
        if self.redis.returncode > 0:
            raise RuntimeError('Could not start redis. Is Docker running?')

        self.container = self.redis.stdout.decode('ascii').strip()
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
        self.app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{self.db}'
        self.app.config['REDIS_HOST'] = 'localhost'
        self.app.config['REDIS_PORT'] = '7000'
        self.app.config['REDIS_CLUSTER'] = '1'

        with self.app.app_context():
            legacy.drop_all()
            users.drop_all()
            legacy.create_all()
            users.create_all()

            with users.transaction() as session:
                # We have a good old-fashioned user.
                db_user = users.models.DBUser(
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
                db_nick = users.models.DBUserNickname(
                    nick_id=1,
                    nickname='foouser',
                    user_id=1,
                    user_seq=1,
                    flag_valid=1,
                    role=0,
                    policy=0,
                    flag_primary=1
                )
                salt = b'fdoo'
                password = b'thepassword'
                hashed = hashlib.sha1(salt + b'-' + password).digest()
                encrypted = b64encode(salt + hashed)
                db_password = users.models.DBUserPassword(
                    user_id=1,
                    password_storage=2,
                    password_enc=encrypted
                )
                session.add(db_user)
                session.add(db_password)
                session.add(db_nick)

    @classmethod
    def tearDownClass(cls):
        """Tear down redis and the test DB."""
        stop_container(cls.container)

    def tearDown(self):
        with self.app.app_context():
            legacy.drop_all()
            users.drop_all()
        try:
            os.remove(self.db)
        except FileNotFoundError:
            pass

    def test_get_login(self):
        """GET request to /login returns the login form."""
        client = self.app.test_client()
        response = client.get('/login')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content_type, 'text/html; charset=utf-8')

    def test_post_login(self):
        """POST request to /login with valid form data returns redirect."""
        client = self.app.test_client()
        client.environ_base = self.environ_base
        form_data = {'username': 'foouser', 'password': 'thepassword'}
        next_page = '/foo'
        response = client.post(f'/login?next_page={next_page}', data=form_data)
        self.assertEqual(response.status_code, status.HTTP_303_SEE_OTHER)
        self.assertTrue(response.headers['Location'].endswith(next_page),
                        "Redirect should point at value of `next_page` param")
        cookies = _parse_cookies(response.headers.getlist('Set-Cookie'))

        cookie_name = self.app.config['AUTH_SESSION_COOKIE_NAME']
        self.assertIn(cookie_name, cookies, "Sets cookie for authn session.")

        classic_cookie_name = self.app.config['CLASSIC_COOKIE_NAME']
        self.assertIn(classic_cookie_name, cookies, "Sets classic cookie")

        cookie = cookies[cookie_name]
        classic_cookie = cookies[classic_cookie_name]

        # Verify that the domain is correct.
        self.assertEqual(cookie['Domain'], '.arxiv.org', 'Domain is set')
        self.assertEqual(classic_cookie['Domain'], '.arxiv.org',
                         'Domain is set')

        # Verify that the correct expiry is set.
        self.assertEqual(int(cookie['Max-Age']), self.expiry - 1)
        self.assertEqual(int(classic_cookie['Max-Age']), self.expiry - 1)

        expires_in = (parse(cookie['Expires']) - datetime.now(UTC)).seconds
        classic_expires_in = (parse(classic_cookie['Expires'])
                              - datetime.now(UTC)).seconds
        self.assertLess(expires_in - self.expiry, 2)
        self.assertLess(classic_expires_in - self.expiry, 2)

        # Verify that the expiry is not set in the database. This is kind of
        # a weird "feature" of the classic auth system.
        with self.app.app_context():
            with legacy.transaction() as session:
                db_session = session.query(legacy.models.DBSession) \
                    .filter(legacy.models.DBSession.user_id == 1) \
                    .order_by(legacy.models.DBSession.session_id.desc()) \
                    .first()
                self.assertEqual(db_session.end_time, 0)

    def test_post_login_baddata(self):
        """POST rquest to /login with invalid data returns 400."""
        form_data = {'username': 'foouser', 'password': 'notthepassword'}
        client = self.app.test_client()
        response = client.post('/login', data=form_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_logout(self):
        """User logs in and then logs out."""
        client = self.app.test_client()
        client.environ_base = self.environ_base
        form_data = {'username': 'foouser', 'password': 'thepassword'}

        # Werkzeug should keep the cookies around for the next request.
        response = client.post('/login', data=form_data)
        cookies = _parse_cookies(response.headers.getlist('Set-Cookie'))

        cookie_name = self.app.config['AUTH_SESSION_COOKIE_NAME']
        self.assertIn(cookie_name, cookies, "Sets cookie for authn session.")

        classic_cookie_name = self.app.config['CLASSIC_COOKIE_NAME']
        self.assertIn(classic_cookie_name, cookies, "Sets classic cookie")

        cookie = cookies[cookie_name]
        classic_cookie = cookies[classic_cookie_name]

        # Verify that the domain is correct.
        self.assertEqual(cookie['Domain'], '.arxiv.org', 'Domain is set')
        self.assertEqual(classic_cookie['Domain'], '.arxiv.org',
                         'Domain is set')

        # Verify that the correct expiry is set.
        self.assertEqual(int(cookie['Max-Age']), self.expiry - 1)
        self.assertEqual(int(classic_cookie['Max-Age']), self.expiry - 1)

        expires_in = (parse(cookie['Expires']) - datetime.now(UTC)).seconds
        classic_expires_in = (parse(classic_cookie['Expires'])
                              - datetime.now(UTC)).seconds
        self.assertLess(expires_in - self.expiry, 2)
        self.assertLess(classic_expires_in - self.expiry, 2)

        # Verify that the expiry is not set in the database. This is kind of
        # a weird "feature" of the classic auth system.
        with self.app.app_context():
            with legacy.transaction() as session:
                db_session = session.query(legacy.models.DBSession) \
                    .filter(legacy.models.DBSession.user_id == 1) \
                    .order_by(legacy.models.DBSession.session_id.desc()) \
                    .first()
                self.assertEqual(db_session.end_time, 0)

        response = client.get('/logout')
        logout_cookies = _parse_cookies(response.headers.getlist('Set-Cookie'))

        cookie = logout_cookies[cookie_name]
        classic_cookie = logout_cookies[classic_cookie_name]

        self.assertEqual(cookie['value'], '', 'Session cookie is unset')
        self.assertEqual(cookie['Max-Age'], '0', 'Session cookie is expired')
        self.assertLessEqual(parse(cookie['Expires']), datetime.now(UTC),
                             "Session cookie is expired")
        self.assertEqual(cookie['Domain'], '.arxiv.org', 'Domain is set')

        self.assertEqual(classic_cookie['value'], '',
                         'Classic cookie is unset')
        self.assertEqual(classic_cookie['Max-Age'], '0',
                         'Classic session cookie is expired')
        self.assertLessEqual(parse(classic_cookie['Expires']),
                             datetime.now(UTC),
                             'Classic session cookie is expired')
        self.assertEqual(classic_cookie['Domain'], '.arxiv.org',
                         'Domain is set')

        # Verify that the expiry is set in the database.
        with self.app.app_context():
            with legacy.transaction() as session:
                db_session = session.query(legacy.models.DBSession) \
                    .filter(legacy.models.DBSession.user_id == 1) \
                    .order_by(legacy.models.DBSession.session_id.desc()) \
                    .first()
                self.assertLessEqual(
                    datetime.fromtimestamp(db_session.end_time, tz=UTC),
                    datetime.now(UTC)
                )

    def test_logout_clears_legacy_submit_cookie(self):
        """When the user logs out, the legacy submit cookie is unset."""
        client = self.app.test_client()
        # client.set_cookie('localhost')
        form_data = {'username': 'foouser', 'password': 'thepassword'}

        # Werkzeug should keep the cookies around for the next request.
        response = client.post('/login', data=form_data)
        cookies = _parse_cookies(response.headers.getlist('Set-Cookie'))

        cookie_name = self.app.config['AUTH_SESSION_COOKIE_NAME']
        classic_cookie_name = self.app.config['CLASSIC_COOKIE_NAME']

        client.set_cookie('', 'submit_session', '12345678')
        self.assertIn(cookie_name, cookies, "Sets cookie for authn session.")
        self.assertIn(classic_cookie_name, cookies,
                      "Sets cookie for classic sessions.")

        cookie = cookies[cookie_name]
        classic_cookie = cookies[classic_cookie_name]

        # Verify that the domain is correct.
        self.assertEqual(cookie['Domain'], '.arxiv.org', 'Domain is set')
        self.assertEqual(classic_cookie['Domain'], '.arxiv.org',
                         'Domain is set')

        # Verify that the correct expiry is set.
        self.assertEqual(int(cookie['Max-Age']), self.expiry - 1)
        self.assertEqual(int(classic_cookie['Max-Age']), self.expiry - 1)

        expires_in = (parse(cookie['Expires']) - datetime.now(UTC)).seconds
        classic_expires_in = (parse(classic_cookie['Expires'])
                              - datetime.now(UTC)).seconds
        self.assertLess(expires_in - self.expiry, 2)
        self.assertLess(classic_expires_in - self.expiry, 2)

        # Now log out.
        response = client.get('/logout')
        logout_cookies = _parse_cookies(response.headers.getlist('Set-Cookie'))

        cookie = logout_cookies[cookie_name]
        classic_cookie = logout_cookies[classic_cookie_name]

        self.assertEqual(cookie['value'], '', 'Session cookie is unset')
        self.assertEqual(cookie['Max-Age'], '0', 'Session cookie is expired')
        self.assertLessEqual(parse(cookie['Expires']), datetime.now(UTC),
                             "Session cookie is expired")
        self.assertEqual(cookie['Domain'], '.arxiv.org', 'Domain is set')
        self.assertEqual(classic_cookie['value'], '',
                         'Classic cookie is unset')
        self.assertEqual(classic_cookie['Max-Age'], '0',
                         'Classic cookie is expired')
        self.assertLessEqual(parse(classic_cookie['Expires']),
                             datetime.now(UTC),
                             "Classic cookie is expired")
        self.assertEqual(classic_cookie['Domain'], '.arxiv.org',
                         'Classic cookie domain is set')
        self.assertEqual(logout_cookies['submit_session']['Max-Age'], '0',
                         'Legacy submission cookie is expired')
