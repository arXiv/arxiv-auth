"""Provides Flask integration for the external user interface."""

from typing import Any, Callable
from datetime import datetime, timedelta
from functools import wraps
from pytz import timezone, UTC
import logging
import secrets
import hmac

from flask import Blueprint, render_template, request, \
    make_response, redirect, current_app, Response, jsonify

from arxiv import status

from accounts.controllers import authentication

# for become_user:
import jwt
import os
import uuid
from arxiv_auth.auth.sessions.store import _generate_nonce
from arxiv_auth.legacy.cookies import pack, unpack
from arxiv_auth.legacy.models import db, DBSession, DBUserNickname, DBUser
from arxiv_auth.legacy.models import TapirAdminAudit
from arxiv_auth.legacy.util import compute_capabilities, now
from accounts.next_page import good_next_page

DEBUG=0


EASTERN = timezone('US/Eastern')

logger = logging.getLogger(__name__)
blueprint = Blueprint('ui', __name__, url_prefix='')


def _set_become_user_csrf_cookie(response: Response, token: str) -> None:
    cookie_name = current_app.config['BECOME_USER_CSRF_COOKIE_NAME']
    params = {
        'httponly': False,
        'domain': current_app.config['AUTH_SESSION_COOKIE_DOMAIN'],
    }
    if current_app.config['AUTH_SESSION_COOKIE_SECURE']:
        params.update({'secure': True, 'samesite': 'lax'})
    response.set_cookie(cookie_name, token, max_age=3600, **params)


def _issue_become_user_csrf_token(response: Response) -> str:
    token = secrets.token_urlsafe(32)
    _set_become_user_csrf_cookie(response, token)
    return token


def _fresh_auth_required() -> bool:
    """Set BECOME_USER_FRESH_AUTH_SECONDS to 0 to disable fresh-auth checks."""
    return bool(current_app.config.get('BECOME_USER_FRESH_AUTH_SECONDS', 600) > 0)


def _is_fresh_auth(session_start_iso: str) -> bool:
    if not _fresh_auth_required():
        return True
    if not session_start_iso:
        return False
    try:
        start = datetime.fromisoformat(session_start_iso)
    except ValueError:
        return False
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    max_age = int(current_app.config['BECOME_USER_FRESH_AUTH_SECONDS'])
    return datetime.now(tz=UTC) - start <= timedelta(seconds=max_age)


def _reauth_redirect() -> Response:
    referrer = request.referrer or ''
    next_page = good_next_page(referrer)
    login_url = f"/login?next_page={next_page}"
    return make_response(redirect(login_url, code=status.HTTP_303_SEE_OTHER))


def _valid_become_user_csrf() -> bool:
    cookie_name = current_app.config['BECOME_USER_CSRF_COOKIE_NAME']
    cookie_token = request.cookies.get(cookie_name, '')
    request_token = request.form.get('csrf_token', '') \
        or request.headers.get('X-CSRF-Token', '')
    return bool(
        cookie_token and request_token
        and hmac.compare_digest(cookie_token, request_token)
    )


def unset_become_user_csrf_cookie(response: Response) -> None:
    cookie_name = current_app.config['BECOME_USER_CSRF_COOKIE_NAME']
    domain = current_app.config['AUTH_SESSION_COOKIE_DOMAIN']
    # Clear with no domain, with leading-dot domain, and without leading dot
    # to ensure the cookie is removed regardless of how the browser stored it.
    response.set_cookie(key=cookie_name, value='', max_age=0, httponly=False)
    response.set_cookie(key=cookie_name, value='', max_age=0, httponly=False, domain=domain)
    response.set_cookie(key=cookie_name, value='', max_age=0, httponly=False,
                        domain=domain.lstrip('.'))


def anonymous_only(func: Callable) -> Callable:
    """Redirect logged-in users to their profile."""
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if request.auth:
            next_page = good_next_page(request.args.get('next_page',None))
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
    cookie_name = current_app.config['MASQUERADE_COOKIE_NAME']
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


@blueprint.route('/login', methods=['GET', 'POST'])
@anonymous_only
def login() -> Response:
    """User can log in with username and password, or permanent token."""
    ip_address = request.remote_addr
    safe_page = good_next_page(request.args.get('next_page', ''))
    logger.debug('Request to log in, then redirect to %s', safe_page)
    data, code, headers = authentication.login(request.method, request.form,
                                               ip_address, safe_page)
    # Flask cookie-setting methods are on response, do here instead of in controller
    if code is status.HTTP_303_SEE_OTHER:
        response = make_response(redirect(safe_page, code=code))
        set_cookies(response, data)
        _issue_become_user_csrf_token(response)
        unset_submission_cookie(response)    # Fix for ARXIVNG-1149
        return response

    # User wants login form, formdata invalid, or login failed
    data.update({'pagetitle': 'Log in to arXiv'})
    return Response(render_template("accounts/login.html", **data), status=code)


@blueprint.route('/logout', methods=['GET'])
def logout() -> Response:
    """Log out of arXiv."""
    session_cookie_key = current_app.config['AUTH_SESSION_COOKIE_NAME']
    classic_cookie_key = current_app.config['CLASSIC_COOKIE_NAME']
    session_cookie = request.cookies.get(session_cookie_key, None)
    classic_cookie = request.cookies.get(classic_cookie_key, None)
    safe_page = good_next_page(request.args.get('next_page', ''))
    logger.debug('Request to log out, then redirect to %s', safe_page)
    data, code, _ = authentication.logout(session_cookie, classic_cookie, safe_page)
    # Flask puts cookie-setting methods response, do that here instead of controller.
    if code is status.HTTP_303_SEE_OTHER:
        logger.debug('Redirecting to %s: %i', safe_page, code)
        response = make_response(redirect(safe_page, code=code))
        set_cookies(response, data)
        unset_submission_cookie(response)  # Fix for ARXIVNG-1149.
        unset_permanent_cookie(response)  # Partial fix for ARXIVNG-1653, ARXIVNG-1644
        unset_masquerade_cookie(response)
        unset_become_user_csrf_cookie(response)
        return response
    return redirect(safe_page, code=status.HTTP_302_FOUND)


@blueprint.route('/auth_status', methods=['GET'])
def auth_status() -> Response:
    """Get if the app is running."""
    return make_response("OK")


@blueprint.route('/become_user/csrf', methods=['GET'])
def become_user_csrf() -> Response:
    """Issue a CSRF token for `/become_user`. Requires admin (flag_edit_users)."""
    if not request.auth:
        return Response("Unauthorized", status=status.HTTP_401_UNAUTHORIZED)
    user_id = request.auth.user.user_id if request.auth.user else None
    if not user_id:
        return Response("Unauthorized", status=status.HTTP_401_UNAUTHORIZED)
    admin_user = db.session.query(DBUser) \
        .filter(DBUser.user_id == int(user_id)) \
        .filter(DBUser.flag_edit_users == 1) \
        .filter(DBUser.flag_deleted == 0) \
        .filter(DBUser.flag_banned == 0) \
        .filter(DBUser.flag_approved == 1) \
        .first()
    if not admin_user:
        return Response("Forbidden", status=status.HTTP_403_FORBIDDEN)
    token = secrets.token_urlsafe(32)
    response = make_response(jsonify({'csrf_token': token}), status.HTTP_200_OK)
    _set_become_user_csrf_cookie(response, token)
    return response


# Only use post in production to avoid caching issues in fastly,
#   but can include GET in dev for testing.
@blueprint.route('/become_user', methods=['POST'])
def become_user_become_user_id() -> Response:

    if not _valid_become_user_csrf():
        return Response("Forbidden", status=status.HTTP_403_FORBIDDEN)

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
    if session_cookie:

        try:
            data = jwt.decode(session_cookie, secret, algorithms=["HS256"])
        except Exception:
            return _reauth_redirect()
        if DEBUG:
            print("BU-DEBUG: jwt decode session_cookie:", data)
        if not _is_fresh_auth(data.get('start_time')):
            return _reauth_redirect()

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
        data: dict[str, Any] = {
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

        data: dict[str, Any] = {
            'cookies': {
                'AUTH_SESSION_COOKIE': (become_jwt, 3600),
                'CLASSIC_COOKIE': (become_session_cookie, 3600),
                'MASQUERADE_COOKIE': ('1', 3600),
            }
        }
        set_cookies(response, data)
        unset_submission_cookie(response)
        unset_permanent_cookie(response)
        unset_become_user_csrf_cookie(response)
        response.set_cookie(key=tracking_cookie_name, value='', max_age=0, httponly=True)

        return response
