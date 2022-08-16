"""Tests for :mod:`arxiv.users.legacy.accounts`."""

import tempfile
from datetime import datetime
import shutil
import hashlib
from pytz import UTC
from unittest import TestCase
from sqlalchemy import select

from .. import models, util, authenticate, exceptions
from .. import accounts
from .util import temporary_db
from ... import domain


def get_user(session, user_id):
    """Helper to get user database objects by user id."""
    db_user, db_nick = (
        session.query(models.DBUser, models.DBUserNickname)
        .filter(models.DBUser.user_id == user_id)
        .filter(models.DBUserNickname.flag_primary == 1)
        .filter(models.DBUserNickname.user_id == models.DBUser.user_id)
        .first()
    )

    db_profile = session.query(models.DBProfile) \
        .filter(models.DBProfile.user_id == user_id) \
        .first()

    return db_user, db_nick, db_profile


class SetUpUserMixin(object):
    """Mixin for creating a test user and other database goodies."""

    def setUp(self):
        """Set up the database."""
        self.db_path = tempfile.mkdtemp()
        self.db_uri = f'sqlite:///{self.db_path}/test.db'
        self.user_id = '15830'
        with temporary_db(self.db_uri, drop=False) as session:
            self.user_class = session.scalar(
                select(models.DBPolicyClass).where(models.DBPolicyClass.class_id==2))
            self.email = 'first@last.iv'
            self.db_user = models.DBUser(
                user_id=self.user_id,
                first_name='first',
                last_name='last',
                suffix_name='iv',
                email=self.email,
                policy_class=self.user_class.class_id,
                flag_edit_users=1,
                flag_email_verified=1,
                flag_edit_system=0,
                flag_approved=1,
                flag_deleted=0,
                flag_banned=0,
                tracking_cookie='foocookie',
            )
            self.username = 'foouser'
            self.db_nick = models.DBUserNickname(
                nickname=self.username,
                user_id=self.user_id,
                user_seq=1,
                flag_valid=1,
                role=0,
                policy=0,
                flag_primary=1
            )
            self.salt = b'foo'
            self.password = b'thepassword'
            hashed = hashlib.sha1(self.salt + b'-' + self.password).digest()
            self.db_password = models.DBUserPassword(
                user_id=self.user_id,
                password_storage=2,
                password_enc=hashed
            )
            n = util.epoch(datetime.now(tz=UTC))
            self.secret = 'foosecret'
            self.db_token = models.DBPermanentToken(
                user_id=self.user_id,
                secret=self.secret,
                valid=1,
                issued_when=n,
                issued_to='127.0.0.1',
                remote_host='foohost.foo.com',
                session_id=0
            )
            session.add(self.user_class)
            session.add(self.db_user)
            session.add(self.db_password)
            session.add(self.db_nick)
            session.add(self.db_token)
            session.commit()

    def tearDown(self):
        shutil.rmtree(self.db_path)


class TestUsernameExists(SetUpUserMixin, TestCase):
    """Tests for :mod:`accounts.does_username_exist`."""

    def test_with_nonexistant_user(self):
        """There is no user with the passed username."""
        with temporary_db(self.db_uri, create=False, drop=False):
            self.assertFalse(accounts.does_username_exist('baruser'))

    def test_with_existant_user(self):
        """There is a user with the passed username."""
        with temporary_db(self.db_uri, create=False, drop=False):
            self.assertTrue(accounts.does_username_exist('foouser'))


class TestEmailExists(SetUpUserMixin, TestCase):
    """Tests for :mod:`accounts.does_email_exist`."""

    def test_with_nonexistant_email(self):
        """There is no user with the passed email."""
        with temporary_db(self.db_uri, create=False, drop=False):
            self.assertFalse(accounts.does_email_exist('foo@bar.com'))

    def test_with_existant_email(self):
        """There is a user with the passed email."""
        with temporary_db(self.db_uri, create=False, drop=False):
            self.assertTrue(accounts.does_email_exist('first@last.iv'))


class TestRegister(SetUpUserMixin, TestCase):
    """Tests for :mod:`accounts.register`."""

    def test_register_with_duplicate_username(self):
        """The username is already in the system."""
        user = domain.User(username='foouser', email='foo@bar.com')
        ip = '1.2.3.4'
        with temporary_db(self.db_uri, create=False, drop=False):
            with self.assertRaises(exceptions.RegistrationFailed):
                accounts.register(user, 'apassword1', ip=ip, remote_host=ip)

    def test_register_with_duplicate_email(self):
        """The email address is already in the system."""
        user = domain.User(username='bazuser', email='first@last.iv')
        ip = '1.2.3.4'
        with temporary_db(self.db_uri, create=False, drop=False):
            with self.assertRaises(exceptions.RegistrationFailed):
                accounts.register(user, 'apassword1', ip=ip, remote_host=ip)

    def test_register_with_name_details(self):
        """Registration includes the user's name."""
        name = domain.UserFullName(forename='foo', surname='user', suffix='iv')
        user = domain.User(username='bazuser', email='new@account.edu',
                           name=name)
        ip = '1.2.3.4'

        with temporary_db(self.db_uri, create=False, drop=False) as session:
            u, _ = accounts.register(user, 'apassword1', ip=ip, remote_host=ip)
            db_user, db_nick, db_profile = get_user(session, u.user_id)

            self.assertEqual(db_user.first_name, name.forename)
            self.assertEqual(db_user.last_name, name.surname)
            self.assertEqual(db_user.suffix_name, name.suffix)

    def test_register_with_bare_minimum(self):
        """Registration includes only a username, name, email address, password."""
        user = domain.User(username='bazuser', email='new@account.edu',
                           name = domain.UserFullName(forename='foo', surname='user', suffix='iv'))
        ip = '1.2.3.4'

        with temporary_db(self.db_uri, create=False, drop=False) as session:
            u, _ = accounts.register(user, 'apassword1', ip=ip, remote_host=ip)
            db_user, db_nick, db_profile = get_user(session, u.user_id)

            self.assertEqual(db_user.flag_email_verified, 0)
            self.assertEqual(db_nick.nickname, user.username)
            self.assertEqual(db_user.email, user.email)

    def test_register_with_profile(self):
        """Registration includes profile information."""
        profile = domain.UserProfile(
            affiliation='School of Hard Knocks',
            country='de',
            rank=1,
            submission_groups=['grp_cs', 'grp_q-bio'],
            default_category=domain.Category('cs.DL'),
            homepage_url='https://google.com'
        )
        name = domain.UserFullName(forename='foo', surname='user', suffix='iv')
        user = domain.User(username='bazuser', email='new@account.edu',
                           name=name, profile=profile)
        ip = '1.2.3.4'

        with temporary_db(self.db_uri, create=False, drop=False) as session:
            u, _ = accounts.register(user, 'apassword1', ip=ip, remote_host=ip)
            db_user, db_nick, db_profile = get_user(session, u.user_id)

            self.assertEqual(db_profile.affiliation, profile.affiliation)
            self.assertEqual(db_profile.country, profile.country),
            self.assertEqual(db_profile.rank, profile.rank),
            self.assertEqual(db_profile.flag_group_cs, 1)
            self.assertEqual(db_profile.flag_group_q_bio, 1)
            self.assertEqual(db_profile.flag_group_physics, 0)
            self.assertEqual(db_profile.archive, 'cs')
            self.assertEqual(db_profile.subject_class, 'DL')

    def test_can_authenticate_after_registration(self):
        """A may authenticate a bare-minimum user after registration."""
        user = domain.User(username='bazuser', email='new@account.edu',
                           name=domain.UserFullName(forename='foo', surname='user'))
        ip = '1.2.3.4'

        with temporary_db(self.db_uri, create=False, drop=False) as session:
            u, _ = accounts.register(user, 'apassword1', ip=ip, remote_host=ip)
            db_user, db_nick, db_profile = get_user(session, u.user_id)
            auth_user, auths = authenticate.authenticate(
                username_or_email=user.username,
                password='apassword1'
            )
            self.assertEqual(str(db_user.user_id), auth_user.user_id)


class TestGetUserById(SetUpUserMixin, TestCase):
    """Tests for :func:`accounts.get_user_by_id`."""

    def test_user_exists(self):
        """A well-rounded user exists with the requested user id."""
        profile = domain.UserProfile(
            affiliation='School of Hard Knocks',
            country='de',
            rank=1,
            submission_groups=['grp_cs', 'grp_q-bio'],
            default_category=domain.Category('cs.DL'),
            homepage_url='https://google.com'
        )
        name = domain.UserFullName(forename='foo', surname='user', suffix='iv')
        user = domain.User(username='bazuser', email='new@account.edu',
                           name=name, profile=profile)
        ip = '1.2.3.4'

        with temporary_db(self.db_uri, create=False, drop=False):
            u, _ = accounts.register(user, 'apassword1', ip=ip, remote_host=ip)
            loaded_user = accounts.get_user_by_id(u.user_id)

        self.assertEqual(loaded_user.username, user.username)
        self.assertEqual(loaded_user.email, user.email)
        self.assertEqual(loaded_user.profile.affiliation, profile.affiliation)

    def test_user_does_not_exist(self):
        """No user with the specified username."""
        with temporary_db(self.db_uri, create=False, drop=False):
            with self.assertRaises(exceptions.NoSuchUser):
                accounts.get_user_by_id('1234')

    def test_with_no_profile(self):
        """The user exists, but there is no profile."""
        name = domain.UserFullName(forename='foo', surname='user', suffix='iv')
        user = domain.User(username='bazuser', email='new@account.edu',
                           name=name)
        ip = '1.2.3.4'

        with temporary_db(self.db_uri, create=False, drop=False):
            u, _ = accounts.register(user, 'apassword1', ip=ip, remote_host=ip)
            loaded_user = accounts.get_user_by_id(u.user_id)

        self.assertEqual(loaded_user.username, user.username)
        self.assertEqual(loaded_user.email, user.email)
        self.assertIsNone(loaded_user.profile)


class TestUpdate(SetUpUserMixin, TestCase):
    """Tests for :func:`accounts.update`."""

    def test_user_without_id(self):
        """A :class:`domain.User` is passed without an ID."""
        user = domain.User(username='bazuser', email='new@account.edu')
        with temporary_db(self.db_uri, create=False, drop=False):
            with self.assertRaises(ValueError):
                accounts.update(user)

    def test_update_nonexistant_user(self):
        """A :class:`domain.User` is passed that is not in the database."""
        user = domain.User(username='bazuser', email='new@account.edu',
                           user_id='12345')
        with temporary_db(self.db_uri, create=False, drop=False):
            with self.assertRaises(exceptions.NoSuchUser):
                accounts.update(user)

    def test_update_name(self):
        """The user's name is changed."""
        name = domain.UserFullName(forename='foo', surname='user', suffix='iv')
        user = domain.User(username='bazuser', email='new@account.edu',
                           name=name)
        ip = '1.2.3.4'

        with temporary_db(self.db_uri, create=False, drop=False) as session:
            user, _ = accounts.register(user, 'apassword1', ip=ip,
                                        remote_host=ip)

        with temporary_db(self.db_uri, create=False, drop=False) as session:
            updated_name = domain.UserFullName(forename='Foo',
                                               surname=name.surname,
                                               suffix=name.suffix)
            updated_user = domain.User(user_id=user.user_id,
                                       username=user.username,
                                       email=user.email,
                                       name=updated_name)

            updated_user, _ = accounts.update(updated_user)
            self.assertEqual(user.user_id, updated_user.user_id)
            self.assertEqual(updated_user.name.forename, 'Foo')
            db_user, db_nick, db_profile = get_user(session, user.user_id)
            self.assertEqual(db_user.first_name, 'Foo')

    def test_update_profile(self):
        """Changes are made to profile information."""
        profile = domain.UserProfile(
            affiliation='School of Hard Knocks',
            country='de',
            rank=1,
            submission_groups=['grp_cs', 'grp_q-bio'],
            default_category=domain.Category('cs.DL'),
            homepage_url='https://google.com'
        )
        name = domain.UserFullName(forename='foo', surname='user', suffix='iv')
        user = domain.User(username='bazuser', email='new@account.edu',
                           name=name, profile=profile)
        ip = '1.2.3.4'

        with temporary_db(self.db_uri, create=False, drop=False) as session:
            user, _ = accounts.register(user, 'apassword1', ip=ip,
                                        remote_host=ip)

        updated_profile = domain.UserProfile(
            affiliation='School of Hard Knocks',
            country='us',
            rank=2,
            submission_groups=['grp_cs', 'grp_physics'],
            default_category=domain.Category('cs.IR'),
            homepage_url='https://google.com'
        )
        updated_user = domain.User(user_id=user.user_id,
                                   username=user.username,
                                   email=user.email,
                                   name=name,
                                   profile=updated_profile)

        with temporary_db(self.db_uri, create=False, drop=False) as session:
            u, _ = accounts.update(updated_user)
            db_user, db_nick, db_profile = get_user(session, u.user_id)

            self.assertEqual(db_profile.affiliation,
                             updated_profile.affiliation)
            self.assertEqual(db_profile.country, updated_profile.country),
            self.assertEqual(db_profile.rank, updated_profile.rank),
            self.assertEqual(db_profile.flag_group_cs, 1)
            self.assertEqual(db_profile.flag_group_q_bio, 0)
            self.assertEqual(db_profile.flag_group_physics, 1)
            self.assertEqual(db_profile.archive, 'cs')
            self.assertEqual(db_profile.subject_class, 'IR')
