"""Tests for :mod:`accounts.services.users`."""

from unittest import TestCase, mock
from datetime import datetime
import hashlib
from base64 import b64encode
from contextlib import contextmanager
from flask import Flask

from accounts.services import users
from accounts.domain import User

DATABASE_URL = 'sqlite:///:memory:'


@contextmanager
def in_memory_db():
    """Provide an in-memory sqlite database for testing purposes."""
    app = Flask('foo')
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['CLASSIC_SESSION_HASH'] = 'foohash'

    with app.app_context():
        users.init_app(app)
        users.create_all()
        try:
            yield users._current_session()
        except Exception:
            raise
        finally:
            users.drop_all()


class TestAuthenticateWithPermanentToken(TestCase):
    """User has a permanent token."""

    def test_token_is_malformed(self):
        """Token is present, but it has the wrong format."""
        bad_token = 'footokenhasnohyphen'
        with in_memory_db():
            with self.assertRaises(users.AuthenticationFailed):
                users.authenticate(token=bad_token)

    def test_token_is_incorrect(self):
        """Token is present, but there is no such token in the database."""
        bad_token = '1234-nosuchtoken'
        with in_memory_db():
            with self.assertRaises(users.AuthenticationFailed):
                users.authenticate(token=bad_token)

    def test_token_is_invalid(self):
        """The token is present, but it is not valid."""
        with in_memory_db() as session:
            # We have a good old-fashioned user.
            user_id = 1
            user_class = users.models.TapirPolicyClass(
                class_id=2,
                name='Public user',
                description='foo',
                password_storage=2,
                recovery_policy=3,
                permanent_login=1
            )
            db_user = users.models.TapirUser(
                user_id=user_id,
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
                nickname='foouser',
                user_id=user_id,
                user_seq=1,
                flag_valid=1,
                role=0,
                policy=0,
                flag_primary=1
            )
            salt = b'foo'
            password = b'thepassword'
            db_password = users.models.TapirUserPassword(
                user_id=user_id,
                password_storage=2,
                password_enc=hashlib.sha1(salt + b'-' + password).digest()
            )
            n = (datetime.now() - datetime.utcfromtimestamp(0)).total_seconds()
            secret = 'foosecret'
            db_token = users.models.TapirPermanentToken(
                user_id=user_id,
                secret=secret,
                valid=0,    # <- Not valid!
                issued_when=n,
                issued_to='127.0.0.1',
                remote_host='foohost.foo.com',
                session_id=0
            )
            session.add(user_class)
            session.add(db_user)
            session.add(db_password)
            session.add(db_nick)
            session.add(db_token)
            session.commit()

            with self.assertRaises(users.AuthenticationFailed):
                users.authenticate(token=f'{user_id}-{secret}')

    def test_token_is_valid(self):
        """The token is valid!."""
        with in_memory_db() as session:
            # We have a good old-fashioned user.
            user_id = 1
            user_class = users.models.TapirPolicyClass(
                class_id=2,
                name='Public user',
                description='foo',
                password_storage=2,
                recovery_policy=3,
                permanent_login=1
            )
            db_user = users.models.TapirUser(
                user_id=user_id,
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
                nickname='foouser',
                user_id=user_id,
                user_seq=1,
                flag_valid=1,
                role=0,
                policy=0,
                flag_primary=1
            )
            salt = b'foo'
            password = b'thepassword'
            db_password = users.models.TapirUserPassword(
                user_id=user_id,
                password_storage=2,
                password_enc=hashlib.sha1(salt + b'-' + password).digest()
            )
            n = (datetime.now() - datetime.utcfromtimestamp(0)).total_seconds()
            secret = 'foosecret'
            db_token = users.models.TapirPermanentToken(
                user_id=user_id,
                secret=secret,
                valid=1,    # <- Valid!
                issued_when=n,
                issued_to='127.0.0.1',
                remote_host='foohost.foo.com',
                session_id=0
            )
            session.add(user_class)
            session.add(db_user)
            session.add(db_password)
            session.add(db_nick)
            session.add(db_token)
            session.commit()
            user = users.authenticate(token=f'{user_id}-{secret}')
            self.assertIsInstance(user, User, "Returns data about the user")
            self.assertEqual(user.user_id, db_user.user_id,
                             "User ID is set correctly")
            self.assertEqual(user.username, db_nick.nickname,
                             "Username is set correctly")
            self.assertEqual(user.email, db_user.email,
                             "User email is set correctly")
            self.assertEqual(user.privileges.classic, 6,
                             "Privileges are set")


class TestAuthenticateWithPassword(TestCase):
    """User is attempting login with username+password."""

    def test_no_username(self):
        """Username is not entered."""
        username = ''
        password = 'foopass'
        with self.assertRaises(users.AuthenticationFailed):
            with in_memory_db():
                users.authenticate(username, password)

    def test_no_password(self):
        """Password is not entered."""
        username = 'foouser'
        password = ''
        with self.assertRaises(users.AuthenticationFailed):
            with in_memory_db():
                users.authenticate(username, password)

    def test_password_is_incorrect(self):
        """Password is incorrect."""
        with in_memory_db() as session:
            # We have a good old-fashioned user.
            user_class = users.models.TapirPolicyClass(
                class_id=2,
                name='Public user',
                description='foo',
                password_storage=2,
                recovery_policy=3,
                permanent_login=1
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
                nickname='foouser',
                user_id=1,
                user_seq=1,
                flag_valid=1,
                role=0,
                policy=0,
                flag_primary=1
            )
            salt = b'foo'
            password = b'thepassword'
            db_password = users.models.TapirUserPassword(
                user_id=1,
                password_storage=2,
                password_enc=hashlib.sha1(salt + b'-' + password).digest()
            )
            session.add(user_class)
            session.add(db_user)
            session.add(db_password)
            session.add(db_nick)
            session.commit()

            with self.assertRaises(users.AuthenticationFailed):
                users.authenticate('foouser', 'notthepassword')

    def test_password_is_correct(self):
        """Password is correct."""
        with in_memory_db() as session:
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

            user = users.authenticate('foouser', 'thepassword')
            self.assertIsInstance(user, User, "Returns data about the user")
            self.assertEqual(user.user_id, db_user.user_id,
                             "User ID is set correctly")
            self.assertEqual(user.username, db_nick.nickname,
                             "Username is set correctly")
            self.assertEqual(user.email, db_user.email,
                             "User email is set correctly")
            self.assertEqual(user.privileges.classic, 6,
                             "Privileges are set")

    def test_login_with_email_and_correct_password(self):
        """User attempts to log in with e-mail address."""
        with in_memory_db() as session:
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

            user = users.authenticate('first@last.iv', 'thepassword')
            self.assertIsInstance(user, User, "Returns data about the user")
            self.assertEqual(user.user_id, db_user.user_id,
                             "User ID is set correctly")
            self.assertEqual(user.username, db_nick.nickname,
                             "Username is set correctly")
            self.assertEqual(user.email, db_user.email,
                             "User email is set correctly")
            self.assertEqual(user.privileges.classic, 6,
                             "Privileges are set")

    def test_no_such_user(self):
        """Username does not exist."""
        with in_memory_db():
            with self.assertRaises(users.AuthenticationFailed):
                users.authenticate('nobody', 'thepassword')
