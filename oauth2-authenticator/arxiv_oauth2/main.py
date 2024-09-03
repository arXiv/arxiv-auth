import os
from typing import Callable

from arxiv.auth.legacy.util import missing_configs
from arxiv.base.globals import get_application_config
from fastapi import FastAPI, Request
from fastapi.responses import Response, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

from arxiv.base.logging import getLogger
from arxiv.db.models import configure_db
from arxiv.auth.openid.oidc_idp import ArxivOidcIdpClient

from .authentication import router as auth_router
from .app_logging import setup_logger

#
# Since this is not a flask app, the config needs to be in the os.environ
# Fill in these if it's missing
#
CONFIG_DEFAULTS = {
    'SESSION_DURATION': '10',
    'CLASSIC_COOKIE_NAME': 'foo',
    'CLASSIC_SESSION_HASH': 'bar'
}

#
# LOGOUT_REDIRECT_URL

# You should set BASE_SERVER first.
# That's the entry point of whole thing
# Setting has the notion of AUTH_SERVER, and it may be relevant.
# For the actual deployment, since this is running in a docker with plain HTTP,
# it's up to the web server's setting.

SERVER_ROOT_PATH = os.environ.get('SERVER_ROOT_PATH', "/aaa")
#
KEYCLOAK_SERVER_URL = os.environ.get('KEYCLOAK_SERVER_URL', 'https://oidc.arxiv.org')

# This is the public URL that OAuth2 calls back when the authentication succeeds.
CALLBACK_URL = os.environ.get("OAUTH2_CALLBACK_URL", "https://dev3.arxiv.org/aaa/callback")

# For arxiv-user, the client needs to know the secret.
# This is in keycloak's setting. Do not ever ues this value. This is for development only.
# You should generate one, and use it in keycloak. it can generate a good one on UI.
KEYCLOAK_CLIENT_SECRET = os.environ.get('KEYCLOAK_CLIENT_SECRET', 'gsG2HIu/lYZawKCwvlVE4fUYJpw=')


# session cookie names
AUTH_SESSION_COOKIE_NAME = os.environ.get("AUTH_SESSION_COOKIE_NAME", "arxiv_session_cookie")
CLASSIC_COOKIE_NAME = os.environ.get("CLASSIC_COOKIE_NAME", "tapir_session_cookie")

_idp_ = ArxivOidcIdpClient(CALLBACK_URL,
                           scope=["openid"],
                           server_url=KEYCLOAK_SERVER_URL,
                           client_secret=KEYCLOAK_CLIENT_SECRET,
                           logger=getLogger(__name__)
                           )

origins = ["http://127.0.0.1", "http://localhost", "https://dev3.arxiv.org"]


def create_app(*args, **kwargs) -> FastAPI:
    setup_logger()
    from arxiv.config import settings

    for key in missing_configs(get_application_config()):
        os.environ[key] = CONFIG_DEFAULTS[key]
        os.putenv(key, CONFIG_DEFAULTS[key])

    engine, _ = configure_db(settings)
    app = FastAPI(
        root_path=SERVER_ROOT_PATH,
        idp=_idp_,
        arxiv_db_engine=engine,
        arxiv_settings=settings,
        JWT_SECRET=settings.SECRET_KEY,
        AUTH_SESSION_COOKIE_NAME=AUTH_SESSION_COOKIE_NAME,
        CLASSIC_COOKIE_NAME=CLASSIC_COOKIE_NAME,
        **{f"ARXIV_URL_{name.upper()}": value for name, value, site in settings.URLS }
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

    app.include_router(auth_router)

    @app.middleware("http")
    async def apply_response_headers(request: Request, call_next: Callable) -> Response:
        """Apply response headers to all responses.
           Prevent UI redress attacks.
        """
        response: Response = await call_next(request)
        response.headers['Content-Security-Policy'] = "frame-ancestors 'none'"
        response.headers['X-Frame-Options'] = 'DENY'
        return response

    @app.get("/")
    async def root(request: Request):
        return "Hello"

    return app
