from typing import Tuple
from werkzeug import MultiDict
from arxiv.users import domain

ResponseData = Tuple[dict, int, dict]


def profile(method: str, params: MultiDict, session: domain.Session,
            ip_address: str) -> ResponseData:
    return {'session': domain.to_dict(session)}, 200, {}
