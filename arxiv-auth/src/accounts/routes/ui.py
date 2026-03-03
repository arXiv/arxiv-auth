"""Provides Flask integration for the external user interface."""

from typing import Any, Callable
from datetime import datetime, timedelta
from functools import wraps
from pytz import timezone, UTC
import logging

from flask import Blueprint, render_template, url_for, request, \
    make_response, redirect, current_app, send_file, Response

from arxiv import status
from arxiv_auth import domain

from accounts.controllers import authentication

# for become_user:
import jwt
import os
import uuid
from arxiv_auth.auth.sessions.store import _generate_nonce
from arxiv_auth.auth.tokens import decode
from arxiv_auth.domain import Session as JWTSession
from arxiv_auth.legacy.cookies import pack, unpack
from arxiv_auth.legacy.models import db, DBSession, DBUserNickname, DBUser
from arxiv_auth.legacy.models import TapirAdminAudit
from arxiv_auth.legacy.util import compute_capabilities, epoch, get_session_duration, now
DEBUG=0


EASTERN = timezone('US/Eastern')

logger = logging.getLogger(__name__)
blueprint = Blueprint('ui', __name__, url_prefix='')


def user_is_owner(session: domain.Session, user_id: str, **kw: Any) -> bool:
    """Determine whether the authenticated user matches the requested user."""
    return bool(session.user.user_id == user_id)


def anonymous_only(func: Callable) -> Callable:
    """Redirect logged-in users to their profile."""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if request.auth:
            next_page = request.args.get('next_page',
                                         current_app.config['DEFAULT_LOGIN_REDIRECT_URL'])
            return make_response(redirect(next_page, code=status.HTTP_303_SEE_OTHER))
        else:
            return func(*args, **kwargs)
    return wrapper


def set_cookies(response: Response, data: dict) -> None:
    """
    Update a :class:`.Response` with cookies in controller data.

    Contollers seeking to update cookies must include a 'cookies' key
    in their response data.
    """
    # Set the session cookie.
    cookies = data.pop('cookies')
    if cookies is None:
        return None
    for cookie_key, (cookie_value, expires) in cookies.items():
        cookie_name = current_app.config[f'{cookie_key.upper()}_NAME']
        max_age = timedelta(seconds=expires)
        # expires_date = expires_date.replace(tzinfo=EASTERN)
        domain = current_app.config['AUTH_SESSION_COOKIE_DOMAIN']
        logger.info('Set cookie %s with %s, max_age %s domain %s',
                    cookie_name, cookie_value, max_age, domain)
        is_httponly = False if cookie_name == "MASQUERADE" else True
        params = dict(httponly=is_httponly, domain=domain)
        if current_app.config['AUTH_SESSION_COOKIE_SECURE']:
            # Setting samesite to lax, to allow reasonable links to
            # authenticated views using GET requests.
            params.update({'secure': True, 'samesite': 'lax'})
        response.set_cookie(key=cookie_name, value=cookie_value, max_age=max_age,
                            **params)

# Not sure unset_masquerade_cookie will be needed,
#   as this other code should be enough to clear it first:
#     accounts/accounts/controllers/authentication.py:190
def unset_masquerade_cookie(response: Response) -> None:
    cookie_name = current_app.config[f'MASQUERADE_COOKIE_NAME']
    response.set_cookie(key=cookie_name, value='', max_age=0, httponly=True)

# This is unlikely to be useful once the classic submission UI is disabled.
def unset_submission_cookie(response: Response) -> None:
    """
    Unset the legacy Catalyst submission cookie.

    In addition to the authenticated session (which was originally from the
    Tapir auth system), Catalyst also tracks a session used specifically for
    the submission process. The legacy Catalyst controller sets this
    automatically, so we don't need to do anything on login. But on logout,
    if this cookie is not cleared, Catalyst may attempt to use the same
    submission session upon subsequent logins. This can lead to weird
    inconsistencies.
    """
    response.set_cookie(key='submit_session', value='', max_age=0, httponly=True)


def unset_permanent_cookie(response: Response) -> None:
    """
    Users who elect a permanent cookie expect it to be unset when they log out.

    If it is not unset, legacy components will attempt to log them back in.
    """
    permanent_cookie_name = current_app.config['CLASSIC_PERMANENT_COOKIE_NAME']
    domain = current_app.config['AUTH_SESSION_COOKIE_DOMAIN']
    now = datetime.now(UTC)
    response.set_cookie(key=permanent_cookie_name, value='', max_age=0, expires=now,
                        httponly=True)
    response.set_cookie(key=permanent_cookie_name, value='', max_age=0, expires=now,
                        httponly=True, domain=domain)
    response.set_cookie(key=permanent_cookie_name, value='', max_age=0, expires=now,
                        httponly=True, domain=domain.lstrip('.'))


@blueprint.after_request
def apply_response_headers(response: Response) -> Response:
    """Apply response headers to all responses."""
    """Prevent UI redress attacks."""
    response.headers['Content-Security-Policy'] = "frame-ancestors 'none'"
    response.headers['X-Frame-Options'] = 'DENY'

    return response

# @blueprint.route('/register', methods=['GET', 'POST'])
@anonymous_only
def register() -> Response:
    """Interface for creating new accounts."""
    captcha_secret = current_app.config['CAPTCHA_SECRET']
    ip_address = request.remote_addr
    next_page = request.args.get('next_page', url_for('account'))
    data, code, headers = registration.register(request.method, request.form,
                                                captcha_secret, ip_address,
                                                next_page)

    # Flask puts cookie-setting methods on the response, so we do that here
    # instead of in the controller.
    if code is status.HTTP_303_SEE_OTHER:
        response = make_response(redirect(headers['Location'], code=code))
        set_cookies(response, data)
        return response
    content = render_template("accounts/register.html", **data)
    response = make_response(content, code, headers)
    return response


@blueprint.route('/login', methods=['GET', 'POST'])
@anonymous_only
def login() -> Response:
    """User can log in with username and password, or permanent token."""
    ip_address = request.remote_addr
    form_data = request.form
    default_next_page = current_app.config['DEFAULT_LOGIN_REDIRECT_URL']
    next_page = request.args.get('next_page', default_next_page)
    logger.debug('Request to log in, then redirect to %s', next_page)
    data, code, headers = authentication.login(request.method,
                                               form_data, ip_address,
                                               next_page)
    data.update({'pagetitle': 'Log in to arXiv'})
    # Flask puts cookie-setting methods on the response, so we do that here
    # instead of in the controller.
    if code is status.HTTP_303_SEE_OTHER:
        # Set the session cookie.
        response = make_response(redirect(headers.get('Location'), code=code))
        set_cookies(response, data)
        unset_submission_cookie(response)    # Fix for ARXIVNG-1149.
        return response

    # Form is invalid, or login failed.
    response = Response(
        render_template("accounts/login.html", **data),
        status=code
    )
    return response

@blueprint.route('/logout', methods=['GET'])
def logout() -> Response:
    """Log out of arXiv."""
    session_cookie_key = current_app.config['AUTH_SESSION_COOKIE_NAME']
    classic_cookie_key = current_app.config['CLASSIC_COOKIE_NAME']
    session_cookie = request.cookies.get(session_cookie_key, None)
    classic_cookie = request.cookies.get(classic_cookie_key, None)
    default_next_page = current_app.config['DEFAULT_LOGOUT_REDIRECT_URL']
    next_page = request.args.get('next_page', default_next_page)
    logger.debug('Request to log out, then redirect to %s', next_page)
    data, code, headers = authentication.logout(session_cookie, classic_cookie,
                                                next_page)
    # Flask puts cookie-setting methods on the response, so we do that here
    # instead of in the controller.
    if code is status.HTTP_303_SEE_OTHER:
        logger.debug('Redirecting to %s: %i', headers.get('Location'), code)
        response = make_response(redirect(headers.get('Location'), code=code))
        set_cookies(response, data)
        unset_submission_cookie(response)    # Fix for ARXIVNG-1149.
        # Partial fix for ARXIVNG-1653, ARXIVNG-1644
        unset_permanent_cookie(response)
        unset_masquerade_cookie(response)
        return response
    return redirect(next_page, code=status.HTTP_302_FOUND)


# @blueprint.route('/captcha', methods=['GET'])
@anonymous_only
def captcha() -> Response:
    """Provide the image for stateless captcha."""
    secret = current_app.config['CAPTCHA_SECRET']
    font = current_app.config.get('CAPTCHA_FONT')
    token = request.args.get('token')
    data, code, headers = captcha_image.get(token, secret, request.remote_addr, font)
    return send_file(data['image'], mimetype=data['mimetype']), code, headers


@blueprint.route('/auth_status', methods=['GET'])
def auth_status() -> Response:
    """Get if the app is running."""
    return make_response("OK")

def _checked_next_page(otherwise=None) -> str:
    if not otherwise:
        otherwise = current_app.config['DEFAULT_LOGIN_REDIRECT_URL']
    next_page = request.args.get('next_page', otherwise)
    if authentication.good_next_page(next_page):
        return next_page
    else:
        return otherwise

# Only use post in production to avoid caching issues in fastly,
#   but can include GET in dev for testing.
@blueprint.route('/become_user', methods=['POST'])
def become_user_become_user_id() -> Response:

    become_user_id = int(request.args.get('become_user_id'))

    classic_cookie_name = current_app.config['CLASSIC_COOKIE_NAME']
    classic_cookie = request.cookies.get(classic_cookie_name, None)
    if DEBUG:
        print("BU-DEBUG: classic_cookie", classic_cookie_name, classic_cookie)
    classic_cookie_data = unpack(classic_cookie)
    if DEBUG:
        print("BU-DEBUG: classic_cookie_data", classic_cookie_data)

    permanent_cookie_name = current_app.config['CLASSIC_PERMANENT_COOKIE_NAME']
    permanent_cookie = request.cookies.get(permanent_cookie_name, None)
    if DEBUG:
        print("BU-DEBUG: permanent_cookie_name", permanent_cookie_name, permanent_cookie)

    session_cookie_name = current_app.config['AUTH_SESSION_COOKIE_NAME']
    session_cookie = request.cookies.get(session_cookie_name, None)
    if DEBUG:
        print("BU-DEBUG: session_cookie_name", session_cookie_name, session_cookie)

    session_cookie_domain = current_app.config['AUTH_SESSION_COOKIE_DOMAIN']
    if DEBUG:
        print("BU-DEBUG: session_cookie_domain", session_cookie_domain)

    session_cookie_secure = current_app.config['AUTH_SESSION_COOKIE_SECURE']
    if DEBUG:
        print("BU-DEBUG: session_cookie_secure", session_cookie_secure)


    submit_cookie_name = 'submit_session'
    submit_cookie = request.cookies.get(submit_cookie_name, None)
    if DEBUG:
        print("BU-DEBUG: submit_cookie", submit_cookie_name, submit_cookie)

    tracking_cookie_name = os.environ.get('CLASSIC_TRACKING_COOKIE', 'browser')
    tracking_cookie = request.cookies.get(tracking_cookie_name, None)
    if DEBUG:
        print("BU-DEBUG: tracking_cookie", tracking_cookie_name, tracking_cookie)

    secret = os.environ.get('JWT_SECRET')

    ip_address = request.remote_addr
    if DEBUG:
        print("BU-DEBUG: ip_address", ip_address)

    valid_user = False
    jwt_session = None
    if session_cookie:

        data = jwt.decode(session_cookie, secret, algorithms=["HS256"])
        if DEBUG:
            print("BU-DEBUG: jwt decode session_cookie:", data)

        user_id = f"{ data.get('user_id') }"
        if user_id:
            user_id = int(user_id)
            if user_id > 0:
                if DEBUG:
                    print("BU-DEBUG: jwt user_id", user_id, type(user_id))

                admin_user = db.session.query(DBUser) \
                    .filter(DBUser.user_id == int(user_id)) \
                    .filter(DBUser.flag_edit_users == 1) \
                    .filter(DBUser.flag_deleted == 0) \
                    .filter(DBUser.flag_banned == 0) \
                    .filter(DBUser.flag_approved == 1) \
                    .first()

                if DEBUG:
                    print("BU-DEBUG: look for admin_user:", admin_user)
                if admin_user:
                    valid_user = True

    valid_become_user_id = False
    if valid_user:
        if become_user_id > 0:
            if DEBUG:
                print("BU-DEBUG: become_user_id", become_user_id)
            become_user = db.session.query(DBUser) \
                .filter(DBUser.user_id == int(become_user_id)) \
                .filter(DBUser.flag_edit_users == 0) \
                .filter(DBUser.flag_deleted == 0) \
                .filter(DBUser.flag_banned == 0) \
                .filter(DBUser.flag_approved == 1) \
                .first()
                #.filter(DBUser.flag_can_lock == 0) \

            if DEBUG:
                print("BU-DEBUG: become_user", become_user)
            if become_user:
                valid_become_user_id= True

            if DEBUG:
                print(dir(become_user))


    found_username = False
    become_username = None
    if valid_become_user_id:
        become_user_nickname = db.session.query(DBUserNickname) \
            .filter(DBUserNickname.user_id == int(become_user_id)) \
            .filter(DBUserNickname.flag_valid == 1) \
            .first()
        if DEBUG:
            print("BU-DEBUG: become_user_nickname", become_user_nickname)
        if become_user_nickname:
            become_username = become_user_nickname.nickname
            found_username = True
            if DEBUG:
                print("BU-DEBUG: become_username", become_username)

    if not (valid_user and valid_become_user_id and found_username):
        response = make_response(redirect("/login", code=status.HTTP_303_SEE_OTHER))
        return response
    else:

        start_time = ( datetime.now(tz=UTC) ).replace(microsecond=0)
        expires    = ( start_time + timedelta(seconds=3600) ).replace(microsecond=0)
        now1 = now()
        if DEBUG:
            print("BU-DEBUG: dates.start_time:", start_time)
            print("BU-DEBUG: dates.expires:", expires)
            print("BU-DEBUG: dates.now1:", now1)

        become_session = DBSession(
            end_time=0,
            last_reissue=now1,
            start_time=now1,
            user_id=become_user.user_id,
        )
        db.session.add(become_session)
        db.session.commit()
        if DEBUG:
            print("BU-DEBUG: become_session", become_session)

        admin_audit = TapirAdminAudit(
            action="become-user",
            admin_user=admin_user.user_id,
            affected_user=become_user.user_id,
            comment='No-comment',
            data=become_session.session_id,
            ip_addr=ip_address,
            log_date=now1,
            session=become_session,
            tracking_cookie=tracking_cookie,
        )
        db.session.add(admin_audit)
        db.session.commit()
        if DEBUG:
            print("BU-DEBUG: admin_audit", admin_audit)

        become_jwt_data = {
            'user_id': become_session.user_id,
            'session_id': str(uuid.uuid4()),
            'nonce': _generate_nonce(),
            "expires": expires.isoformat(),
            "start_time": start_time.isoformat(),
        }
        become_jwt = jwt.encode(become_jwt_data, secret)
        if DEBUG:
            print("BU-DEBUG: become_jwt", become_jwt)

        next_page = "https://check.dev.arxiv.org/"
        data: Dict[str, Any] = {
            'next_page': next_page,
            'admin_user': admin_user,
            'become_user': become_user,
            'become_username': become_username,
        }
        response = Response(
           render_template("accounts/become_user.html", **data),
            status=200
        )

        become_session_cookie = pack(
            become_session.session_id,
            become_session.user_id,
            ip_address,
            start_time,
            compute_capabilities(become_user),
        )
        if DEBUG:
            print("BU-DEBUG: become_session_cookie", become_session_cookie)

        data: Dict[str, Any] = {
            'cookies': {
                'AUTH_SESSION_COOKIE': (become_jwt, 3600),
                'CLASSIC_COOKIE': (become_session_cookie, 3600),
                'MASQUERADE_COOKIE': ('1', 3600),
            }
        }
        set_cookies(response, data)
        unset_submission_cookie(response)
        unset_permanent_cookie(response)
        response.set_cookie(key=tracking_cookie_name, value='', max_age=0, httponly=True)

        return response
