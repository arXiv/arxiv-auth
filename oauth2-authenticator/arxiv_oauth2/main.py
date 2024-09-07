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
# Fill in these if it's missing. This is required for setting up Tapir session.
# On Apache, these are found.
# Since this is running in docker, there is no way to get that value so needs to be set
# as environment.
# These look a little redundant (which probably true) but making sure they are present in the
# os.environ wi
#
CONFIG_DEFAULTS = {
    'SESSION_DURATION': os.environ.get('SESSION_DURATION', '36000'),
    'CLASSIC_COOKIE_NAME': os.environ.get("CLASSIC_COOKIE_NAME", "tapir_session"),
    'CLASSIC_SESSION_HASH': os.environ.get('CLASSIC_SESSION_HASH', 'not-very-safe-hash-value')
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
AUTH_SESSION_COOKIE_NAME = os.environ.get("AUTH_SESSION_COOKIE_NAME", "arxiv_oidc_session")

# More cors origins
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "")

_idp_ = ArxivOidcIdpClient(CALLBACK_URL,
                           scope=["openid"],
                           server_url=KEYCLOAK_SERVER_URL,
                           client_secret=KEYCLOAK_CLIENT_SECRET,
                           logger=getLogger(__name__)
                           )

origins = ["http://localhost.arxiv.org",
           "http://localhost.arxiv.org/",
           "http://localhost.arxiv.org:5000",
           "http://localhost.arxiv.org:5000/",
           "http://localhost.arxiv.org:5000/admin-console",
           "http://localhost.arxiv.org:5000/admin-console/",
           "https://dev3.arxiv.org",
           "https://dev3.arxiv.org/",
           "https://dev.arxiv.org",
           "https://dev.arxiv.org/",
           "https://arxiv.org",
           "https://arxiv.org/"
           ]

def create_app(*args, **kwargs) -> FastAPI:
    setup_logger()
    from arxiv.config import settings

    # Doubly check we agree with get_application_config
    for key in missing_configs(get_application_config()):
        os.environ[key] = CONFIG_DEFAULTS[key]
        os.putenv(key, CONFIG_DEFAULTS[key])
    CLASSIC_COOKIE_NAME = os.environ['CLASSIC_COOKIE_NAME']
    logger = getLogger(__name__)

    # DOMAIN is okay to be None
    DOMAIN = os.environ.get("DOMAIN")
    if DOMAIN:
        if DOMAIN[0] != ".":
            DOMAIN = "." + DOMAIN
            logger.warning("DOMAIN did not have the leading dot. %s", DOMAIN)
    secure = True
    SECURE = os.environ.get("SECURE", "").lower()
    if SECURE in ["false", "no"]:
        secure = False

    logger.info(f"SERVER_ROOT_PATH: {SERVER_ROOT_PATH}")
    logger.info(f"CALLBACK_URL: {CALLBACK_URL}")
    logger.info(f"AUTH_SESSION_COOKIE_NAME: {AUTH_SESSION_COOKIE_NAME}")
    logger.info(f"CLASSIC_COOKIE_NAME: {CLASSIC_COOKIE_NAME}")

    if not secure:
        logger.warning("SECURE is off. This cannot be good even in dev. This is for local development, like running under debugger.")

    jwt_secret = get_application_config().get('JWT_SECRET', settings.SECRET_KEY)

    engine, _ = configure_db(settings)
    app = FastAPI(
        root_path=SERVER_ROOT_PATH,
        idp=_idp_,
        arxiv_db_engine=engine,
        arxiv_settings=settings,
        SECURE=secure,
        DOMAIN=DOMAIN,
        JWT_SECRET=jwt_secret,
        AUTH_SESSION_COOKIE_NAME=AUTH_SESSION_COOKIE_NAME,
        CLASSIC_COOKIE_NAME=CLASSIC_COOKIE_NAME,
        **{f"ARXIV_URL_{name.upper()}": value for name, value, site in settings.URLS }
    )

    if CORS_ORIGINS:
        for cors_origin in CORS_ORIGINS.split(","):
            origins.append(cors_origin.strip())

    flattened_origins = ",".join(origins)
    logger.info(f"cors origins: {flattened_origins}")

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
