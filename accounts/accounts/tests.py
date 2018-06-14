"""."""

from unittest import TestCase, mock
from datetime import datetime
import os
import subprocess
import time
import hashlib
from base64 import b64encode

from arxiv import status
from accounts.factory import create_web_app
from accounts.domain import User, UserSession, UserPrivileges


def _parse_cookies(cookie_data):
    cookies = {}
    for cdata in cookie_data:
        parts = cdata.split('; ')
        data = parts[0]
        key, value = data[:data.index('=')], data[data.index('=') + 1:]
        extra = {
            part[:part.index('=')]: part[part.index('=') + 1:]
            for part in parts[1:]
        }
        cookies[key] = dict(value=value, **extra)
    return cookies


class TestLoginLogoutRoutes(TestCase):
    """Test logging in and logging out."""

    @classmethod
    def setUpClass(cls):
        """Spin up redis."""
        cls.redis = subprocess.run(
            "docker run -d -p 6379:6379 redis",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
        )
        time.sleep(5)    # In case it takes a moment to start.
        if cls.redis.returncode > 0:
            raise RuntimeError('Could not start redis. Is Docker running?')

        cls.container = cls.redis.stdout.decode('ascii').strip()
        cls.secret = 'bazsecret'
        cls.app = create_web_app()
        cls.app.config['CLASSIC_COOKIE_NAME'] = 'foo_tapir_session'
        cls.app.config['SESSION_COOKIE_NAME'] = 'baz_session'
        cls.app.config['JWT_SECRET'] = cls.secret
        cls.app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db.sqlite'
        cls.client = cls.app.test_client()
        cls.app.app_context().push()
        from accounts.services import classic_session_store, users
        classic_session_store.create_all()
        users.create_all()

        with users.transaction() as session:
            # We have a good old-fashioned user.
            user_class = users.models.TapirPolicyClass(
                class_id=2,
                name='Public user',
                password_storage=2,
                recovery_policy=3,
                permanent_login=1,
                description=''
            )
            db_user = users.models.TapirUser(
                user_id=1,
                first_name='first',
                last_name='last',
                suffix_name='iv',
                email='first@last.iv',
                policy_class=user_class.class_id,
                flag_edit_users=1,
                flag_email_verified=1,
                flag_edit_system=0,
                flag_approved=1,
                flag_deleted=0,
                flag_banned=0,
                tracking_cookie='foocookie',
            )
            db_nick = users.models.TapirUserNickname(
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
            db_password = users.models.TapirUserPassword(
                user_id=1,
                password_storage=2,
                password_enc=encrypted
            )
            session.add(db_user)
            session.add(db_password)
            session.add(db_nick)
            session.add(user_class)
            session.commit()

    @classmethod
    def tearDownClass(cls):
        """Tear down redis."""
        subprocess.run(f"docker rm -f {cls.container}",
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       shell=True)
        from accounts.services import classic_session_store, users
        classic_session_store.drop_all()
        users.drop_all()

    def test_get_login(self):
        """GET request to /login returns the login form."""
        response = self.client.get('/user/login')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.content_type, 'text/html; charset=utf-8')

    def test_post_login(self):
        """POST request to /login with valid form data returns redirect."""
        form_data = {'username': 'foouser', 'password': 'thepassword'}
        next_page = '/foo'
        response = self.client.post(f'/user/login?next_page={next_page}',
                                    data=form_data)
        self.assertEqual(response.status_code, status.HTTP_303_SEE_OTHER)
        self.assertTrue(response.headers['Location'].endswith(next_page),
                        "Redirect should point at value of `next_page` param")
        cookies = _parse_cookies(response.headers.getlist('Set-Cookie'))

        self.assertIn(self.app.config['SESSION_COOKIE_NAME'], cookies,
                      "Sets cookie for authn session.")
        self.assertIn(self.app.config['CLASSIC_COOKIE_NAME'], cookies,
                      "Sets cookie for classic sessions.")

    def test_post_login_baddata(self):
        """POST rquest to /login with invalid data returns 400."""
        form_data = {'username': 'foouser', 'password': 'notthepassword'}
        response = self.client.post('/user/login', data=form_data)
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_logout(self):
        """User logs in and then logs out."""
        form_data = {'username': 'foouser', 'password': 'thepassword'}

        # Werkzeug should keep the cookies around for the next request.
        response = self.client.post('/user/login', data=form_data)
        cookies = _parse_cookies(response.headers.getlist('Set-Cookie'))
        self.assertIn(self.app.config['SESSION_COOKIE_NAME'], cookies,
                      "Sets cookie for authn session.")
        self.assertIn(self.app.config['CLASSIC_COOKIE_NAME'], cookies,
                      "Sets cookie for classic sessions.")
        response = self.client.get('/user/logout')
        cookies = _parse_cookies(response.headers.getlist('Set-Cookie'))
        self.assertEqual(
            cookies[self.app.config['SESSION_COOKIE_NAME']]['value'],
            '',
            'UserSession cookie is unset'
        )
        cookie_expires = datetime.strptime(
            cookies[self.app.config['SESSION_COOKIE_NAME']]['Expires'],
            '%a, %d-%b-%Y %H:%M:%S %Z'
        )
        self.assertGreater(datetime.now(), cookie_expires,
                           "Session cookie is expired")
        self.assertEqual(
            cookies[self.app.config['CLASSIC_COOKIE_NAME']]['value'],
            '',
            'Classic cookie is unset'
        )
        classic_cookie_expires = datetime.strptime(
            cookies[self.app.config['CLASSIC_COOKIE_NAME']]['Expires'],
            '%a, %d-%b-%Y %H:%M:%S %Z'
        )
        self.assertGreater(datetime.now(), classic_cookie_expires,
                           "Classic session cookie is expired")
