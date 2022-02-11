from typing import Literal, List, Optional

from pydantic import BaseModel


class Auth(BaseModel):
    """ See arxiv-auth users/arxiv/users/auth/sessions/store.py
    generate_cookie() """
    user_id: int
    session_id: str
    nonce: str
    expires: str


class RawAuth(BaseModel):
    """An encoded JWT from a HTTP request"""
    rawjwt: str
    rawheader: Optional[str]
    via: Literal["cookie", "header"]
    key: str

class User(BaseModel):
    """Represents an arXiv admin or mod user"""

    user_id: int
    """arXiv user ID"""
    
    name: str
    """name of user built from first_name and last_name"""

    username: str
    """arXiv nickname from tapir_nicknames"""

    email: str
    """email addresss of user"""
    
    is_moderator: bool
    """True if listed as modertor for any category or archive"""
    
    is_admin: bool
    """True if has flag edit users"""
    
    moderated_categories: List[str]
    """Moderated categories but see ``UserStore`` for limitations"""
    
    moderated_archives: List[str]
    """Moderated archives but see ``UserStore`` for limitations"""
