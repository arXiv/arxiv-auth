import os

from arxiv.config import settings
from fastapi import FastAPI, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Tuple, List, Dict
from pydantic import BaseModel
from sqlalchemy.orm import Session
import logging

from arxiv.db import get_db
from arxiv.db.models import TapirUser, TapirUsersPassword, \
    TapirNickname, Demographic, configure_db, State, TapirPolicyClass
from arxiv.auth.legacy.passwords import check_password
from arxiv.auth.legacy.exceptions import PasswordAuthenticationFailed, NoSuchUser

UserProfile = Tuple[TapirUser, TapirUsersPassword, TapirNickname, Demographic]

logger = logging.getLogger(__name__)

app = FastAPI()

security = HTTPBearer()

@app.get("/")
async def root():
    return {"message": "Hello"}

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    token = credentials.credentials
    if token != os.getenv("API_SECRET_KEY"):
        raise HTTPException(status_code=401, detail="Invalid or missing token")
    return token


def get_user_profile(session: Session, tapir_user: TapirUser) -> UserProfile:
    """
    Retrieve password, nickname and profile data.

    Parameters
    ----------
    session: DB session
    tapir_user : TapirUser

    Returns
    -------
    :class:`.TapirUser`
    :class:`.TapirUsersPassword`
    :class:`.TapirNickname`
    :class:`.Demographic`

    Raises
    ------
    :class:`NoSuchUser`
        Raised when the user cannot be found.
    :class:`RuntimeError`
        Raised when other problems arise.

    """
    if not tapir_user:
        raise NoSuchUser('User does not exist')

    tapir_nick = session.query(TapirNickname) \
            .filter(TapirNickname.user_id == tapir_user.user_id) \
            .first()
    if not tapir_nick:
        raise NoSuchUser('User lacks a nickname')

    tapir_password: TapirUsersPassword = session.query(TapirUsersPassword) \
        .filter(TapirUsersPassword.user_id == tapir_user.user_id) \
        .first()
    if not tapir_password:
        raise RuntimeError(f'Missing password')

    tapir_profile: Demographic = session.query(Demographic) \
        .filter(Demographic.user_id == tapir_user.user_id) \
        .first()
    return tapir_user, tapir_password, tapir_nick, tapir_profile


def authenticate_password(session: Session, user: TapirUser, password: str) -> UserProfile | None:
    """
    Authenticate using username/email and password.

    Parameters
    ----------
    user : TapirUser
        user model instance
    password : str

    Returns
    -------
    :class:`.TapirUser`
    :class:`.TapirUsersPassword`
    :class:`.TapirNickname`
    :class:`.TapirUserProfile`

    Raises
    ------
    :class:`AuthenticationFailed`
        Raised if the user does not exist or the password is incorrect.
    :class:`RuntimeError`
        Raised when other problems arise.

    """
    logger.debug(f'Authenticate with password, user: {user.user_id}')
    user_profile = get_user_profile(session, user)
    _db_user, db_pass, _db_nick, _db_profile = user_profile
    try:
        if check_password(password, db_pass.password_enc):
            return user_profile
    except PasswordAuthenticationFailed:
        pass
    return None


def _get_user_by_user_id(session: Session, user_id: int) -> TapirUser | None:
    """Only used by perm token"""
    return session.query(TapirUser) \
        .filter(TapirUser.user_id == int(user_id)) \
        .first()


def _get_user_by_email(session: Session, email: str) -> TapirUser | None:
    return session.query(TapirUser) \
        .filter(TapirUser.email == email) \
        .first()


def _get_user_by_username(session: Session, username: str) -> TapirUser | None:
    """Username is the tapir nickname."""
    if not username or '@' in username:
        raise ValueError("username must not contain a @")
    tapir_nick = session.query(TapirNickname) \
            .filter(TapirNickname.nickname == username) \
            .first()
    if not tapir_nick:
        return None

    return session.query(TapirUser) \
                .filter(TapirUser.user_id == tapir_nick.user_id) \
                .first()

def is_email(username_or_email) -> bool:
    return '@' in username_or_email


def get_tapir_user(session: Session, claim: str) -> TapirUser | None:
    """
    Does the user exist?

    Parameters
    ----------
    claim : str
        Either the email address or username of the authenticating user.

    Returns
    -------
    :class:`.TapirUser`
    """
    return _get_user_by_email(session, claim) if is_email(claim) else _get_user_by_username(session, claim)


class AuthResponse(BaseModel):
    id: str
    username: str
    email: str
    firstName: str
    lastName: str
    enabled: bool
    emailVerified: bool
    attributes: Dict[str, List[str]]
    roles: List[str]
    groups: List[str]
    requiredActions: List[str]


class PasswordData(BaseModel):
    password: str


def tapir_user_to_auth_response(tapir_user: TapirUser) -> AuthResponse:
    """Turns the tapir user to the user migration record"""
    # Keycloak's realm "arxiv" should have the roles beforehand.
    # Internal
    # AllowTexProduced
    # EditUsers
    # EditSystem
    # Approved
    # Banned
    # CanLock

    roles = []
    # not used - Only Pole Houle has this role apparently
    if tapir_user.flag_internal or tapir_user.flag_edit_system:
        roles.append('Owner')

    # admin flag
    if tapir_user.flag_allow_tex_produced:
        roles.append('AllowTexProduced')

    # admin flag
    if tapir_user.flag_edit_users:
        roles.append('Administrator')

    # not used
    if tapir_user.flag_approved:
        roles.append('Approved')

    # ?
    if tapir_user.flag_banned:
        roles.append('Banned')

    # user is able to lock submissions from further changes (ARXIVNG-2605)
    if tapir_user.flag_can_lock:
        roles.append('CanLock')

    attributes = {}

    # Important to have this. Otherwise, Keycloak does not pick up the email
    attributes["email"] = [tapir_user.email]

    # not used
    email_preferences = "email_preferences"
    attributes[email_preferences] = []
    if tapir_user.flag_wants_email:
        attributes[email_preferences].append('WantsEmail')
    if tapir_user.flag_html_email:
        attributes[email_preferences].append('HtmlEmail')

    # not used
    attributes["share"] = []
    if tapir_user.share_first_name:
        attributes["share"].append('FirstName')
    if tapir_user.share_last_name:
        attributes["share"].append('LastName')
    if tapir_user.share_email:
        attributes["share"].append('Email')

    # seems to exist in DB
    if tapir_user.joined_date:
        attributes["joined_date"] = [tapir_user.joined_date]
    if tapir_user.joined_ip_num:
        attributes["joined_ip_num"] = [tapir_user.joined_ip_num]
    if tapir_user.joined_remote_host:
        attributes["joined_remote_host"] = [tapir_user.joined_remote_host]

    if tapir_user.tracking_cookie:
        attributes["tracking_cookie"] = [tapir_user.tracking_cookie]

    if tapir_user.suffix_name:
        attributes["suffix_name"] = [tapir_user.suffix_name]

    if tapir_user.email_bouncing:
        attributes["email_bouncing"] = [str(tapir_user.email_bouncing)]

    groups = []

    tpc: TapirPolicyClass = tapir_user.tapir_policy_classes
    if tpc.class_id:
        groups.append(tpc.name)
        roles.append(tpc.name)

    username = tapir_user.tapir_nicknames.nickname
    if os.environ.get("NORMALIZE_USERNAME", "true") == "true":
        username = username.lower()

    return AuthResponse(
        id=tapir_user.user_id,
        username=username,
        email=tapir_user.email,
        firstName=tapir_user.first_name,
        lastName=tapir_user.last_name,
        enabled=not tapir_user.flag_deleted,
        emailVerified=tapir_user.flag_email_verified != 0,
        attributes=attributes,
        roles=roles,
        groups=groups,
        requiredActions=[],
    )


@app.get("/auth/{name}", response_model=AuthResponse)
async def get_auth_name(name: str, _token: str=Depends(verify_token)) -> AuthResponse:
    with get_db() as session:
        tapir_user = get_tapir_user(session, name)

        if not tapir_user:
            raise HTTPException(status_code=404, detail="User not found")

        return tapir_user_to_auth_response(tapir_user)


@app.post("/auth/{name}")
async def validate_user(name: str, pwd: PasswordData, _token: str=Depends(verify_token)):
    with get_db() as session:
        tapir_user = get_tapir_user(session, name)
        if not tapir_user:
            raise HTTPException(status_code=404, detail="User not found")

        if tapir_user.flag_banned:
            raise HTTPException(status_code=403, detail="User is banned")

        if tapir_user.flag_deleted:
            raise HTTPException(status_code=410, detail="User is deleted")

        if authenticate_password(session, tapir_user, pwd.password):
            # Placeholder for actual password validation logic
            return {"message": "User validated successfully"}
        else:
            raise HTTPException(status_code=401, detail="Invalid credentials")
    pass


@app.get("/states", response_model=dict)
async def health_check() -> dict:
    try:
        with get_db() as session:
            states: State = session.query(State).all()
            result = {state.name: state.value for state in states}
            return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.on_event("startup")
def on_startup():
    logger.debug('start')
    engine, _ = configure_db(settings)

    logger.debug(f"Engine: {engine.name}, DBURI: {settings.CLASSIC_DB_URI}")
    try:
        with get_db() as session:
            tapir_user = get_tapir_user(session, "ph18@cornell.edu")
            if tapir_user:
                logger.info(f"TapirUser: {str(tapir_user_to_auth_response(tapir_user))}")


    except Exception as e:
        logger.error("Database connection error")

    pass
9