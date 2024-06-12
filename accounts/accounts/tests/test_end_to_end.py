"""End-to-end tests, via requests to the user interface."""

from flask import request, Blueprint
from unittest import TestCase
from datetime import datetime
from pytz import timezone, UTC
from dateutil.parser import parse
import os
import hashlib
from base64 import b64encode
from urllib.parse  import quote_plus

from arxiv import status
from arxiv.db import models
#from accounts.services import legacy, users
from arxiv_auth.legacy import util
from accounts.factory import create_web_app


import urllib

from hypothesis import given, settings
from hypothesis import strategies as st
import string


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

blueprint = Blueprint('testauth', __name__)

@blueprint.route('/test_auth')
def auth_check():
    if hasattr(request, 'auth') and request.auth:
        return {}, status.HTTP_200_OK, {}
    else:
        return {}, status.HTTP_401_UNAUTHORIZED, {}


class TestLoginLogoutRoutes(TestCase):
    """Test logging in and logging out."""

    @classmethod
    def setUpClass(self):
        self.secret = 'bazsecret'
        self.db = 'db.sqlite'
        self.expiry = 500

    def setUp(self):
        self.ip_address = '10.1.2.3'
        os.environ['ARXIV_AUTH_DEBUG'] = '1'
        os.environ['CLASSIC_COOKIE_NAME'] = 'foo_tapir_session'
        os.environ['AUTH_SESSION_COOKIE_NAME'] = 'baz_session'
        os.environ['AUTH_SESSION_COOKIE_SECURE'] = '0'
        os.environ['SESSION_DURATION'] = str(self.expiry)
        os.environ['JWT_SECRET'] = self.secret
        os.environ['CLASSIC_DATABASE_URI'] = f'sqlite:///{self.db}'
        os.environ['CLASSIC_SESSION_HASH'] = 'xyz1234'
        os.environ['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{self.db}'
        os.environ['REDIS_FAKE'] = '1'

        self.environ_base = {'REMOTE_ADDR': self.ip_address}
        self.app = create_web_app()
        self.app.register_blueprint(blueprint)

        with self.app.app_context():
            util.drop_all(self.app.config['DB_ENGINE'])
            util.create_all(self.app.config['DB_ENGINE'])

            with util.transaction() as session:
                # We have a good old-fashioned user.
                db_user = models.TapirUser(
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
                db_nick = models.TapirNickname(
                    nick_id=1,
                    nickname='foouser',
                    user_id=1,
                    user_seq=1,
                    flag_valid=1,
                    role=0,
                    policy=0,
                    flag_primary=1
                )
                db_demo = models.Demographic(
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
                db_password = models.TapirUsersPassword(
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

        assert next_page in response.headers['Location'] #  redirect should point at value of `next_page` param
        cookies = _parse_cookies(response.headers.getlist('Set-Cookie'))

        cookie_name = self.app.config['AUTH_SESSION_COOKIE_NAME']
        self.assertIn(cookie_name, cookies, "Sets cookie for authn session.")

        classic_cookie_name = self.app.config['CLASSIC_COOKIE_NAME']
        self.assertIn(classic_cookie_name, cookies, "Sets classic cookie")

        cookie = cookies[cookie_name]
        classic_cookie = cookies[classic_cookie_name]

        # Verify that the domain is correct.
        self.assertEqual(cookie['Domain'], 'arxiv.org', 'Domain is set')
        self.assertEqual(classic_cookie['Domain'], 'arxiv.org',
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
            with util.transaction() as session:
                db_session = session.query(models.TapirSession) \
                    .filter(models.TapirSession.user_id == 1) \
                    .order_by(models.TapirSession.session_id.desc()) \
                    .first()
                self.assertEqual(db_session.end_time, 0)


    def test_post_login_continuation_byte(self):
        """POST with data that cannot be encoded as utf8 ARXIVNG-4743"""
        client = self.app.test_client()
        client.environ_base = self.environ_base
        form_data = {'username': 'foouser',
                     'password': '\xD8\x01\xDC\x37'}
        next_page = '/foo'
        response = client.post(f'/login?next_page={next_page}', data=form_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_post_login_bad_data(self):
        """POST /login with bad form data ARXIVNG-4743"""
        client = self.app.test_client()
        client.environ_base = self.environ_base
        form_data = {'username':
                     '\xd1\x85\xd1\x85\xd1\x85\xd1\x82\xd0\xb5\xd0\xbd\xd1\x82\xd0\xb0\xd1\x81\xd0\xbe\xd0\xbd',
                     'password': 'thepassword'}
        next_page = '/foo'
        response = client.post(f'/login?next_page={next_page}', data=form_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_get_something_protected(self):
        """User logs in, then reqeusts an auth protected page"""
        client = self.app.test_client()
        response = client.get('/test_auth')
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

        form_data = {'username': 'foouser', 'password': 'thepassword'}
        response = client.post('/login', data=form_data)
        self.assertEqual(response.status_code, status.HTTP_303_SEE_OTHER)
        assert response.headers.getlist('Set-Cookie')

        # the flask client should keep cookies but werkzeug won't let us set domain to
        # localhost so we have to work around like this.
        auth_cookie_name = self.app.config['AUTH_SESSION_COOKIE_NAME']
        cookie = _parse_cookies(response.headers.getlist('Set-Cookie'))[auth_cookie_name]
        client.set_cookie(key=auth_cookie_name, value=cookie['value'], domain='localhost')

        legacy_cookie_name = self.app.config['CLASSIC_COOKIE_NAME']
        cookie = _parse_cookies(response.headers.getlist('Set-Cookie'))[legacy_cookie_name]
        client.set_cookie(key=legacy_cookie_name, value=cookie['value'], domain='localhost')

        next_page = 'https://arxiv.org/some_sort_of_next_page?cheeseburger=yes%20please'
        response = client.get('/login?next_page=' + quote_plus(next_page))
        assert response.status_code == status.HTTP_303_SEE_OTHER
        assert response.headers['Location'] == next_page

        response = client.get('/test_auth')
        assert response.status_code == status.HTTP_200_OK

    def test_already_logged_in_redirect(self):
        """User logs in, then reqeusts /login again and should be redirected"""
        client = self.app.test_client()
        form_data = {'username': 'foouser', 'password': 'thepassword'}
        response = client.post('/login', data=form_data)
        self.assertEqual(response.status_code, status.HTTP_303_SEE_OTHER)
        assert response.headers.getlist('Set-Cookie')

        # the flask client should keep cookies but werkzeug won't let us set domain to
        # localhost so we have to work around like this.
        auth_cookie_name = self.app.config['AUTH_SESSION_COOKIE_NAME']
        cookie = _parse_cookies(response.headers.getlist('Set-Cookie'))[auth_cookie_name]
        client.set_cookie(key=auth_cookie_name, value=cookie['value'], domain='localhost')

        legacy_cookie_name = self.app.config['CLASSIC_COOKIE_NAME']
        cookie = _parse_cookies(response.headers.getlist('Set-Cookie'))[legacy_cookie_name]
        client.set_cookie(key=legacy_cookie_name, value=cookie['value'], domain='localhost')

        next_page = 'https://arxiv.org/some_sort_of_next_page?cheeseburger=yes%20please'
        response = client.get('/login?next_page=' + quote_plus(next_page))
        assert response.status_code == status.HTTP_303_SEE_OTHER
        assert response.headers['Location'] == next_page

        next_page = 'https://somesubdomain.arxiv.org/some_sort_of_next_page?blt=yes%20please'
        response = client.get('/login?next_page=' + quote_plus(next_page))
        assert response.status_code == status.HTTP_303_SEE_OTHER
        assert response.headers['Location'] == next_page, "/login should fowrward to arxiv subdomains"

        next_page = '/some_relative_page'
        response = client.get('/login?next_page=' + quote_plus(next_page))
        assert response.status_code == status.HTTP_303_SEE_OTHER
        assert response.headers['Location'].endswith(next_page), "/login should fowrward to relative pages"

        next_page = 'https://scammy.example.com/whereisit?cheese=idontknow'
        response = client.get('/login?next_page=' + quote_plus(next_page))
        assert response.headers['Location'] != next_page, "/login should not forward to scammmy URLs"
        assert response.headers['Location'] == self.app.config['DEFAULT_LOGIN_REDIRECT_URL']

        next_page = '/whereisit?' + ','.join(30 * 'cheese=idontknow')
        response = client.get('/login?next_page=' + quote_plus(next_page))
        assert response.headers['Location'] != next_page, "/login should not forward to super long URL"
        assert response.headers['Location'] == self.app.config['DEFAULT_LOGIN_REDIRECT_URL']

        next_page = 'https://arxiv.org/whereisit?' + ','.join(30 * 'cheese=idontknow')
        response = client.get('/login?next_page=' + quote_plus(next_page))
        assert response.headers['Location'] != next_page, "/login should not forward to super long URL"
        assert response.headers['Location'] == self.app.config['DEFAULT_LOGIN_REDIRECT_URL']

    def test_post_login_baddata(self):
        """POST request to /login with invalid data returns 400."""
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
        self.assertEqual(cookie['Domain'], 'arxiv.org', 'Domain is set')
        self.assertEqual(classic_cookie['Domain'], 'arxiv.org', 'Domain is set')

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
            with util.transaction() as session:
                db_session = session.query(models.TapirSession) \
                    .filter(models.TapirSession.user_id == 1) \
                    .order_by(models.TapirSession.session_id.desc()) \
                    .first()
                self.assertEqual(db_session.end_time, 0)

        response = client.get('/logout')
        assert response.status_code == 303
        logout_cookies = _parse_cookies(response.headers.getlist('Set-Cookie'))
        cookie = logout_cookies[cookie_name]
        classic_cookie = logout_cookies[classic_cookie_name]

        self.assertEqual(cookie['value'], '', 'Session cookie is unset')
        self.assertEqual(cookie['Max-Age'], '0', 'Session cookie is expired')
        self.assertLessEqual(parse(cookie['Expires']), datetime.now(UTC),
                             "Session cookie is expired")
        self.assertEqual(cookie['Domain'], 'arxiv.org', 'Domain is set')

        self.assertEqual(classic_cookie['value'], '',
                         'Classic cookie is unset')
        self.assertEqual(classic_cookie['Max-Age'], '0',
                         'Classic session cookie is expired')
        self.assertLessEqual(parse(classic_cookie['Expires']),
                             datetime.now(UTC),
                             'Classic session cookie is expired')
        self.assertEqual(classic_cookie['Domain'], 'arxiv.org',
                         'Domain is set')

        # Verify that the expiry is set in the database.
        with self.app.app_context():
            with util.transaction() as session:
                db_session = session.query(models.TapirSession) \
                    .filter(models.TapirSession.user_id == 1) \
                    .order_by(models.TapirSession.session_id.desc()) \
                    .first()
                self.assertLessEqual(
                    datetime.fromtimestamp(db_session.end_time, tz=UTC),
                    datetime.now(UTC)
                )

    def test_logout_clears_legacy_submit_cookie(self):
        """When the user logs out, the legacy submit cookie is unset."""
        client = self.app.test_client()
        form_data = {'username': 'foouser', 'password': 'thepassword'}

        # Werkzeug should keep the cookies around for the next request.
        response = client.post('/login', data=form_data)
        cookies = _parse_cookies(response.headers.getlist('Set-Cookie'))

        cookie_name = self.app.config['AUTH_SESSION_COOKIE_NAME']
        classic_cookie_name = self.app.config['CLASSIC_COOKIE_NAME']

        client.set_cookie(key='submit_session', value='12345678')
        self.assertIn(cookie_name, cookies, "Sets cookie for authn session.")
        self.assertIn(classic_cookie_name, cookies,
                      "Sets cookie for classic sessions.")

        cookie = cookies[cookie_name]
        classic_cookie = cookies[classic_cookie_name]

        # Verify that the domain is correct.
        self.assertEqual(cookie['Domain'], 'arxiv.org', 'Domain is set')
        self.assertEqual(classic_cookie['Domain'], 'arxiv.org',
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
        self.assertEqual(cookie['Domain'], 'arxiv.org', 'Domain is set')
        self.assertEqual(classic_cookie['value'], '',
                         'Classic cookie is unset')
        self.assertEqual(classic_cookie['Max-Age'], '0',
                         'Classic cookie is expired')
        self.assertLessEqual(parse(classic_cookie['Expires']),
                             datetime.now(UTC),
                             "Classic cookie is expired")
        self.assertEqual(classic_cookie['Domain'], 'arxiv.org',
                         'Classic cookie domain is set')
        self.assertEqual(logout_cookies['submit_session']['Max-Age'], '0',
                         'Legacy submission cookie is expired')


    def test_post_login_empty(self):
        """Empty POST request to /login."""
        form_data = {'username': 'foouser', 'password': ''}
        client = self.app.test_client()
        response = client.post('/login', data=form_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = client.post('/login', data=form_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = client.post('/login', data=form_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        response = client.post('/login', data=form_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @given(st.text()) #Limited to utf-8
    @settings(max_examples=2000, deadline=1000)
    def test_post_login_fuzz(self, fuzzed_pw):
        """Fuzz POST request to /login."""
        if fuzzed_pw == 'thepassword':
            return
        form_data = {'username': 'foouser', 'password': fuzzed_pw}
        client = self.app.test_client()
        response = client.post('/login', data=form_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)


    def test_post_login_with_next_page(self):
        """POST request to /login with valid form data but bad next_page."""
        client = self.app.test_client()
        client.environ_base = self.environ_base
        form_data = {'username': 'foouser', 'password': 'thepassword'}
        bad_next_page = 'https://bbc.co.uk'
        response = client.post(f'/login?next_page={bad_next_page}', data=form_data)
        self.assertEqual(response.status_code, status.HTTP_303_SEE_OTHER)

        assert bad_next_page not in response.headers['Location'] #  redirect should NOT point at value of `bad_next_page` param

        # Now client should be logged in

        bad_next_page = 'https://bbc.co.uk'
        response = client.post(f'/login?next_page={bad_next_page}', data=form_data)
        self.assertEqual(response.status_code, status.HTTP_303_SEE_OTHER)
        assert bad_next_page not in response.headers['Location'] #  redirect should NOT point at value of `bad_next_page` param



    def test_post_login_with_next_page_implicit_protocol(self):
        """POST request to /login with valid form data but bad next_page."""
        client = self.app.test_client()
        client.environ_base = self.environ_base
        form_data = {'username': 'foouser', 'password': 'thepassword'}
        bad_next_page = '//bbc.co.uk'
        response = client.post(f'/login?next_page={bad_next_page}', data=form_data)
        self.assertEqual(response.status_code, status.HTTP_303_SEE_OTHER)
        assert bad_next_page not in response.headers['Location'] #  redirect should NOT point at value of `bad_next_page` param
        assert "bbc" not in response.headers['Location'] #  redirect should NOT point at value of `bad_next_page` param

        # Now client should be logged in
        bad_next_page = '//bbc.co.uk'  # implied protocol, gets a https: added by client browser on redirect
        response = client.post(f'/login?next_page={bad_next_page}', data=form_data)
        self.assertEqual(response.status_code, status.HTTP_303_SEE_OTHER)
        assert bad_next_page not in response.headers['Location'] #  redirect should NOT point at value of `bad_next_page` param
        assert "bbc" not in response.headers['Location'] #  redirect should NOT point at value of `bad_next_page` param
